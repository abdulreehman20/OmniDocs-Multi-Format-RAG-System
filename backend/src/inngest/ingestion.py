import json
import tempfile
from pathlib import Path

from sqlmodel import Session

import inngest
from src.ai.ingestion.pipeline import (
    chunk_to_manifest_row,
    parse_local_file,
    read_jsonl_from_storage,
    sha256_file,
    staging_prefix,
    write_json_to_storage,
    write_jsonl_to_storage,
)
from src.ai.ingestion.registry import IngestionParseError
from src.config import get_settings
from src.db.session import engine
from src.inngest.client import get_inngest_client
from src.providers.runtime import get_embedding_provider, get_object_storage, get_vector_store
from src.services import ingestion as ingestion_service
from src.services.ingestion import IngestionConflictError

client = get_inngest_client()


def _session() -> Session:
    return Session(engine)


@client.create_function(
    fn_id="ingest-document-uploaded",
    trigger=inngest.TriggerEvent(event="document/uploaded.v1"),
    concurrency=[
        inngest.Concurrency(limit=1, key="event.data.owner_id"),
    ],
)
def ingest_document_uploaded(ctx: inngest.ContextSync) -> dict:
    data = ctx.event.data
    document_id = str(data["document_id"])
    job_id = str(data["job_id"])
    generation = int(data["generation"])
    owner_id = str(data["owner_id"])

    settings = get_settings()
    storage = get_object_storage()
    embeddings = get_embedding_provider()
    vectors = get_vector_store()

    def claim() -> dict:
        with _session() as session:
            return ingestion_service.claim_job(
                session,
                document_id=document_id,
                job_id=job_id,
                generation=generation,
            )

    try:
        claimed = ctx.step.run("claim-job", claim)
    except Exception as exc:
        with _session() as session:
            ingestion_service.mark_failed(
                session,
                document_id=document_id,
                job_id=job_id,
                error_code="claim_failed",
                error_message=str(exc),
            )
        raise

    object_key = str(claimed["object_key"])
    source_type = str(claimed["source_type"])
    prefix = staging_prefix(owner_id, document_id, generation)

    def download_and_verify() -> dict:
        with _session() as session:
            ingestion_service.update_progress(
                session,
                document_id=document_id,
                job_id=job_id,
                stage="download",
                progress=0.15,
                message="Downloading original",
            )
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        try:
            storage.download_to_file(object_key, tmp_path)
            return {
                "sha256": sha256_file(tmp_path),
                "byte_size": Path(tmp_path).stat().st_size,
            }
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    verified = ctx.step.run("download-and-verify", download_and_verify)

    def parse_and_chunk() -> dict:
        with _session() as session:
            ingestion_service.update_progress(
                session,
                document_id=document_id,
                job_id=job_id,
                stage="parse",
                progress=0.3,
                message="Parsing document",
            )
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        try:
            storage.download_to_file(object_key, tmp_path)
            units, chunks, warnings = parse_local_file(
                tmp_path,
                source_type=source_type,
                settings=settings,
                generation=generation,
                embedding_model_id=settings.embedding_model_id,
            )
        except IngestionParseError as exc:
            with _session() as session:
                ingestion_service.mark_failed(
                    session,
                    document_id=document_id,
                    job_id=job_id,
                    error_code=exc.code,
                    error_message=exc.message,
                )
            raise
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        with _session() as session:
            ingestion_service.update_progress(
                session,
                document_id=document_id,
                job_id=job_id,
                stage="chunk",
                progress=0.45,
                message="Chunking document",
                extra={"chunk_count": len(chunks)},
            )

        rows = [chunk_to_manifest_row(c, document_id) for c in chunks]
        normalized_key = f"{prefix}/normalized.jsonl"
        manifest_key = f"{prefix}/chunks-manifest.json"
        write_jsonl_to_storage(storage, normalized_key, units)
        write_json_to_storage(storage, manifest_key, {"chunks": rows, "chunk_count": len(rows)})

        batch_size = max(1, settings.ingestion_embed_batch_size)
        batch_keys: list[str] = []
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            key = f"{prefix}/batches/{len(batch_keys)}.jsonl"
            write_jsonl_to_storage(storage, key, batch)
            batch_keys.append(key)

        with _session() as session:
            ingestion_service.upsert_batches(
                session,
                job_id=job_id,
                document_id=document_id,
                generation=generation,
                batch_keys=batch_keys,
            )
        return {
            "normalized_key": normalized_key,
            "manifest_key": manifest_key,
            "batch_keys": batch_keys,
            "chunk_count": len(rows),
            "warnings": warnings,
        }

    try:
        manifest = ctx.step.run("parse-and-chunk", parse_and_chunk)
    except IngestionParseError:
        return {"status": "failed", "document_id": document_id}
    except Exception as exc:
        with _session() as session:
            ingestion_service.mark_failed(
                session,
                document_id=document_id,
                job_id=job_id,
                error_code="parse_chunk_failed",
                error_message=str(exc),
            )
        raise

    batch_keys = list(manifest["batch_keys"])

    def make_embed_fn(batch_number: int, batch_key: str):
        def embed_batch() -> dict:
            total = max(1, len(batch_keys))
            with _session() as session:
                ingestion_service.update_progress(
                    session,
                    document_id=document_id,
                    job_id=job_id,
                    stage="embed",
                    progress=0.5 + (0.35 * (batch_number + 1) / total),
                    message=f"Embedding batch {batch_number + 1}/{total}",
                )
            rows = read_jsonl_from_storage(storage, batch_key)
            texts = [str(r["text"]) for r in rows]
            embeds = embeddings.embed_documents(texts)
            payload = [
                {
                    "id": row["vector_id"],
                    "values": values,
                    "metadata": {
                        "document_id": document_id,
                        "owner_id": owner_id,
                        "generation": generation,
                        "chunk_index": row["chunk_index"],
                        "text_sha256": row["text_sha256"],
                    },
                }
                for row, values in zip(rows, embeds, strict=True)
            ]
            vectors.upsert(namespace=owner_id, vectors=payload)
            with _session() as session:
                ingestion_service.mark_batch_done(
                    session,
                    job_id=job_id,
                    batch_number=batch_number,
                    result={"upserted": len(payload)},
                )
            return {"batch_number": batch_number, "upserted": len(payload)}

        return embed_batch

    for i, key in enumerate(batch_keys):
        ctx.step.run(f"embed-upsert-batch-{i}", make_embed_fn(i, key))

    def persist_metadata() -> dict:
        with _session() as session:
            ingestion_service.update_progress(
                session,
                document_id=document_id,
                job_id=job_id,
                stage="persist",
                progress=0.9,
                message="Persisting chunk metadata",
            )
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        try:
            storage.download_to_file(manifest["manifest_key"], tmp_path)
            payload = json.loads(Path(tmp_path).read_text(encoding="utf-8"))
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        rows = payload["chunks"]
        with _session() as session:
            count = ingestion_service.replace_chunk_rows(
                session,
                owner_id=owner_id,
                document_id=document_id,
                generation=generation,
                rows=rows,
                embedding_model_id=settings.embedding_model_id,
                chunker_version=settings.chunker_version,
            )
        return {"chunk_count": count}

    persisted = ctx.step.run("persist-chunk-metadata", persist_metadata)

    def finalize() -> dict:
        with _session() as session:
            ingestion_service.finalize_generation(
                session,
                settings,
                document_id=document_id,
                job_id=job_id,
                generation=generation,
                chunk_count=int(persisted["chunk_count"]),
                content_sha256=str(verified["sha256"]),
            )
        return {"status": "ready"}

    try:
        ctx.step.run("finalize-generation", finalize)
    except IngestionConflictError as exc:
        with _session() as session:
            ingestion_service.mark_failed(
                session,
                document_id=document_id,
                job_id=job_id,
                error_code=exc.code,
                error_message=exc.message,
            )
        return {"status": "failed", "reason": exc.code}

    def cleanup() -> dict:
        items, _ = storage.list_prefix(prefix + "/")
        for item in items:
            key = item.get("Key")
            if key:
                try:
                    storage.delete(key)
                except Exception:
                    pass
        return {"cleaned": len(items)}

    ctx.step.run("cleanup-staging", cleanup)
    return {
        "status": "ready",
        "document_id": document_id,
        "chunk_count": persisted["chunk_count"],
    }

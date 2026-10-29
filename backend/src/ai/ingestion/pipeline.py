import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from src.ai.ingestion.chunking import chunk_extracted
from src.ai.ingestion.contracts import ChunkUnit
from src.ai.ingestion.normalize import normalize_extracted
from src.ai.ingestion.registry import load_document
from src.config import Settings
from src.providers.protocols import ObjectStorage


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build_vector_id(document_id: str, generation: int, chunk_index: int) -> str:
    return f"{document_id}:{generation}:{chunk_index}"


def staging_prefix(owner_id: str, document_id: str, generation: int) -> str:
    return f"users/{owner_id}/documents/{document_id}/staging/{generation}"


def parse_local_file(
    path: str | Path,
    *,
    source_type: str,
    settings: Settings,
    generation: int,
    embedding_model_id: str,
) -> tuple[list[dict[str, Any]], list[ChunkUnit], list[str]]:
    extracted = load_document(path, source_type=source_type, settings=settings)
    normalized = normalize_extracted(extracted)
    chunks = chunk_extracted(
        normalized,
        source_type=source_type,
        settings=settings,
        generation=generation,
        embedding_model_id=embedding_model_id,
    )
    units_payload = [
        {"text": u.text, "locator": u.locator} for u in normalized.units
    ]
    return units_payload, chunks, normalized.warnings


def write_jsonl_to_storage(
    storage: ObjectStorage,
    key: str,
    rows: list[dict[str, Any]],
) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
        for row in rows:
            tmp.write(json.dumps(row, ensure_ascii=False) + "\n")
        tmp_path = tmp.name
    try:
        storage.upload_file(key, tmp_path, "application/jsonl")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def write_json_to_storage(
    storage: ObjectStorage,
    key: str,
    payload: dict[str, Any],
) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(payload, tmp, ensure_ascii=False)
        tmp_path = tmp.name
    try:
        storage.upload_file(key, tmp_path, "application/json")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def read_jsonl_from_storage(storage: ObjectStorage, key: str) -> list[dict[str, Any]]:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        storage.download_to_file(key, tmp_path)
        rows: list[dict[str, Any]] = []
        for line in Path(tmp_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def batch_chunks(chunks: list[ChunkUnit], batch_size: int) -> list[list[ChunkUnit]]:
    size = max(1, batch_size)
    return [chunks[i : i + size] for i in range(0, len(chunks), size)]


def chunk_to_manifest_row(chunk: ChunkUnit, document_id: str) -> dict[str, Any]:
    return {
        "chunk_index": chunk.chunk_index,
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "text_sha256": chunk.text_sha256,
        "token_estimate": chunk.token_estimate,
        "locator": chunk.locator,
        "chunker_version": chunk.chunker_version,
        "embedding_model_id": chunk.embedding_model_id,
        "generation": chunk.generation,
        "vector_id": build_vector_id(document_id, chunk.generation, chunk.chunk_index),
    }

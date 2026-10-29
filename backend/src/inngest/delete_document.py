from datetime import UTC, datetime

from sqlmodel import Session, select

import inngest
from src.db.models import Chunk, Document, DocumentStatus
from src.db.session import engine
from src.inngest.client import get_inngest_client
from src.providers.runtime import get_object_storage, get_vector_store
from src.services import ingestion as ingestion_service

client = get_inngest_client()


@client.create_function(
    fn_id="document-delete-requested",
    trigger=inngest.TriggerEvent(event="document/delete.requested.v1"),
)
def document_delete_requested(ctx: inngest.ContextSync) -> dict:
    data = ctx.event.data
    document_id = str(data["document_id"])
    owner_id = str(data["owner_id"])
    object_key = str(data.get("object_key") or "")
    generation = int(data.get("generation") or 0)

    storage = get_object_storage()
    vectors = get_vector_store()

    def cancel_and_delete_vectors() -> dict:
        with Session(engine) as session:
            ingestion_service.cancel_jobs_for_document(session, document_id)
            doc = session.get(Document, document_id)
            gens = set()
            if generation:
                gens.add(generation)
            if doc is not None:
                gens.add(doc.active_generation)
                if doc.pending_generation:
                    gens.add(doc.pending_generation)
            for gen in gens:
                if gen and gen > 0:
                    try:
                        vectors.delete_by_document_generation(
                            namespace=owner_id,
                            document_id=document_id,
                            generation=gen,
                        )
                    except Exception:
                        pass
            chunks = session.exec(
                select(Chunk).where(Chunk.document_id == document_id)
            ).all()
            for chunk in chunks:
                session.delete(chunk)
            session.commit()
            return {"generations": sorted(gens), "chunks_removed": len(chunks)}

    result = ctx.step.run("cancel-and-delete-vectors", cancel_and_delete_vectors)

    def cleanup_objects() -> dict:
        deleted = 0
        if object_key:
            try:
                storage.delete(object_key)
                deleted += 1
            except Exception:
                pass
        prefix = f"users/{owner_id}/documents/{document_id}/"
        items, _ = storage.list_prefix(prefix)
        for item in items:
            key = item.get("Key")
            if key:
                try:
                    storage.delete(key)
                    deleted += 1
                except Exception:
                    pass
        return {"objects_deleted": deleted}

    cleanup = ctx.step.run("cleanup-objects", cleanup_objects)

    def finalize() -> dict:
        with Session(engine) as session:
            doc = session.get(Document, document_id)
            if doc is None:
                return {"status": "missing"}
            doc.status = DocumentStatus.DELETED
            doc.deleted_at = datetime.now(UTC)
            doc.updated_at = datetime.now(UTC)
            doc.status_message = "Deleted"
            session.add(doc)
            session.commit()
            return {"status": "deleted"}

    final = ctx.step.run("finalize-deleted", finalize)
    return {**result, **cleanup, **final}

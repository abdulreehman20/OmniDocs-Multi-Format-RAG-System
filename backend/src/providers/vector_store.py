from pinecone import Pinecone

from src.config import Settings
from src.providers.protocols import VectorRecord


class PineconeVectorStore:
    """Pinecone document-schema index (Documents API, API version 2026-07+).

    ``omni-rag`` declares a dense_vector field named ``embeddings`` (2048-d).
    Classic ``index.upsert`` / vector delete endpoints return 400 on this index.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is required for vector store")
        if not settings.pinecone_index_host and not settings.pinecone_index_name:
            raise ValueError(
                "PINECONE_INDEX_HOST or PINECONE_INDEX_NAME is required "
                "(set in backend/.env and restart uvicorn if it was empty at boot)"
            )
        self._dense_field = settings.pinecone_dense_field
        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        if settings.pinecone_index_host:
            self._index = self._pc.index(host=settings.pinecone_index_host)
        else:
            self._index = self._pc.index(name=settings.pinecone_index_name)  # type: ignore[arg-type]

    def upsert(self, *, namespace: str, vectors: list[VectorRecord]) -> None:
        if not vectors:
            return
        documents = [_to_document(v, dense_field=self._dense_field) for v in vectors]
        self._index.documents.upsert(namespace=namespace, documents=documents)

    def delete_by_document_generation(
        self,
        *,
        namespace: str,
        document_id: str,
        generation: int,
    ) -> None:
        self._index.documents.delete(
            namespace=namespace,
            filter={
                "document_id": {"$eq": document_id},
                "generation": {"$eq": generation},
            },
        )


def _to_document(record: VectorRecord, *, dense_field: str) -> dict:
    """Flatten VectorRecord into a Documents API body (top-level metadata keys)."""
    if dense_field in record["metadata"]:
        raise ValueError(f"metadata must not contain dense field name {dense_field!r}")
    doc: dict = {
        "_id": record["id"],
        dense_field: record["values"],
        **record["metadata"],
    }
    return doc

from pinecone import Pinecone

from src.config import Settings
from src.providers.protocols import VectorRecord


class PineconeVectorStore:
    def __init__(self, settings: Settings) -> None:
        if not settings.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is required for vector store")
        if not settings.pinecone_index_host and not settings.pinecone_index_name:
            raise ValueError("PINECONE_INDEX_HOST or PINECONE_INDEX_NAME is required")
        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        if settings.pinecone_index_host:
            self._index = self._pc.Index(host=settings.pinecone_index_host)
        else:
            self._index = self._pc.Index(settings.pinecone_index_name)  # type: ignore[arg-type]

    def upsert(self, *, namespace: str, vectors: list[VectorRecord]) -> None:
        if not vectors:
            return
        payload = [
            {
                "id": v["id"],
                "values": v["values"],
                "metadata": v["metadata"],
            }
            for v in vectors
        ]
        self._index.upsert(vectors=payload, namespace=namespace)

    def delete_by_document_generation(
        self,
        *,
        namespace: str,
        document_id: str,
        generation: int,
    ) -> None:
        self._index.delete(
            filter={
                "document_id": {"$eq": document_id},
                "generation": {"$eq": generation},
            },
            namespace=namespace,
        )

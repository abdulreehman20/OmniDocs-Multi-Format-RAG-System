from typing import Protocol, TypedDict


class ObjectStorage(Protocol):
    def create_upload_url(
        self,
        key: str,
        content_type: str,
        expires_seconds: int = 300,
    ) -> str: ...

    def create_download_url(
        self,
        key: str,
        expires_seconds: int = 300,
    ) -> str: ...

    def head(self, key: str) -> dict: ...

    def download_to_file(
        self,
        key: str,
        destination: str,
    ) -> None: ...

    def upload_file(
        self,
        key: str,
        source: str,
        content_type: str,
    ) -> None: ...

    def delete(self, key: str) -> None: ...

    def list_prefix(
        self,
        prefix: str,
        continuation: str | None = None,
    ) -> tuple[list[dict], str | None]: ...


class EmbeddingProvider(Protocol):
    @property
    def model_id(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class VectorRecord(TypedDict):
    id: str
    values: list[float]
    metadata: dict


class VectorMatch(TypedDict):
    id: str
    score: float
    metadata: dict


class VectorStore(Protocol):
    def upsert(self, *, namespace: str, vectors: list[VectorRecord]) -> None: ...

    def query(
        self,
        *,
        namespace: str,
        vector: list[float],
        top_k: int,
        filter: dict | None = None,
    ) -> list[VectorMatch]: ...

    def delete_by_document_generation(
        self,
        *,
        namespace: str,
        document_id: str,
        generation: int,
    ) -> None: ...

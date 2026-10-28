from typing import Protocol


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

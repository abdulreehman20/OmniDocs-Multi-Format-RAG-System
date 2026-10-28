from pathlib import Path


class FakeObjectStorage:
    """In-memory ObjectStorage for unit tests. Not for production use."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._content_types: dict[str, str] = {}

    def create_upload_url(
        self,
        key: str,
        content_type: str,
        expires_seconds: int = 300,
    ) -> str:
        _ = expires_seconds
        self._content_types[key] = content_type
        return f"fake://upload/{key}"

    def create_download_url(
        self,
        key: str,
        expires_seconds: int = 300,
    ) -> str:
        _ = expires_seconds
        if key not in self._objects:
            raise KeyError(key)
        return f"fake://download/{key}"

    def head(self, key: str) -> dict:
        if key not in self._objects:
            raise KeyError(key)
        body = self._objects[key]
        return {
            "ContentLength": len(body),
            "ContentType": self._content_types.get(key, "application/octet-stream"),
        }

    def download_to_file(self, key: str, destination: str) -> None:
        if key not in self._objects:
            raise KeyError(key)
        Path(destination).write_bytes(self._objects[key])

    def upload_file(self, key: str, source: str, content_type: str) -> None:
        self._objects[key] = Path(source).read_bytes()
        self._content_types[key] = content_type

    def delete(self, key: str) -> None:
        self._objects.pop(key, None)
        self._content_types.pop(key, None)

    def list_prefix(
        self,
        prefix: str,
        continuation: str | None = None,
    ) -> tuple[list[dict], str | None]:
        _ = continuation
        items = [
            {
                "Key": key,
                "Size": len(body),
                "ContentType": self._content_types.get(key),
            }
            for key, body in sorted(self._objects.items())
            if key.startswith(prefix)
        ]
        return items, None

    def put_bytes(
        self,
        key: str,
        body: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Test helper: store bytes without going through a file path."""
        self._objects[key] = body
        self._content_types[key] = content_type

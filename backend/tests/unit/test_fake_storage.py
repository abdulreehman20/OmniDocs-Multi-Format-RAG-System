from pathlib import Path

import pytest
from src.providers import FakeObjectStorage


def test_fake_object_storage_roundtrip(tmp_path: Path) -> None:
    storage = FakeObjectStorage()
    key = "users/u1/documents/d1/original"
    source = tmp_path / "upload.bin"
    dest = tmp_path / "download.bin"
    source.write_bytes(b"hello-rag")

    upload_url = storage.create_upload_url(key, "text/plain")
    assert upload_url.startswith("fake://upload/")

    storage.upload_file(key, str(source), "text/plain")
    meta = storage.head(key)
    assert meta["ContentLength"] == 9
    assert meta["ContentType"] == "text/plain"

    download_url = storage.create_download_url(key)
    assert download_url.startswith("fake://download/")

    storage.download_to_file(key, str(dest))
    assert dest.read_bytes() == b"hello-rag"

    listed, continuation = storage.list_prefix("users/u1/")
    assert continuation is None
    assert len(listed) == 1
    assert listed[0]["Key"] == key

    storage.delete(key)
    with pytest.raises(KeyError):
        storage.head(key)


def test_fake_object_storage_put_bytes() -> None:
    storage = FakeObjectStorage()
    storage.put_bytes("a/b", b"xyz", "application/octet-stream")
    assert storage.head("a/b")["ContentLength"] == 3

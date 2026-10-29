from uuid import uuid4

from src.api import deps as api_deps
from src.providers.fakes import FakeObjectStorage


def _init(client, headers, *, filename="notes.md", mime="text/markdown", size=11):
    return client.post(
        "/api/v1/uploads/init",
        headers=headers,
        json={
            "filename": filename,
            "mime_type": mime,
            "byte_size": size,
            "idempotency_key": str(uuid4()),
        },
    )


def test_reject_unsupported_filetype(client, auth_header_user_a) -> None:
    response = _init(
        client,
        auth_header_user_a,
        filename="virus.exe",
        mime="application/octet-stream",
        size=10,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "unsupported_file_type"


def test_upload_complete_and_ownership(
    client,
    auth_header_user_a,
    auth_header_user_b,
) -> None:
    init = _init(client, auth_header_user_a, size=5)
    assert init.status_code == 200
    body = init.json()
    document_id = body["document_id"]
    object_key = body["object_key"]

    storage = api_deps._test_storage
    assert isinstance(storage, FakeObjectStorage)
    storage.put_bytes(object_key, b"hello", "text/markdown")

    complete = client.post(
        f"/api/v1/documents/{document_id}/complete",
        headers=auth_header_user_a,
    )
    assert complete.status_code == 202
    assert complete.json()["status"] == "queued"

    listed = client.get("/api/v1/documents", headers=auth_header_user_a)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    other = client.get(f"/api/v1/documents/{document_id}", headers=auth_header_user_b)
    assert other.status_code == 404

    download = client.get(
        f"/api/v1/documents/{document_id}/download",
        headers=auth_header_user_a,
    )
    assert download.status_code == 200
    assert "download_url" in download.json()

    foreign_download = client.get(
        f"/api/v1/documents/{document_id}/download",
        headers=auth_header_user_b,
    )
    assert foreign_download.status_code == 404


def test_complete_without_object(client, auth_header_user_a) -> None:
    init = _init(client, auth_header_user_a, size=4)
    document_id = init.json()["document_id"]
    complete = client.post(
        f"/api/v1/documents/{document_id}/complete",
        headers=auth_header_user_a,
    )
    assert complete.status_code == 400
    assert complete.json()["detail"] == "object_missing"


def test_delete_tombstone(client, auth_header_user_a) -> None:
    init = _init(client, auth_header_user_a, size=3)
    document_id = init.json()["document_id"]
    object_key = init.json()["object_key"]
    storage = api_deps._test_storage
    assert isinstance(storage, FakeObjectStorage)
    storage.put_bytes(object_key, b"abc", "text/markdown")
    client.post(f"/api/v1/documents/{document_id}/complete", headers=auth_header_user_a)

    deleted = client.post(
        f"/api/v1/documents/{document_id}/delete",
        headers=auth_header_user_a,
    )
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"

    listed = client.get("/api/v1/documents", headers=auth_header_user_a)
    assert listed.json() == []


def test_limits(client, auth_header_user_a) -> None:
    response = client.get("/api/v1/limits", headers=auth_header_user_a)
    assert response.status_code == 200
    body = response.json()
    assert body["max_file_size_bytes"] == 26_214_400
    assert body["max_files_per_selection"] == 6
    assert ".pdf" in body["accepted_extensions"]

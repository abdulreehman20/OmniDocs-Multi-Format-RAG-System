from datetime import UTC, datetime, timedelta

from src.config import Settings
from src.db.models import Document, DocumentStatus, UploadSession, User
from src.inngest.outbox_reconcile import run_outbox_reconcile
from src.providers.fakes import FakeObjectStorage, FakeVectorStore
from src.services.maintenance import (
    cleanup_abandoned_uploads,
    cleanup_orphan_vectors,
    dispatch_pending_outbox,
)


def _settings(**kwargs) -> Settings:
    base = dict(
        database_url="sqlite://",
        database_url_pooled="sqlite://",
        neon_auth_base_url="https://auth.example.neon.tech/neondb/auth",
        maintenance_dry_run=False,
        abandoned_upload_ttl_seconds=3600,
        maintenance_batch_size=50,
    )
    base.update(kwargs)
    return Settings(**base)


def test_abandoned_upload_skips_ready_docs(session):
    session.add(User(id="user-a", email="a@example.com"))
    session.add(
        Document(
            id="doc-ready",
            owner_id="user-a",
            filename="a.md",
            source_type="markdown",
            mime_type="text/markdown",
            byte_size=1,
            object_bucket="documents",
            object_key="users/user-a/documents/doc-ready/file.md",
            status=DocumentStatus.READY,
            active_generation=1,
        )
    )
    session.add(
        UploadSession(
            id="sess-1",
            document_id="doc-ready",
            owner_id="user-a",
            expected_size=1,
            mime_type="text/markdown",
            object_key="users/user-a/documents/doc-ready/file.md",
            expires_at=datetime.now(UTC) - timedelta(hours=2),
            completed=False,
            idempotency_key="idem-ready",
        )
    )
    session.commit()
    storage = FakeObjectStorage()
    storage.put_bytes("users/user-a/documents/doc-ready/file.md", b"x")
    result = cleanup_abandoned_uploads(session, storage, _settings())
    doc = session.get(Document, "doc-ready")
    assert doc is not None
    assert doc.status == DocumentStatus.READY
    assert result["documents_marked_deleted"] == 0


def test_abandoned_upload_cleans_pending(session):
    session.add(User(id="user-a", email="a@example.com"))
    session.add(
        Document(
            id="doc-pending",
            owner_id="user-a",
            filename="b.md",
            source_type="markdown",
            mime_type="text/markdown",
            byte_size=1,
            object_bucket="documents",
            object_key="users/user-a/documents/doc-pending/file.md",
            status=DocumentStatus.UPLOAD_PENDING,
            active_generation=0,
        )
    )
    session.add(
        UploadSession(
            id="sess-2",
            document_id="doc-pending",
            owner_id="user-a",
            expected_size=1,
            mime_type="text/markdown",
            object_key="users/user-a/documents/doc-pending/file.md",
            expires_at=datetime.now(UTC) - timedelta(hours=2),
            completed=False,
            idempotency_key="idem-pending",
        )
    )
    session.commit()
    storage = FakeObjectStorage()
    storage.put_bytes("users/user-a/documents/doc-pending/file.md", b"x")
    result = cleanup_abandoned_uploads(session, storage, _settings())
    assert result["documents_marked_deleted"] == 1
    doc = session.get(Document, "doc-pending")
    assert doc is not None
    assert doc.status == DocumentStatus.DELETED


def test_orphan_vectors_skips_active_generation(session):
    session.add(User(id="user-a", email="a@example.com"))
    session.add(
        Document(
            id="doc-1",
            owner_id="user-a",
            filename="a.md",
            source_type="markdown",
            mime_type="text/markdown",
            byte_size=1,
            object_bucket="documents",
            object_key="k",
            status=DocumentStatus.READY,
            active_generation=2,
        )
    )
    session.commit()
    store = FakeVectorStore()
    store.upsert(
        namespace="user-a",
        vectors=[
            {
                "id": "doc-1:2:0",
                "values": [0.1, 0.2],
                "metadata": {"document_id": "doc-1", "generation": 2},
            },
            {
                "id": "doc-1:1:0",
                "values": [0.1, 0.2],
                "metadata": {"document_id": "doc-1", "generation": 1},
            },
        ],
    )
    # Mark stale chunk so cleanup finds generation 1
    from src.db.models import Chunk

    session.add(
        Chunk(
            id="c-stale",
            owner_id="user-a",
            document_id="doc-1",
            generation=1,
            vector_id="doc-1:1:0",
            chunk_index=0,
            text="old",
            text_sha256="x",
            state="active",
        )
    )
    session.commit()
    cleanup_orphan_vectors(session, store, _settings())
    assert "doc-1:2:0" in store.vectors["user-a"]
    assert "doc-1:1:0" not in store.vectors["user-a"]


def test_outbox_helper_callable(session):
    result = dispatch_pending_outbox(session, limit=10)
    assert result["pending_seen"] == 0
    # Shared cron helper must be a plain function.
    assert callable(run_outbox_reconcile)

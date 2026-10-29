from src.ai.ingestion.pipeline import build_vector_id
from src.db.models import Document, DocumentStatus, IngestionJob, User
from src.providers.fakes import FakeEmbeddingProvider, FakeVectorStore
from src.services import ingestion as ingestion_service


def test_fake_embed_upsert_idempotent() -> None:
    emb = FakeEmbeddingProvider(dimension=4)
    store = FakeVectorStore()
    texts = ["hello", "world"]
    vectors = emb.embed_documents(texts)
    payload = [
        {
            "id": build_vector_id("d1", 1, i),
            "values": v,
            "metadata": {"document_id": "d1", "generation": 1},
        }
        for i, v in enumerate(vectors)
    ]
    store.upsert(namespace="u1", vectors=payload)
    store.upsert(namespace="u1", vectors=payload)
    assert len(store.vectors["u1"]) == 2
    store.delete_by_document_generation(namespace="u1", document_id="d1", generation=1)
    assert store.vectors["u1"] == {}


def test_claim_rejects_deleted(session) -> None:
    session.add(User(id="u1", email="u@example.com"))
    session.commit()
    doc = Document(
        id="d1",
        owner_id="u1",
        filename="a.txt",
        source_type="text",
        mime_type="text/plain",
        byte_size=1,
        object_bucket="b",
        object_key="users/u1/documents/d1/original",
        status=DocumentStatus.DELETED,
    )
    job = IngestionJob(id="j1", owner_id="u1", document_id="d1", generation=1)
    session.add(doc)
    session.add(job)
    session.commit()

    try:
        ingestion_service.claim_job(session, document_id="d1", job_id="j1", generation=1)
        raised = False
    except ingestion_service.IngestionConflictError as exc:
        raised = True
        assert exc.code == "document_deleted"
    assert raised


def test_finalize_promotes_generation(session, settings) -> None:
    session.add(User(id="u1", email="u@example.com"))
    session.commit()
    doc = Document(
        id="d1",
        owner_id="u1",
        filename="a.txt",
        source_type="text",
        mime_type="text/plain",
        byte_size=1,
        object_bucket="b",
        object_key="users/u1/documents/d1/original",
        status=DocumentStatus.PROCESSING,
        pending_generation=1,
    )
    job = IngestionJob(
        id="j1",
        owner_id="u1",
        document_id="d1",
        generation=1,
        status="processing",
    )
    session.add(doc)
    session.add(job)
    session.commit()

    ingestion_service.finalize_generation(
        session,
        settings,
        document_id="d1",
        job_id="j1",
        generation=1,
        chunk_count=3,
        content_sha256="abc",
    )
    session.refresh(doc)
    session.refresh(job)
    assert doc.status == DocumentStatus.READY
    assert doc.active_generation == 1
    assert doc.pending_generation is None
    assert doc.chunk_count == 3
    assert doc.corpus_version == 1
    assert job.status == "succeeded"


def test_retry_only_failed(client, session, auth_header_user_a) -> None:
    session.add(User(id="user-a", email="a@example.com"))
    session.commit()
    doc = Document(
        id="d1",
        owner_id="user-a",
        filename="a.txt",
        source_type="text",
        mime_type="text/plain",
        byte_size=1,
        object_bucket="b",
        object_key="users/user-a/documents/d1/original",
        status=DocumentStatus.READY,
    )
    session.add(doc)
    session.commit()

    response = client.post("/api/v1/documents/d1/retry", headers=auth_header_user_a)
    assert response.status_code == 409

    doc.status = DocumentStatus.FAILED
    session.add(doc)
    session.commit()
    response = client.post("/api/v1/documents/d1/retry", headers=auth_header_user_a)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"

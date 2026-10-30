from datetime import UTC, datetime

from src.api import deps as api_deps
from src.db.models import Chunk, Document, DocumentStatus, User
from src.providers.fakes import FakeEmbeddingProvider, FakeVectorStore


class FakeLLM:
    def stream(self, messages):
        class Chunk:
            content = "Widgets are great [S1]. Invented [S99]."

        yield Chunk()

    async def astream(self, messages):
        class Chunk:
            content = "Widgets are great [S1]. Invented [S99]."

        yield Chunk()


def _ensure_user(session, user_id: str) -> None:
    if session.get(User, user_id) is None:
        session.add(User(id=user_id, email=f"{user_id}@example.com"))
        session.commit()


def _ready_doc_with_chunk(session, *, owner_id: str, doc_id: str = "doc-1") -> None:
    _ensure_user(session, owner_id)
    session.add(
        Document(
            id=doc_id,
            owner_id=owner_id,
            filename="notes.md",
            source_type="markdown",
            mime_type="text/markdown",
            byte_size=12,
            object_bucket="documents",
            object_key=f"{owner_id}/{doc_id}",
            status=DocumentStatus.READY,
            active_generation=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    session.add(
        Chunk(
            id="chunk-1",
            owner_id=owner_id,
            document_id=doc_id,
            generation=1,
            vector_id="vec-1",
            chunk_index=0,
            text="Widgets are great for assembly.",
            text_sha256="x",
            token_estimate=8,
            locator={"heading": "Widgets"},
            state="active",
        )
    )
    session.commit()


def test_conversation_ownership_404(client, session, auth_header_user_a, auth_header_user_b):
    _ensure_user(session, "user-a")
    create = client.post(
        "/api/v1/conversations",
        headers=auth_header_user_a,
        json={"title": "Mine"},
    )
    assert create.status_code == 201
    conv_id = create.json()["id"]

    foreign = client.get(f"/api/v1/conversations/{conv_id}", headers=auth_header_user_b)
    assert foreign.status_code == 404


def test_chat_rejects_non_ready_docs(client, session, auth_header_user_a):
    _ensure_user(session, "user-a")
    session.add(
        Document(
            id="doc-pending",
            owner_id="user-a",
            filename="x.md",
            source_type="markdown",
            mime_type="text/markdown",
            byte_size=1,
            object_bucket="documents",
            object_key="user-a/doc-pending",
            status=DocumentStatus.QUEUED,
            active_generation=0,
        )
    )
    session.commit()
    conv = client.post(
        "/api/v1/conversations",
        headers=auth_header_user_a,
        json={"selected_document_ids": ["doc-pending"]},
    )
    assert conv.status_code == 400


def test_chat_stream_and_citation_validation(client, session, auth_header_user_a, monkeypatch):
    _ready_doc_with_chunk(session, owner_id="user-a")
    embeddings = FakeEmbeddingProvider()
    store = FakeVectorStore()
    qvec = embeddings.embed_query("widgets")
    store.upsert(
        namespace="user-a",
        vectors=[
            {
                "id": "vec-1",
                "values": qvec,
                "metadata": {
                    "owner_id": "user-a",
                    "document_id": "doc-1",
                    "generation": 1,
                },
            }
        ],
    )
    api_deps._test_embeddings = embeddings
    api_deps._test_vectors = store

    from src.services import chat as chat_service

    original = chat_service.run_chat_stream

    async def wrapped(*args, **kwargs):
        kwargs["llm"] = FakeLLM()
        async for item in original(*args, **kwargs):
            yield item

    monkeypatch.setattr(chat_service, "run_chat_stream", wrapped)

    conv = client.post(
        "/api/v1/conversations",
        headers=auth_header_user_a,
        json={"selected_document_ids": ["doc-1"]},
    )
    assert conv.status_code == 201
    conv_id = conv.json()["id"]

    with client.stream(
        "POST",
        "/api/v1/chat",
        headers=auth_header_user_a,
        json={
            "conversation_id": conv_id,
            "message": "What about widgets?",
            "idempotency_key": "idem-1",
        },
    ) as response:
        assert response.status_code == 200
        assert response.headers.get("x-vercel-ai-ui-message-stream") == "v1"
        body = "".join(response.iter_text())
        assert "text-delta" in body
        assert "[DONE]" in body

    messages = client.get(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=auth_header_user_a,
    )
    assert messages.status_code == 200
    rows = messages.json()
    assert len(rows) >= 2
    assistant = [m for m in rows if m["role"] == "assistant"][-1]
    assert assistant["status"] == "completed"
    labels = [c["label"] for c in assistant["citations"]]
    assert "S1" in labels
    assert "S99" not in labels

    # Regenerate does not add another user message.
    user_count_before = sum(1 for m in rows if m["role"] == "user")
    with client.stream(
        "POST",
        "/api/v1/chat/regenerate",
        headers=auth_header_user_a,
        json={"conversation_id": conv_id},
    ) as response:
        assert response.status_code == 200
        _ = "".join(response.iter_text())

    messages2 = client.get(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=auth_header_user_a,
    ).json()
    user_count_after = sum(1 for m in messages2 if m["role"] == "user")
    assert user_count_after == user_count_before


def test_citation_resolve_authz(client, session, auth_header_user_a, auth_header_user_b, monkeypatch):
    _ready_doc_with_chunk(session, owner_id="user-a")
    embeddings = FakeEmbeddingProvider()
    store = FakeVectorStore()
    store.upsert(
        namespace="user-a",
        vectors=[
            {
                "id": "vec-1",
                "values": embeddings.embed_query("widgets"),
                "metadata": {
                    "owner_id": "user-a",
                    "document_id": "doc-1",
                    "generation": 1,
                },
            }
        ],
    )
    api_deps._test_embeddings = embeddings
    api_deps._test_vectors = store

    from src.services import chat as chat_service

    original = chat_service.run_chat_stream

    async def wrapped(*args, **kwargs):
        kwargs["llm"] = FakeLLM()
        async for item in original(*args, **kwargs):
            yield item

    monkeypatch.setattr(chat_service, "run_chat_stream", wrapped)

    conv_id = client.post(
        "/api/v1/conversations",
        headers=auth_header_user_a,
        json={"selected_document_ids": ["doc-1"]},
    ).json()["id"]

    with client.stream(
        "POST",
        "/api/v1/chat",
        headers=auth_header_user_a,
        json={"conversation_id": conv_id, "message": "widgets?", "idempotency_key": "c1"},
    ) as response:
        _ = "".join(response.iter_text())

    assistant = [
        m
        for m in client.get(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=auth_header_user_a,
        ).json()
        if m["role"] == "assistant"
    ][-1]
    cite_id = assistant["citations"][0]["id"]

    ok = client.get(f"/api/v1/citations/{cite_id}", headers=auth_header_user_a)
    assert ok.status_code == 200
    assert ok.json()["filename"] == "notes.md"

    denied = client.get(f"/api/v1/citations/{cite_id}", headers=auth_header_user_b)
    assert denied.status_code == 404

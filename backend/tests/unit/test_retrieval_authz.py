import pytest
from sqlmodel import Session

from src.ai.rag.retrieval import retrieve_for_chat
from src.config import Settings
from src.db.models import Chunk, Document, DocumentStatus, User
from src.providers.fakes import FakeEmbeddingProvider, FakeVectorStore


def _seed_doc(
    session: Session,
    *,
    owner_id: str,
    doc_id: str,
    status: str = DocumentStatus.READY,
    generation: int = 1,
) -> Document:
    if session.get(User, owner_id) is None:
        session.add(User(id=owner_id, email=f"{owner_id}@example.com"))
    doc = Document(
        id=doc_id,
        owner_id=owner_id,
        filename="a.md",
        source_type="markdown",
        mime_type="text/markdown",
        byte_size=10,
        object_bucket="documents",
        object_key=f"{owner_id}/{doc_id}",
        status=status,
        active_generation=generation,
    )
    session.add(doc)
    session.commit()
    return doc


def test_retrieve_rejects_non_ready(session: Session, settings: Settings):
    doc = _seed_doc(session, owner_id="user-a", doc_id="doc-1", status=DocumentStatus.QUEUED)
    with pytest.raises(PermissionError):
        retrieve_for_chat(
            session,
            settings=settings,
            embeddings=FakeEmbeddingProvider(),
            vectors=FakeVectorStore(),
            owner_id="user-a",
            documents=[doc],
            query="hello",
        )


def test_retrieve_filters_owner_namespace(session: Session, settings: Settings):
    doc = _seed_doc(session, owner_id="user-a", doc_id="doc-1")
    chunk = Chunk(
        id="chunk-1",
        owner_id="user-a",
        document_id="doc-1",
        generation=1,
        vector_id="vec-1",
        chunk_index=0,
        text="Alpha content about widgets",
        text_sha256="abc",
        token_estimate=10,
        locator={"heading": "Widgets"},
        state="active",
    )
    session.add(chunk)
    session.commit()

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
    # Foreign namespace vector should never be queried.
    store.upsert(
        namespace="user-b",
        vectors=[
            {
                "id": "vec-foreign",
                "values": qvec,
                "metadata": {
                    "owner_id": "user-b",
                    "document_id": "doc-x",
                    "generation": 1,
                },
            }
        ],
    )

    result = retrieve_for_chat(
        session,
        settings=settings,
        embeddings=embeddings,
        vectors=store,
        owner_id="user-a",
        documents=[doc],
        query="widgets",
    )
    assert result.sources
    assert all(s.owner_id == "user-a" for s in result.sources)
    assert result.filter_used["owner_id"]["$eq"] == "user-a"

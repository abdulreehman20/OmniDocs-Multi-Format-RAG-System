"""Ensure generate prep commits before LLM so we do not idle in a transaction."""

from src.services import chat_pipeline


class _FakeLLM:
    def stream(self, messages):
        class Chunk:
            content = "Hello [S1]."

        yield Chunk()


def test_prepare_generate_commits_before_stream(session, monkeypatch):
    commits: list[str] = []
    original_commit = session.commit

    def tracking_commit():
        commits.append("commit")
        return original_commit()

    monkeypatch.setattr(session, "commit", tracking_commit)

    # Minimal stubs — prepare should not require a real Message if we stop early.
    # Use the public helpers with a real message row instead.
    from datetime import UTC, datetime

    from src.db.models import Conversation, Message, User

    session.add(User(id="u1", email="u1@example.com"))
    session.add(
        Conversation(
            id="c1",
            owner_id="u1",
            title="t",
            selected_document_ids=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    session.add(
        Message(
            id="a1",
            conversation_id="c1",
            owner_id="u1",
            role="assistant",
            content="",
            status="streaming",
            retrieval_config={"sources": []},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    session.commit()
    commits.clear()

    from src.config import get_settings

    settings = get_settings()
    ctx = chat_pipeline.prepare_generate_context(
        session,
        settings=settings,
        owner_id="u1",
        conversation_id="c1",
        assistant_message_id="a1",
        question="hi",
        user_message_id=None,
    )
    assert "commit" in commits
    assert ctx["question"] == "hi"
    assert ctx["sources"] == []

    # Empty sources → abstention path; still must finalize without error.
    result = chat_pipeline.stream_and_finalize_generate(
        session.get_bind(),
        settings=settings,
        ctx=ctx,
        llm=_FakeLLM(),
    )
    assert result["status"] == "completed"
    assert result["chars"] > 0

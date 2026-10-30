from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlmodel import Session, col, select

import inngest
from src.ai.rag.citations import citation_record_payload, validate_citations
from src.ai.rag.generation import astream_answer_tokens, format_llm_error
from src.ai.rag.prompts import get_active_prompt
from src.ai.rag.retrieval import retrieve_for_chat
from src.ai.rag.types import RetrievedSource
from src.config import Settings
from src.db.models import Conversation, Message, MessageCitation
from src.providers.protocols import EmbeddingProvider, VectorStore
from src.services import conversations as conversations_service


def _now() -> datetime:
    return datetime.now(UTC)


def short_chat_title(text: str, *, max_words: int = 4) -> str:
    """Build a short sidebar title (3–4 words) from the first user prompt."""
    words = [w.strip(".,!?;:\"'`") for w in text.strip().split() if w.strip(".,!?;:\"'`")]
    if not words:
        return "New chat"
    n = min(max_words, len(words))
    if n >= 4:
        n = 4
    elif n >= 3:
        n = 3
    title = " ".join(words[:n])
    return title[:80] or "New chat"


def _sse(obj: dict[str, Any] | str) -> str:
    if isinstance(obj, str):
        return f"data: {obj}\n\n"
    return f"data: {json.dumps(obj, separators=(',', ':'))}\n\n"


def history_for_conversation(
    session: Session,
    *,
    conversation_id: str,
    owner_id: str,
    limit: int,
    exclude_message_id: str | None = None,
) -> list[dict[str, str]]:
    rows = list(
        session.exec(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.owner_id == owner_id,
                col(Message.role).in_(["user", "assistant"]),
                col(Message.status).in_(["completed", "partial"]),
            )
            .order_by(Message.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit + 5)
        ).all()
    )
    rows.reverse()
    out: list[dict[str, str]] = []
    for m in rows:
        if exclude_message_id and m.id == exclude_message_id:
            continue
        if m.role in ("user", "assistant") and m.content:
            out.append({"role": m.role, "content": m.content})
    return out[-limit:]


def insert_user_message(
    session: Session,
    *,
    conversation: Conversation,
    owner_id: str,
    content: str,
    idempotency_key: str | None,
) -> Message:
    if idempotency_key:
        existing = session.exec(
            select(Message).where(
                Message.conversation_id == conversation.id,
                Message.idempotency_key == idempotency_key,
            )
        ).first()
        if existing is not None:
            return existing

    msg = Message(
        conversation_id=conversation.id,
        owner_id=owner_id,
        role="user",
        content=content,
        status="completed",
        idempotency_key=idempotency_key,
    )
    session.add(msg)
    conversation.updated_at = _now()
    if conversation.title == "New chat" and content.strip():
        conversation.title = short_chat_title(content)
    session.add(conversation)
    session.commit()
    session.refresh(msg)
    return msg


def create_assistant_placeholder(
    session: Session,
    *,
    conversation: Conversation,
    owner_id: str,
    model_id: str,
    prompt_version_id: str | None,
    retrieval_config: dict[str, Any],
) -> Message:
    msg = Message(
        conversation_id=conversation.id,
        owner_id=owner_id,
        role="assistant",
        content="",
        status="streaming",
        model_id=model_id,
        prompt_version_id=prompt_version_id,
        retrieval_config=retrieval_config,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


def finalize_assistant_message(
    session: Session,
    *,
    message: Message,
    content: str,
    status: str,
    sources: list[RetrievedSource],
    latency_ms: int,
    error_message: str | None = None,
) -> Message:
    message.content = content
    message.status = status
    message.latency_ms = latency_ms
    message.error_message = error_message
    message.updated_at = _now()
    session.add(message)

    # Clear any prior citations (regenerate).
    prior = session.exec(
        select(MessageCitation).where(MessageCitation.message_id == message.id)
    ).all()
    for c in prior:
        session.delete(c)

    if status in ("completed", "partial") and content:
        valid = validate_citations(content, sources)
        for src in valid:
            payload = citation_record_payload(src)
            session.add(
                MessageCitation(
                    message_id=message.id,
                    owner_id=message.owner_id,
                    document_id=payload["document_id"],
                    chunk_id=payload["chunk_id"],
                    label=payload["label"],
                    generation=payload["generation"],
                    filename=payload["filename"],
                    source_type=payload["source_type"],
                    locator=payload["locator"],
                    excerpt=payload["excerpt"],
                )
            )

    session.commit()
    session.refresh(message)
    return message


def prepare_chat_turn(
    session: Session,
    *,
    settings: Settings,
    embeddings: EmbeddingProvider,
    vectors: VectorStore,
    owner_id: str,
    conversation_id: str,
    question: str,
    selected_document_ids: list[str] | None,
    idempotency_key: str | None,
    insert_user: bool = True,
) -> tuple[Conversation, Message | None, Message, list[RetrievedSource], str, list[dict[str, str]]]:
    conversation = conversations_service.get_owned_conversation(
        session, owner_id, conversation_id
    )
    doc_ids = (
        list(selected_document_ids)
        if selected_document_ids is not None
        else list(conversation.selected_document_ids or [])
    )
    if selected_document_ids is not None:
        conversations_service.validate_ready_documents(
            session, owner_id=owner_id, document_ids=doc_ids, settings=settings
        )
        conversation.selected_document_ids = doc_ids
        conversation.updated_at = _now()
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

    documents = conversations_service.validate_ready_documents(
        session, owner_id=owner_id, document_ids=doc_ids, settings=settings
    )
    if not documents:
        raise conversations_service.ConversationError(
            "no_documents",
            "Select at least one ready document",
        )

    user_msg: Message | None = None
    if insert_user:
        user_msg = insert_user_message(
            session,
            conversation=conversation,
            owner_id=owner_id,
            content=question,
            idempotency_key=idempotency_key,
        )

    prompt = get_active_prompt(session)
    retrieval = retrieve_for_chat(
        session,
        settings=settings,
        embeddings=embeddings,
        vectors=vectors,
        owner_id=owner_id,
        documents=documents,
        query=question,
    )
    history = history_for_conversation(
        session,
        conversation_id=conversation.id,
        owner_id=owner_id,
        limit=settings.max_history_messages,
        exclude_message_id=user_msg.id if user_msg else None,
    )
    # Drop the just-inserted user message from history (already the current question).
    if user_msg and history and history[-1].get("content") == question:
        history = history[:-1]

    assistant = create_assistant_placeholder(
        session,
        conversation=conversation,
        owner_id=owner_id,
        model_id=settings.chat_model_id,
        prompt_version_id=prompt.id if prompt.id != "ephemeral-grounded-v1" else None,
        retrieval_config={
            "filter": retrieval.filter_used,
            "candidate_count": retrieval.candidate_count,
            "source_labels": [s.label for s in retrieval.sources],
            "max_context_chunks": settings.max_context_chunks,
        },
    )
    return conversation, user_msg, assistant, retrieval.sources, prompt.template, history


def iter_ui_message_stream(
    *,
    message_id: str,
    token_iter: Iterator[str],
) -> Iterator[str]:
    text_id = "text-1"
    yield _sse({"type": "start", "messageId": message_id})
    yield _sse({"type": "text-start", "id": text_id})
    try:
        for token in token_iter:
            if token:
                yield _sse({"type": "text-delta", "id": text_id, "delta": token})
        yield _sse({"type": "text-end", "id": text_id})
        yield _sse({"type": "finish"})
    except Exception as exc:  # noqa: BLE001
        yield _sse({"type": "error", "errorText": str(exc)})
    yield _sse("[DONE]")


async def aiter_ui_message_stream(
    *,
    message_id: str,
    token_aiter: AsyncIterator[str],
) -> AsyncIterator[str]:
    text_id = "text-1"
    yield _sse({"type": "start", "messageId": message_id})
    yield _sse({"type": "text-start", "id": text_id})
    try:
        async for token in token_aiter:
            if token:
                yield _sse({"type": "text-delta", "id": text_id, "delta": token})
        yield _sse({"type": "text-end", "id": text_id})
        yield _sse({"type": "finish"})
    except Exception as exc:  # noqa: BLE001
        yield _sse({"type": "error", "errorText": str(exc)})
    yield _sse("[DONE]")


def _dispatch_chat_event(
    *,
    owner_id: str,
    conversation_id: str,
    assistant_message_id: str,
    user_message_id: str,
    question: str,
) -> None:
    from src.inngest.client import get_inngest_client

    client = get_inngest_client()
    client.send_sync(
        inngest.Event(
            name="chat/message.requested.v1",
            data={
                "owner_id": owner_id,
                "conversation_id": conversation_id,
                "assistant_message_id": assistant_message_id,
                "user_message_id": user_message_id or None,
                "question": question,
            },
        )
    )


async def bridge_assistant_stream(
    *,
    settings: Settings,
    assistant_message_id: str,
    conversation_id: str,
    owner_id: str,
    question: str,
    user_message_id: str,
    llm: Any | None = None,
) -> AsyncIterator[str]:
    """Wait for Inngest embed+search, then stream LLM tokens live over SSE.

    Generation runs on the request path so the UI sees tokens as they arrive
    (no DB-poll lag / false \"Timed out waiting for chat job\" on slow models).
    """
    import asyncio

    from src.db.session import engine
    from src.services import chat_pipeline

    text_id = "text-1"
    yield _sse({"type": "start", "messageId": assistant_message_id})
    yield _sse({"type": "text-start", "id": text_id})

    last_stage: str | None = None
    retrieval_deadline = time.monotonic() + max(
        30, settings.chat_retrieval_timeout_seconds
    )
    sources: list[RetrievedSource] = []

    while time.monotonic() < retrieval_deadline:
        with Session(engine) as poll:
            msg = poll.get(Message, assistant_message_id)
            if msg is None:
                yield _sse({"type": "error", "errorText": "assistant message missing"})
                yield _sse("[DONE]")
                return
            cfg = dict(msg.retrieval_config or {})
            stage = cfg.get("stage")
            label = cfg.get("stage_label") or stage
            status = msg.status
            err = msg.error_message
            raw_sources = list(cfg.get("sources") or [])

        if stage and stage != last_stage:
            yield _sse(
                {
                    "type": "data-rag-progress",
                    "data": {"stage": stage, "label": label},
                }
            )
            last_stage = stage

        if status == "failed" or stage == chat_pipeline.STAGE_FAILED:
            yield _sse({"type": "error", "errorText": err or "Retrieval failed"})
            yield _sse("[DONE]")
            return

        if stage in (
            chat_pipeline.STAGE_SOURCES_READY,
            chat_pipeline.STAGE_GENERATING,
            chat_pipeline.STAGE_COMPLETED,
        ) or (raw_sources and stage not in (None, chat_pipeline.STAGE_EMBEDDING, chat_pipeline.STAGE_SEARCHING)):
            sources = [chat_pipeline.source_from_dict(s) for s in raw_sources]
            break

        await asyncio.sleep(0.15)
    else:
        yield _sse(
            {
                "type": "error",
                "errorText": "Timed out waiting for document search",
            }
        )
        yield _sse("[DONE]")
        return

    # Live generation on this SSE connection.
    started = time.perf_counter()
    with Session(engine) as session:
        chat_pipeline.set_message_stage(
            session,
            message_id=assistant_message_id,
            stage=chat_pipeline.STAGE_GENERATING,
        )
        prompt = get_active_prompt(session)
        system_template = prompt.template
        history = history_for_conversation(
            session,
            conversation_id=conversation_id,
            owner_id=owner_id,
            limit=settings.max_history_messages,
            exclude_message_id=user_message_id or None,
        )
        if history and history[-1].get("content") == question:
            history = history[:-1]
        session.commit()

    yield _sse(
        {
            "type": "data-rag-progress",
            "data": {
                "stage": chat_pipeline.STAGE_GENERATING,
                "label": chat_pipeline.STAGE_LABELS[chat_pipeline.STAGE_GENERATING],
            },
        }
    )

    parts: list[str] = []
    final_status = "completed"
    error_message: str | None = None
    last_flush = 0

    try:
        i = 0
        async for token in astream_answer_tokens(
            settings,
            system_template=system_template,
            sources=sources,
            history=history,
            question=question,
            llm=llm,
        ):
            if not token:
                continue
            parts.append(token)
            yield _sse({"type": "text-delta", "id": text_id, "delta": token})
            # Flush to DB often enough for refresh/reconnect, without blocking SSE.
            if i == 0 or (i + 1) % 2 == 0:
                try:
                    chat_pipeline._write_partial_assistant(
                        engine,
                        message_id=assistant_message_id,
                        content="".join(parts),
                    )
                    last_flush = len(parts)
                except Exception:  # noqa: BLE001
                    pass
            if i % 8 == 0:
                await asyncio.sleep(0)
            i += 1
    except Exception as exc:  # noqa: BLE001
        final_status = "failed"
        error_message = format_llm_error(exc, model_id=settings.chat_model_id)

    content = "".join(parts)
    # Soft-finish: keep visible tokens as a partial answer instead of trapping the UI.
    if final_status == "failed" and content:
        final_status = "partial"
    if final_status == "completed" and not content:
        final_status = "failed"
        error_message = error_message or "empty model response"

    if len(parts) != last_flush and content:
        try:
            chat_pipeline._write_partial_assistant(
                engine,
                message_id=assistant_message_id,
                content=content,
            )
        except Exception:  # noqa: BLE001
            pass

    latency_ms = int((time.perf_counter() - started) * 1000)
    try:
        chat_pipeline._finalize_generate(
            engine,
            assistant_message_id=assistant_message_id,
            content=content,
            final_status=final_status,
            sources=sources,
            latency_ms=latency_ms,
            error_message=error_message,
        )
    except Exception as exc:  # noqa: BLE001
        if content:
            final_status = "partial"
            error_message = error_message or str(exc)
        else:
            final_status = "failed"
            error_message = error_message or str(exc)

    # Always close the UI Message Stream so useChat leaves "streaming".
    if content:
        yield _sse({"type": "text-end", "id": text_id})
    if final_status == "failed":
        yield _sse({"type": "error", "errorText": error_message or "Chat job failed"})
    yield _sse({"type": "finish"})
    yield _sse("[DONE]")


async def _emit_message_as_ui_stream(
    session: Session,
    *,
    assistant_message_id: str,
) -> AsyncIterator[str]:
    """One-shot SSE for an already-finished assistant message (unit tests / FakeLLM)."""
    msg = session.get(Message, assistant_message_id)
    if msg is None:
        yield _sse({"type": "error", "errorText": "assistant message missing"})
        yield _sse("[DONE]")
        return
    text_id = "text-1"
    cfg = dict(msg.retrieval_config or {})
    yield _sse({"type": "start", "messageId": assistant_message_id})
    if cfg.get("stage"):
        yield _sse(
            {
                "type": "data-rag-progress",
                "data": {
                    "stage": cfg.get("stage"),
                    "label": cfg.get("stage_label"),
                },
            }
        )
    yield _sse({"type": "text-start", "id": text_id})
    if msg.content:
        yield _sse({"type": "text-delta", "id": text_id, "delta": msg.content})
    if msg.status == "failed":
        yield _sse({"type": "error", "errorText": msg.error_message or "Chat job failed"})
    else:
        yield _sse({"type": "text-end", "id": text_id})
        yield _sse({"type": "finish"})
    yield _sse("[DONE]")


async def run_chat_stream(
    session: Session,
    *,
    settings: Settings,
    embeddings: EmbeddingProvider,
    vectors: VectorStore,
    owner_id: str,
    conversation_id: str,
    question: str,
    selected_document_ids: list[str] | None = None,
    idempotency_key: str | None = None,
    insert_user: bool = True,
    llm: Any | None = None,
) -> AsyncIterator[str]:
    """Start Inngest chat job (or inline in tests) and bridge progress/tokens over SSE."""
    from src.services import chat_pipeline

    user_message_id, assistant_message_id, normalized_q = chat_pipeline.begin_chat_turn(
        session,
        settings=settings,
        owner_id=owner_id,
        conversation_id=conversation_id,
        question=question,
        selected_document_ids=selected_document_ids,
        idempotency_key=idempotency_key or str(uuid4()),
        insert_user=insert_user,
    )

    # Tests / FakeLLM: same DB session as the request (no Inngest / app-engine poll).
    if settings.environment == "test" or llm is not None:
        chat_pipeline.run_chat_pipeline(
            session,
            settings=settings,
            embeddings=embeddings,
            vectors=vectors,
            owner_id=owner_id,
            conversation_id=conversation_id,
            assistant_message_id=assistant_message_id,
            question=normalized_q,
            user_message_id=user_message_id or None,
            llm=llm,
        )
        async for event in _emit_message_as_ui_stream(
            session, assistant_message_id=assistant_message_id
        ):
            yield event
        return

    try:
        _dispatch_chat_event(
            owner_id=owner_id,
            conversation_id=conversation_id,
            assistant_message_id=assistant_message_id,
            user_message_id=user_message_id,
            question=normalized_q,
        )
    except Exception as exc:  # noqa: BLE001
        chat_pipeline.set_message_stage(
            session,
            message_id=assistant_message_id,
            stage=chat_pipeline.STAGE_FAILED,
            extra={"error_message": str(exc)},
        )
        msg = session.get(Message, assistant_message_id)
        if msg is not None:
            msg.status = "failed"
            msg.error_message = str(exc)
            session.add(msg)
            session.commit()

    async for event in bridge_assistant_stream(
        settings=settings,
        assistant_message_id=assistant_message_id,
        conversation_id=conversation_id,
        owner_id=owner_id,
        question=normalized_q,
        user_message_id=user_message_id,
        llm=llm,
    ):
        yield event


def last_user_message(
    session: Session,
    *,
    conversation_id: str,
    owner_id: str,
) -> Message | None:
    return session.exec(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.owner_id == owner_id,
            Message.role == "user",
        )
        .order_by(Message.created_at.desc())  # type: ignore[attr-defined]
    ).first()

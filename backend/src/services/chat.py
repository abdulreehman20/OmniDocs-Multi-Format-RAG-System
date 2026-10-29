from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlmodel import Session, col, select

from src.ai.rag.citations import citation_record_payload, validate_citations
from src.ai.rag.generation import astream_answer_tokens, stream_answer_tokens
from src.ai.rag.prompts import get_active_prompt
from src.ai.rag.retrieval import retrieve_for_chat
from src.ai.rag.types import RetrievedSource
from src.config import Settings
from src.db.models import Conversation, Message, MessageCitation
from src.providers.protocols import EmbeddingProvider, VectorStore
from src.services import conversations as conversations_service
from src.services.corpus import get_user_corpus_version


def _now() -> datetime:
    return datetime.now(UTC)


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
        conversation.title = content.strip()[:80]
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
    corpus_version: int | None = None,
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
        corpus_version=corpus_version,
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
        corpus_version=get_user_corpus_version(session, owner_id),
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
    started = time.perf_counter()
    (
        _conversation,
        _user_msg,
        assistant,
        sources,
        template,
        history,
    ) = prepare_chat_turn(
        session,
        settings=settings,
        embeddings=embeddings,
        vectors=vectors,
        owner_id=owner_id,
        conversation_id=conversation_id,
        question=question,
        selected_document_ids=selected_document_ids,
        idempotency_key=idempotency_key or str(uuid4()),
        insert_user=insert_user,
    )

    parts: list[str] = []
    final_status = "completed"
    error_message: str | None = None

    async def _tokens() -> AsyncIterator[str]:
        nonlocal final_status, error_message
        try:
            if llm is not None:
                for token in stream_answer_tokens(
                    settings,
                    system_template=template,
                    sources=sources,
                    history=history,
                    question=question,
                    llm=llm,
                ):
                    parts.append(token)
                    yield token
            else:
                async for token in astream_answer_tokens(
                    settings,
                    system_template=template,
                    sources=sources,
                    history=history,
                    question=question,
                ):
                    parts.append(token)
                    yield token
        except Exception as exc:  # noqa: BLE001
            final_status = "failed"
            error_message = str(exc)
            raise

    try:
        async for event in aiter_ui_message_stream(
            message_id=assistant.id,
            token_aiter=_tokens(),
        ):
            yield event
    except Exception:
        final_status = "failed" if final_status != "failed" else final_status
        if not error_message:
            error_message = "stream failed"
        # Still emit DONE via aiter which catches — but if raise before, finalize below.
        yield _sse({"type": "error", "errorText": error_message})
        yield _sse("[DONE]")
    finally:
        content = "".join(parts)
        if final_status == "completed" and not content:
            # Client may have disconnected with no tokens — treat as partial if we started.
            final_status = "partial" if parts else "failed"
        latency_ms = int((time.perf_counter() - started) * 1000)
        # Re-load message in case session state drifted.
        msg = session.get(Message, assistant.id) or assistant
        finalize_assistant_message(
            session,
            message=msg,
            content=content,
            status=final_status if final_status != "streaming" else "partial",
            sources=sources,
            latency_ms=latency_ms,
            error_message=error_message,
        )


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

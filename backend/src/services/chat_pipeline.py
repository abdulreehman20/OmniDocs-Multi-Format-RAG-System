"""Inngest-backed chat RAG pipeline (embed → search → generate).

Stage progress is written to ``Message.retrieval_config["stage"]`` so the
request-path SSE bridge / UI can show progress without coupling to Inngest.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session

from src.ai.rag.generation import format_llm_error, stream_answer_tokens
from src.ai.rag.prompts import get_active_prompt
from src.ai.rag.retrieval import retrieve_for_chat
from src.ai.rag.types import RetrievedSource
from src.config import Settings
from src.db.models import Message
from src.providers.protocols import EmbeddingProvider, VectorStore
from src.services import chat as chat_service
from src.services import conversations as conversations_service

logger = logging.getLogger(__name__)

STAGE_EMBEDDING = "embedding"
STAGE_SEARCHING = "searching"
STAGE_SOURCES_READY = "sources_ready"
STAGE_GENERATING = "generating"
STAGE_COMPLETED = "completed"
STAGE_FAILED = "failed"

STAGE_LABELS = {
    STAGE_EMBEDDING: "Embedding question…",
    STAGE_SEARCHING: "Searching documents…",
    STAGE_SOURCES_READY: "Sources ready…",
    STAGE_GENERATING: "Generating response…",
    STAGE_COMPLETED: "Done",
    STAGE_FAILED: "Failed",
}


def _now() -> datetime:
    return datetime.now(UTC)


def set_message_stage(
    session: Session,
    *,
    message_id: str,
    stage: str,
    extra: dict[str, Any] | None = None,
) -> Message:
    msg = session.get(Message, message_id)
    if msg is None:
        raise ValueError(f"message not found: {message_id}")
    cfg = dict(msg.retrieval_config or {})
    cfg["stage"] = stage
    cfg["stage_label"] = STAGE_LABELS.get(stage, stage)
    if extra:
        cfg.update(extra)
    msg.retrieval_config = cfg
    msg.updated_at = _now()
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


def source_to_dict(src: RetrievedSource) -> dict[str, Any]:
    return asdict(src)


def source_from_dict(data: dict[str, Any]) -> RetrievedSource:
    return RetrievedSource(**data)


def begin_chat_turn(
    session: Session,
    *,
    settings: Settings,
    owner_id: str,
    conversation_id: str,
    question: str,
    selected_document_ids: list[str] | None,
    idempotency_key: str | None,
    insert_user: bool = True,
) -> tuple[str, str, str]:
    """Validate docs, create user+assistant placeholders. Returns (user_id|'', assistant_id, question)."""
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

    user_msg_id = ""
    if insert_user:
        user_msg = chat_service.insert_user_message(
            session,
            conversation=conversation,
            owner_id=owner_id,
            content=question,
            idempotency_key=idempotency_key,
        )
        user_msg_id = user_msg.id

    prompt = get_active_prompt(session)
    assistant = chat_service.create_assistant_placeholder(
        session,
        conversation=conversation,
        owner_id=owner_id,
        model_id=settings.chat_model_id,
        prompt_version_id=prompt.id if prompt.id != "ephemeral-grounded-v1" else None,
        retrieval_config={
            "stage": STAGE_EMBEDDING,
            "stage_label": STAGE_LABELS[STAGE_EMBEDDING],
            "document_ids": doc_ids,
        },
    )
    return user_msg_id, assistant.id, question


def step_embed_and_search(
    session: Session,
    *,
    settings: Settings,
    embeddings: EmbeddingProvider,
    vectors: VectorStore,
    owner_id: str,
    assistant_message_id: str,
    question: str,
) -> dict[str, Any]:
    """Embed query + Pinecone search; persist sources on the assistant message."""
    assistant = set_message_stage(
        session, message_id=assistant_message_id, stage=STAGE_EMBEDDING
    )
    doc_ids = list((assistant.retrieval_config or {}).get("document_ids") or [])
    documents = conversations_service.validate_ready_documents(
        session, owner_id=owner_id, document_ids=doc_ids, settings=settings
    )

    set_message_stage(session, message_id=assistant_message_id, stage=STAGE_SEARCHING)
    # Release txn before OpenRouter embed + Pinecone (same Neon idle-in-txn risk).
    session.commit()

    # embed happens inside retrieve_for_chat via embeddings.embed_query
    retrieval = retrieve_for_chat(
        session,
        settings=settings,
        embeddings=embeddings,
        vectors=vectors,
        owner_id=owner_id,
        documents=documents,
        query=question,
    )
    sources_payload = [source_to_dict(s) for s in retrieval.sources]
    # Hand off to the HTTP SSE path for live token streaming (not Inngest generate).
    set_message_stage(
        session,
        message_id=assistant_message_id,
        stage=STAGE_SOURCES_READY,
        extra={
            "filter": retrieval.filter_used,
            "candidate_count": retrieval.candidate_count,
            "source_labels": [s.label for s in retrieval.sources],
            "sources": sources_payload,
            "max_context_chunks": settings.max_context_chunks,
        },
    )
    return {
        "candidate_count": retrieval.candidate_count,
        "source_count": len(sources_payload),
        "sources": sources_payload,
    }


def _write_partial_assistant(
    bind: Any,
    *,
    message_id: str,
    content: str,
) -> None:
    """Short-lived session so Neon never sees idle-in-transaction during LLM waits."""
    with Session(bind) as write:
        msg = write.get(Message, message_id)
        if msg is None:
            return
        msg.content = content
        msg.status = "streaming"
        msg.updated_at = _now()
        write.add(msg)
        write.commit()


def _finalize_generate(
    bind: Any,
    *,
    assistant_message_id: str,
    content: str,
    final_status: str,
    sources: list[RetrievedSource],
    latency_ms: int,
    error_message: str | None,
) -> None:
    """Persist final answer on a fresh session (survives a killed long-lived connection)."""
    with Session(bind) as write:
        assistant = write.get(Message, assistant_message_id)
        if assistant is None:
            raise ValueError(f"assistant message not found: {assistant_message_id}")
        chat_service.finalize_assistant_message(
            write,
            message=assistant,
            content=content,
            status=final_status,
            sources=sources,
            latency_ms=latency_ms,
            error_message=error_message,
        )
        stage = (
            STAGE_COMPLETED if final_status in ("completed", "partial") else STAGE_FAILED
        )
        set_message_stage(
            write,
            message_id=assistant_message_id,
            stage=stage,
            extra={"error_message": error_message} if error_message else None,
        )


def prepare_generate_context(
    session: Session,
    *,
    settings: Settings,
    owner_id: str,
    conversation_id: str,
    assistant_message_id: str,
    question: str,
    user_message_id: str | None,
) -> dict[str, Any]:
    """Load prompt/history/sources and commit so no txn is open during the LLM call."""
    assistant = session.get(Message, assistant_message_id)
    if assistant is None:
        raise ValueError(f"assistant message not found: {assistant_message_id}")

    set_message_stage(session, message_id=assistant_message_id, stage=STAGE_GENERATING)

    cfg = dict(assistant.retrieval_config or {})
    sources = [source_from_dict(s) for s in (cfg.get("sources") or [])]
    prompt = get_active_prompt(session)
    history = chat_service.history_for_conversation(
        session,
        conversation_id=conversation_id,
        owner_id=owner_id,
        limit=settings.max_history_messages,
        exclude_message_id=user_message_id or None,
    )
    if history and history[-1].get("content") == question:
        history = history[:-1]

    # End the transaction before blocking on OpenRouter — otherwise Neon raises
    # IdleInTransactionSessionTimeout (see chat generate-answer failures).
    session.commit()

    return {
        "assistant_message_id": assistant_message_id,
        "question": question,
        "system_template": prompt.template,
        "sources": sources,
        "history": history,
    }


def stream_and_finalize_generate(
    bind: Any,
    *,
    settings: Settings,
    ctx: dict[str, Any],
    llm: Any | None = None,
    started: float | None = None,
) -> dict[str, Any]:
    """Run the LLM and persist results using only short-lived DB sessions."""
    t0 = started if started is not None else time.perf_counter()
    assistant_message_id = str(ctx["assistant_message_id"])
    question = str(ctx["question"])
    system_template = str(ctx["system_template"])
    sources: list[RetrievedSource] = list(ctx["sources"])
    history: list[dict[str, str]] = list(ctx["history"])

    parts: list[str] = []
    final_status = "completed"
    error_message: str | None = None

    try:
        for i, token in enumerate(
            stream_answer_tokens(
                settings,
                system_template=system_template,
                sources=sources,
                history=history,
                question=question,
                llm=llm,
            )
        ):
            parts.append(token)
            if i == 0 or (i + 1) % 3 == 0:
                try:
                    _write_partial_assistant(
                        bind,
                        message_id=assistant_message_id,
                        content="".join(parts),
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("partial assistant write failed; continuing stream")
    except Exception as exc:  # noqa: BLE001
        final_status = "failed"
        error_message = format_llm_error(exc, model_id=settings.chat_model_id)

    content = "".join(parts)
    if final_status == "completed" and not content:
        final_status = "failed"
        error_message = error_message or "empty model response"

    latency_ms = int((time.perf_counter() - t0) * 1000)
    try:
        _finalize_generate(
            bind,
            assistant_message_id=assistant_message_id,
            content=content,
            final_status=final_status,
            sources=sources,
            latency_ms=latency_ms,
            error_message=error_message,
        )
    except Exception:
        logger.exception("finalize failed; retrying on fresh session")
        _finalize_generate(
            bind,
            assistant_message_id=assistant_message_id,
            content=content,
            final_status=final_status if final_status != "completed" else "failed",
            sources=sources,
            latency_ms=latency_ms,
            error_message=error_message or "failed to persist assistant message",
        )

    out: dict[str, Any] = {
        "status": final_status,
        "chars": len(content),
        "latency_ms": latency_ms,
    }
    if error_message:
        out["error_message"] = error_message[:500]
    return out


def step_generate(
    session: Session,
    *,
    settings: Settings,
    owner_id: str,
    conversation_id: str,
    assistant_message_id: str,
    question: str,
    user_message_id: str | None,
    llm: Any | None = None,
) -> dict[str, Any]:
    """Stream LLM tokens into the assistant message; finalize citations.

    Prefer ``prepare_generate_context`` + ``stream_and_finalize_generate`` in
    Inngest so the pool connection is released before the LLM HTTP wait.
    """
    started = time.perf_counter()
    ctx = prepare_generate_context(
        session,
        settings=settings,
        owner_id=owner_id,
        conversation_id=conversation_id,
        assistant_message_id=assistant_message_id,
        question=question,
        user_message_id=user_message_id,
    )
    return stream_and_finalize_generate(
        session.get_bind(),
        settings=settings,
        ctx=ctx,
        llm=llm,
        started=started,
    )


def run_chat_pipeline(
    session: Session,
    *,
    settings: Settings,
    embeddings: EmbeddingProvider,
    vectors: VectorStore,
    owner_id: str,
    conversation_id: str,
    assistant_message_id: str,
    question: str,
    user_message_id: str | None = None,
    llm: Any | None = None,
) -> dict[str, Any]:
    """Full pipeline for tests / sync fallback (same steps as Inngest)."""
    search = step_embed_and_search(
        session,
        settings=settings,
        embeddings=embeddings,
        vectors=vectors,
        owner_id=owner_id,
        assistant_message_id=assistant_message_id,
        question=question,
    )
    gen = step_generate(
        session,
        settings=settings,
        owner_id=owner_id,
        conversation_id=conversation_id,
        assistant_message_id=assistant_message_id,
        question=question,
        user_message_id=user_message_id,
        llm=llm,
    )
    return {**search, **gen}

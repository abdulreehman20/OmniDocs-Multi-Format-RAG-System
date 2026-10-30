from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openrouter import ChatOpenRouter

from src.ai.rag.prompts import build_system_prompt
from src.ai.rag.types import RetrievedSource
from src.config import Settings


def build_chat_model(settings: Settings) -> ChatOpenRouter:
    if not settings.openrouter_api_key and settings.environment != "test":
        raise ValueError("OPENROUTER_API_KEY is required for chat")
    # langchain_openrouter maps `timeout` to SDK timeout_ms (milliseconds).
    return ChatOpenRouter(
        model=settings.chat_model_id,
        api_key=settings.openrouter_api_key or "test-key",
        base_url=settings.openrouter_base_url,
        streaming=True,
        timeout=max(1, settings.chat_stream_timeout_seconds) * 1000,
        temperature=0.2,
    )


def format_llm_error(exc: BaseException, *, model_id: str) -> str:
    """Make OpenRouter/provider failures readable in Inngest + UI."""
    msg = str(exc).strip() or type(exc).__name__
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict) and err.get("message"):
            msg = str(err["message"])
        elif isinstance(err, str) and err:
            msg = err
    return f"{model_id}: {msg}"[:500]


def build_messages(
    *,
    system_template: str,
    sources: list[RetrievedSource],
    history: list[dict[str, str]],
    question: str,
) -> list[Any]:
    messages: list[Any] = [
        SystemMessage(content=build_system_prompt(system_template, sources)),
    ]
    for turn in history:
        role = turn.get("role")
        content = turn.get("content") or ""
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=question))
    return messages


def stream_answer_tokens(
    settings: Settings,
    *,
    system_template: str,
    sources: list[RetrievedSource],
    history: list[dict[str, str]],
    question: str,
    llm: Any | None = None,
) -> Iterator[str]:
    """Sync token stream for tests / simple callers."""
    if not sources:
        yield (
            "I couldn't find enough information in the selected documents "
            "to answer that reliably."
        )
        return

    model = llm or build_chat_model(settings)
    messages = build_messages(
        system_template=system_template,
        sources=sources,
        history=history,
        question=question,
    )
    for chunk in model.stream(messages):
        content = getattr(chunk, "content", None)
        if isinstance(content, str) and content:
            yield content
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text")
                    if text:
                        yield text
                elif isinstance(part, str) and part:
                    yield part


async def astream_answer_tokens(
    settings: Settings,
    *,
    system_template: str,
    sources: list[RetrievedSource],
    history: list[dict[str, str]],
    question: str,
    llm: Any | None = None,
) -> AsyncIterator[str]:
    if not sources:
        yield (
            "I couldn't find enough information in the selected documents "
            "to answer that reliably."
        )
        return

    model = llm or build_chat_model(settings)
    messages = build_messages(
        system_template=system_template,
        sources=sources,
        history=history,
        question=question,
    )
    async for chunk in model.astream(messages):
        content = getattr(chunk, "content", None)
        if isinstance(content, str) and content:
            yield content
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text")
                    if text:
                        yield text
                elif isinstance(part, str) and part:
                    yield part

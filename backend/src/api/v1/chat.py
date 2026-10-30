from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from src.api.deps import AppSettings, CurrentUser, DbSession, Embeddings, Vectors
from src.db.models import Message
from src.schemas.chat import ChatRequest, CitationResponse, RegenerateRequest
from src.services import chat as chat_service
from src.services import conversations as conversations_service
from src.services.conversations import ConversationError

router = APIRouter(tags=["chat"])


def _stream_headers() -> dict[str, str]:
    return {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "x-vercel-ai-ui-message-stream": "v1",
    }


def _resolve_user_message(
    session: Session,
    *,
    owner_id: str,
    conversation_id: str,
    message_id: str | None,
) -> Message:
    if message_id:
        user_msg = session.get(Message, message_id)
        if (
            user_msg is None
            or user_msg.owner_id != owner_id
            or user_msg.conversation_id != conversation_id
            or user_msg.role != "user"
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        return user_msg
    user_msg = chat_service.last_user_message(
        session,
        conversation_id=conversation_id,
        owner_id=owner_id,
    )
    if user_msg is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user message to regenerate",
        )
    return user_msg


@router.post("/chat")
async def chat_stream(
    body: ChatRequest,
    session: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
    embeddings: Embeddings,
    vectors: Vectors,
) -> StreamingResponse:
    if not body.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty message")

    async def event_gen() -> AsyncIterator[str]:
        try:
            async for chunk in chat_service.run_chat_stream(
                session,
                settings=settings,
                embeddings=embeddings,
                vectors=vectors,
                owner_id=current_user.id,
                conversation_id=body.conversation_id,
                question=body.message.strip(),
                selected_document_ids=body.selected_document_ids,
                idempotency_key=body.idempotency_key,
                insert_user=True,
            ):
                yield chunk
        except ConversationError as exc:
            yield chat_service._sse({"type": "error", "errorText": exc.message})
            yield chat_service._sse("[DONE]")

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers=_stream_headers(),
    )


@router.post("/chat/regenerate")
async def regenerate_stream(
    body: RegenerateRequest,
    session: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
    embeddings: Embeddings,
    vectors: Vectors,
) -> StreamingResponse:
    conversations_service.get_owned_conversation(
        session, current_user.id, body.conversation_id
    )
    user_msg = _resolve_user_message(
        session,
        owner_id=current_user.id,
        conversation_id=body.conversation_id,
        message_id=body.message_id,
    )
    question = user_msg.content

    async def event_gen() -> AsyncIterator[str]:
        try:
            async for chunk in chat_service.run_chat_stream(
                session,
                settings=settings,
                embeddings=embeddings,
                vectors=vectors,
                owner_id=current_user.id,
                conversation_id=body.conversation_id,
                question=question,
                selected_document_ids=None,
                idempotency_key=None,
                insert_user=False,
            ):
                yield chunk
        except ConversationError as exc:
            yield chat_service._sse({"type": "error", "errorText": exc.message})
            yield chat_service._sse("[DONE]")

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers=_stream_headers(),
    )


@router.get("/citations/{citation_id}", response_model=CitationResponse)
def get_citation(
    citation_id: str,
    session: DbSession,
    current_user: CurrentUser,
) -> CitationResponse:
    cite = conversations_service.get_owned_citation(
        session, owner_id=current_user.id, citation_id=citation_id
    )
    return CitationResponse(
        id=cite.id,
        message_id=cite.message_id,
        label=cite.label,
        document_id=cite.document_id,
        chunk_id=cite.chunk_id,
        generation=cite.generation,
        filename=cite.filename,
        source_type=cite.source_type,
        locator=cite.locator or {},
        excerpt=cite.excerpt,
    )

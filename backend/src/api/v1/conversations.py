from fastapi import APIRouter, HTTPException, status

from src.api.deps import AppSettings, CurrentUser, DbSession
from src.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
)
from src.services import conversations as conversations_service
from src.services.conversations import ConversationError

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    session: DbSession,
    current_user: CurrentUser,
) -> list[ConversationResponse]:
    rows = conversations_service.list_conversations(session, current_user.id)
    return [ConversationResponse(**conversations_service.conversation_to_dict(c)) for c in rows]


@router.post("", response_model=ConversationResponse, status_code=201)
def create_conversation(
    body: ConversationCreate,
    session: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> ConversationResponse:
    try:
        conv = conversations_service.create_conversation(
            session,
            owner_id=current_user.id,
            settings=settings,
            title=body.title,
            selected_document_ids=body.selected_document_ids,
        )
    except ConversationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    return ConversationResponse(**conversations_service.conversation_to_dict(conv))


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    session: DbSession,
    current_user: CurrentUser,
) -> ConversationResponse:
    conv = conversations_service.get_owned_conversation(
        session, current_user.id, conversation_id
    )
    return ConversationResponse(**conversations_service.conversation_to_dict(conv))


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    session: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> ConversationResponse:
    try:
        conv = conversations_service.update_conversation(
            session,
            owner_id=current_user.id,
            conversation_id=conversation_id,
            settings=settings,
            title=body.title,
            selected_document_ids=body.selected_document_ids,
            archived=body.archived,
        )
    except ConversationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    return ConversationResponse(**conversations_service.conversation_to_dict(conv))


@router.delete("/{conversation_id}", response_model=ConversationResponse)
def delete_conversation(
    conversation_id: str,
    session: DbSession,
    current_user: CurrentUser,
) -> ConversationResponse:
    conv = conversations_service.soft_delete_conversation(
        session,
        owner_id=current_user.id,
        conversation_id=conversation_id,
    )
    return ConversationResponse(**conversations_service.conversation_to_dict(conv))


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(
    conversation_id: str,
    session: DbSession,
    current_user: CurrentUser,
) -> list[MessageResponse]:
    rows = conversations_service.list_messages(
        session,
        owner_id=current_user.id,
        conversation_id=conversation_id,
    )
    return [
        MessageResponse(**conversations_service.message_to_dict(session, m)) for m in rows
    ]

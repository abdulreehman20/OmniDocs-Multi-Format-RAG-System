from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlmodel import Session, col, select

from src.config import Settings
from src.db.models import Conversation, Document, DocumentStatus, Message, MessageCitation


class ConversationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _now() -> datetime:
    return datetime.now(UTC)


def conversation_to_dict(conv: Conversation) -> dict:
    return {
        "id": conv.id,
        "title": conv.title,
        "selected_document_ids": list(conv.selected_document_ids or []),
        "archived": bool(conv.archived),
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


def get_owned_conversation(
    session: Session,
    owner_id: str,
    conversation_id: str,
) -> Conversation:
    conv = session.get(Conversation, conversation_id)
    if conv is None or conv.owner_id != owner_id or conv.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return conv


def validate_ready_documents(
    session: Session,
    *,
    owner_id: str,
    document_ids: list[str],
    settings: Settings,
) -> list[Document]:
    if len(document_ids) > settings.max_selected_documents_per_chat:
        raise ConversationError(
            "too_many_documents",
            f"At most {settings.max_selected_documents_per_chat} documents allowed",
        )
    if not document_ids:
        return []
    docs = list(
        session.exec(
            select(Document).where(
                Document.owner_id == owner_id,
                col(Document.id).in_(document_ids),
            )
        ).all()
    )
    by_id = {d.id: d for d in docs}
    ordered: list[Document] = []
    for did in document_ids:
        doc = by_id.get(did)
        if doc is None or doc.status != DocumentStatus.READY:
            raise ConversationError(
                "document_not_ready",
                "All selected documents must be owned and ready",
            )
        ordered.append(doc)
    return ordered


def list_conversations(session: Session, owner_id: str) -> list[Conversation]:
    return list(
        session.exec(
            select(Conversation)
            .where(
                Conversation.owner_id == owner_id,
                Conversation.deleted_at.is_(None),  # type: ignore[union-attr]
                Conversation.archived == False,  # noqa: E712
            )
            .order_by(Conversation.updated_at.desc())  # type: ignore[attr-defined]
        ).all()
    )


def create_conversation(
    session: Session,
    *,
    owner_id: str,
    settings: Settings,
    title: str | None = None,
    selected_document_ids: list[str] | None = None,
) -> Conversation:
    ids = list(selected_document_ids or [])
    validate_ready_documents(
        session, owner_id=owner_id, document_ids=ids, settings=settings
    )
    conv = Conversation(
        owner_id=owner_id,
        title=(title or "New chat").strip() or "New chat",
        selected_document_ids=ids,
    )
    session.add(conv)
    session.commit()
    session.refresh(conv)
    return conv


def update_conversation(
    session: Session,
    *,
    owner_id: str,
    conversation_id: str,
    settings: Settings,
    title: str | None = None,
    selected_document_ids: list[str] | None = None,
    archived: bool | None = None,
) -> Conversation:
    conv = get_owned_conversation(session, owner_id, conversation_id)
    if title is not None:
        conv.title = title.strip() or conv.title
    if selected_document_ids is not None:
        validate_ready_documents(
            session,
            owner_id=owner_id,
            document_ids=selected_document_ids,
            settings=settings,
        )
        conv.selected_document_ids = list(selected_document_ids)
    if archived is not None:
        conv.archived = archived
    conv.updated_at = _now()
    session.add(conv)
    session.commit()
    session.refresh(conv)
    return conv


def soft_delete_conversation(
    session: Session,
    *,
    owner_id: str,
    conversation_id: str,
) -> Conversation:
    conv = get_owned_conversation(session, owner_id, conversation_id)
    conv.deleted_at = _now()
    conv.updated_at = _now()
    session.add(conv)
    session.commit()
    session.refresh(conv)
    return conv


def list_messages(
    session: Session,
    *,
    owner_id: str,
    conversation_id: str,
    limit: int = 100,
) -> list[Message]:
    get_owned_conversation(session, owner_id, conversation_id)
    return list(
        session.exec(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.owner_id == owner_id,
            )
            .order_by(Message.created_at.asc())  # type: ignore[attr-defined]
            .limit(limit)
        ).all()
    )


def citations_for_message(
    session: Session,
    *,
    owner_id: str,
    message_id: str,
) -> list[MessageCitation]:
    return list(
        session.exec(
            select(MessageCitation).where(
                MessageCitation.message_id == message_id,
                MessageCitation.owner_id == owner_id,
            )
        ).all()
    )


def message_to_dict(
    session: Session,
    message: Message,
) -> dict:
    cites = citations_for_message(
        session, owner_id=message.owner_id, message_id=message.id
    )
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "status": message.status,
        "model_id": message.model_id,
        "latency_ms": message.latency_ms,
        "created_at": message.created_at.isoformat(),
        "citations": [
            {
                "id": c.id,
                "message_id": c.message_id,
                "label": c.label,
                "document_id": c.document_id,
                "chunk_id": c.chunk_id,
                "generation": c.generation,
                "filename": c.filename,
                "source_type": c.source_type,
                "locator": c.locator or {},
                "excerpt": c.excerpt,
            }
            for c in cites
        ],
    }


def get_owned_citation(
    session: Session,
    *,
    owner_id: str,
    citation_id: str,
) -> MessageCitation:
    cite = session.get(MessageCitation, citation_id)
    if cite is None or cite.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return cite

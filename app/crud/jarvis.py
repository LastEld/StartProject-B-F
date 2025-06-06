#app/crud/jarvis.py
from sqlalchemy.orm import Session
from app.models.jarvis import ChatMessage
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger("DevOS.ChatController")

class ChatControllerError(Exception):
    """Custom exception for chat controller errors."""
    pass

def save_message(
    db: Session,
    project_id: int,
    role: str,
    content: str,
    timestamp: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None,
    author: Optional[str] = None,
    ai_notes: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    is_deleted: bool = False,
) -> ChatMessage:
    """
    Сохраняет новое сообщение чата (AI/пользователь).
    """
    if not all([project_id, role, content]):
        raise ChatControllerError("Project ID, role, and content are required to save a chat message.")
    if timestamp is None:
        timestamp = datetime.utcnow()
    if metadata is not None and not isinstance(metadata, dict):
        raise ChatControllerError("Metadata must be a dictionary.")
    if attachments is not None and not isinstance(attachments, list):
        raise ChatControllerError("Attachments must be a list of dicts.")

    db_message = ChatMessage(
        project_id=project_id,
        role=role,
        content=content,
        timestamp=timestamp,
        metadata_=metadata,
        author=author,
        ai_notes=ai_notes,
        attachments=attachments or [],
        is_deleted=is_deleted,
    )
    try:
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        logger.info(f"Saved chat message {db_message.id} for project {project_id}")
        return db_message
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving chat message for project {project_id}: {e}")
        raise ChatControllerError(f"Could not save chat message: {e}")

def get_message_by_id(
    db: Session,
    message_id: int,
    include_deleted: bool = False
) -> Optional[ChatMessage]:
    """
    Получает конкретное сообщение чата по id.
    """
    query = db.query(ChatMessage).filter(ChatMessage.id == message_id)
    if not include_deleted:
        query = query.filter(ChatMessage.is_deleted == False)
    return query.first()

def get_history(
    db: Session,
    project_id: int,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    include_deleted: bool = False,
) -> List[ChatMessage]:
    """
    Возвращает историю чата для проекта, старые сообщения первыми (ASC).
    Если limit задан — возвращает только последние N сообщений, отсортированные по времени (ASC).
    """
    if not project_id:
        raise ChatControllerError("Project ID is required to get chat history.")

    base_query = db.query(ChatMessage).filter(ChatMessage.project_id == project_id)
    if not include_deleted:
        base_query = base_query.filter(ChatMessage.is_deleted == False)
    base_query = base_query.order_by(ChatMessage.timestamp.asc())

    # Если limit не указан, просто обычная пагинация (ASC)
    if limit is None:
        if offset is not None:
            base_query = base_query.offset(offset)
        return base_query.all()

    # Если limit есть — получить последние N id (DESC), затем вернуть их в правильном ASC-порядке
    subquery = (
        db.query(ChatMessage.id)
        .filter(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(limit)
        .subquery()
    )
    query = db.query(ChatMessage).filter(ChatMessage.id.in_(subquery))
    if not include_deleted:
        query = query.filter(ChatMessage.is_deleted == False)
    query = query.order_by(ChatMessage.timestamp.asc())
    if offset is not None:
        query = query.offset(offset)
    return query.all()

def soft_delete_message(db: Session, message_id: int) -> bool:
    """
    Архивирует (soft-delete) сообщение чата по id.
    """
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not msg:
        raise ChatControllerError("Chat message not found.")
    if msg.is_deleted:
        raise ChatControllerError("Message already deleted.")
    msg.is_deleted = True
    try:
        db.commit()
        logger.info(f"Soft-deleted chat message {message_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to soft-delete chat message: {e}")
        raise ChatControllerError(f"Could not delete chat message: {e}")

def restore_message(db: Session, message_id: int) -> bool:
    """
    Восстанавливает soft-deleted сообщение чата.
    """
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not msg:
        raise ChatControllerError("Chat message not found.")
    if not msg.is_deleted:
        raise ChatControllerError("Message is not archived.")
    msg.is_deleted = False
    try:
        db.commit()
        logger.info(f"Restored chat message {message_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to restore chat message: {e}")
        raise ChatControllerError(f"Could not restore chat message: {e}")

def delete_history_for_project(db: Session, project_id: int, hard: bool = False) -> int:
    """
    Удаляет все сообщения чата для проекта. Возвращает число удалённых.
    По умолчанию — soft-delete, если hard=True — физически удаляет из базы.
    """
    if not project_id:
        raise ChatControllerError("Project ID is required to delete chat history.")
    try:
        if hard:
            num_deleted = db.query(ChatMessage).filter(ChatMessage.project_id == project_id).delete()
        else:
            num_deleted = db.query(ChatMessage).filter(ChatMessage.project_id == project_id).update({"is_deleted": True})
        db.commit()
        logger.info(f"{'Deleted' if hard else 'Soft-deleted'} {num_deleted} chat messages for project {project_id}.")
        return num_deleted
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting chat history for project {project_id}: {e}")
        raise ChatControllerError(f"Could not delete chat history: {e}")

#app/crud/jarvis.py
from sqlalchemy.orm import Session
from app.models.jarvis import ChatMessage
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import httpx
import os
import json
from app.schemas.jarvis import JarvisRequest, JarvisResponse

logger = logging.getLogger("DevOS.ChatController")

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")

class ChatControllerError(Exception):
    """Custom exception for chat controller errors."""
    pass


async def ask_ollama(db: Session, request: JarvisRequest, current_user_username: str) -> JarvisResponse:
    """
    Asynchronously sends a prompt to the Ollama service and returns its response,
    while also saving the conversation if a project_id is provided.
    """
    payload = {
        "model": request.model or "llama3",  # Default to llama3
        "prompt": request.prompt,
        "stream": False,  # Keep stream False for simplicity
        "options": request.options or {}
    }

    logger.debug(f"Ollama request payload: {json.dumps(payload)}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(OLLAMA_API_URL, json=payload, timeout=60.0)
            response.raise_for_status()  # Raise an exception for 4XX or 5XX status codes
            ollama_data = response.json()

            # Map Ollama response to JarvisResponse schema
            # Ollama's created_at is a string, convert to datetime
            created_at_str = ollama_data.get("created_at", datetime.utcnow().isoformat())
            try:
                created_at_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except ValueError: # Fallback if parsing fails
                logger.warning(f"Could not parse created_at string '{created_at_str}', using utcnow().")
                created_at_dt = datetime.utcnow()

            jarvis_response_data = {
                "response": ollama_data.get("response", ""),
                "model": ollama_data.get("model", request.model or "llama3"),
                "created_at": created_at_dt,
                "done": ollama_data.get("done", True),
                "context": ollama_data.get("context"),
                "total_duration": ollama_data.get("total_duration"),
                "load_duration": ollama_data.get("load_duration"),
                "prompt_eval_count": ollama_data.get("prompt_eval_count"),
                "prompt_eval_duration": ollama_data.get("prompt_eval_duration"),
                "eval_count": ollama_data.get("eval_count"),
                "eval_duration": ollama_data.get("eval_duration"),
            }

            parsed_jarvis_response = JarvisResponse(**jarvis_response_data)

        except httpx.RequestError as e:
            logger.error(f"Error connecting to Ollama service at {OLLAMA_API_URL}: {e}")
            raise ChatControllerError(f"Could not connect to Ollama service: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.status_code} - {e.response.text}")
            raise ChatControllerError(f"Ollama API returned an error: {e.response.status_code} - {e.response.text}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON response from Ollama: {e}")
            raise ChatControllerError(f"Could not decode JSON response from Ollama: {e}")
        except Exception as e:  # Catch any other unexpected errors
            logger.error(f"Unexpected error in ask_ollama: {e}", exc_info=True) # Add exc_info for more details
            raise ChatControllerError(f"An unexpected error occurred: {e}")

    # Save user prompt and Ollama's response
    if request.project_id is not None:
        try:
            save_message(
                db=db,
                project_id=request.project_id,
                role="user",
                content=request.prompt,
                author=current_user_username,
                metadata={"model_requested": request.model or "llama3", "session_id": request.session_id}
            )

            save_message(
                db=db,
                project_id=request.project_id,
                role="assistant",
                content=parsed_jarvis_response.response,
                author="Jarvis", # Or parsed_jarvis_response.model
                metadata={
                    "model_used": parsed_jarvis_response.model,
                    "total_duration_ns": parsed_jarvis_response.total_duration,
                    "prompt_eval_count": parsed_jarvis_response.prompt_eval_count,
                    "eval_count": parsed_jarvis_response.eval_count,
                    "session_id": request.session_id
                }
            )
        except Exception as e:
            logger.error(f"Failed to save conversation messages for project_id {request.project_id}: {e}", exc_info=True)
            # Decide if this failure should raise an error or just be logged
            # For now, logging, as the primary goal (getting Ollama response) was met.

    return parsed_jarvis_response

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

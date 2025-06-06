#app/api/jarvis.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
from app.schemas.jarvis import (
    ChatMessageCreate, ChatMessageRead, ChatMessageUpdate, ChatMessageShort
)
from app.crud.jarvis import (
    save_message,
    get_history,
    delete_history_for_project,
    get_message_by_id,
    update_message,
    soft_delete_message,
    ChatControllerError,
)
from app.dependencies import get_db, get_current_active_user
from app.schemas.response import SuccessResponse
from app.models.user import User as UserModel

import logging

router = APIRouter(prefix="/jarvis", tags=["Jarvis"])
logger = logging.getLogger("DevOS.JarvisAPI")


@router.post("/chat/", response_model=ChatMessageRead)
def create_chat_message(
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Создает новое сообщение (аналог /message)."""
    try:
        msg = save_message(
            db=db,
            project_id=data.project_id,
            role=data.role,
            content=data.content,
            timestamp=data.timestamp,
            metadata=data.metadata,
            author=data.author or current_user.username,
            ai_notes=data.ai_notes,
            attachments=data.attachments,
            is_deleted=data.is_deleted,
        )
        return msg
    except Exception as e:
        logger.error(f"Failed to save chat message: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/chat/", response_model=List[ChatMessageShort])
def list_chat_messages(
    project_id: int,
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: Optional[int] = Query(None, ge=0),
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Возвращает сообщения проекта."""
    try:
        messages = get_history(db, project_id, limit=limit, offset=offset, include_deleted=include_deleted)
        return [ChatMessageShort.from_orm(m) for m in messages]
    except Exception as e:
        logger.error(f"Failed to list chat messages: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/chat/{message_id}", response_model=ChatMessageRead)
def get_chat_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    msg = get_message_by_id(db, message_id)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return msg


@router.patch("/chat/{message_id}", response_model=ChatMessageRead)
def patch_chat_message(
    message_id: int,
    data: ChatMessageUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    try:
        msg = update_message(db, message_id, data.dict(exclude_unset=True))
        return msg
    except ChatControllerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/chat/{message_id}", response_model=SuccessResponse)
def delete_chat_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    try:
        result = soft_delete_message(db, message_id)
        return SuccessResponse(result=result, detail="Message deleted")
    except ChatControllerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/message", response_model=ChatMessageRead)
def post_message(
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Сохраняет новое сообщение в чате проекта.
    """
    try:
        msg = save_message(
            db=db,
            project_id=data.project_id,
            role=data.role,
            content=data.content,
            timestamp=data.timestamp,
            metadata=data.metadata,
            author=data.author or current_user.username,
            ai_notes=data.ai_notes,
            attachments=data.attachments,
            is_deleted=data.is_deleted,
        )
        return msg
    except Exception as e:
        logger.error(f"Failed to save chat message: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/history/{project_id}", response_model=List[ChatMessageRead])
def chat_history(
    project_id: int,
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Возвращает историю чата по проекту (по умолчанию — все).
    """
    # Доступ: можно добавить проверку доступа к проекту, если есть приватные чаты
    try:
        history = get_history(db, project_id, limit=limit, offset=offset)
        return history
    except Exception as e:
        logger.error(f"Failed to get chat history for project {project_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/history/{project_id}", response_model=SuccessResponse)
def delete_chat_history(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Удаляет (soft/hard) историю чата проекта.
    """
    try:
        deleted = delete_history_for_project(db, project_id)
        return SuccessResponse(result=deleted, detail="Chat history deleted")
    except Exception as e:
        logger.error(f"Failed to delete chat history for project {project_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/history/{project_id}/last", response_model=List[ChatMessageShort])
def last_messages(
    project_id: int,
    n: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Возвращает последние N сообщений (например, для prompt генерации AI).
    """
    try:
        history = get_history(db, project_id, limit=n)
        # Возвращаем последние n, если limit меньше всей истории
        return [ChatMessageShort.from_orm(msg) for msg in history[-n:]]
    except Exception as e:
        logger.error(f"Failed to get last messages for project {project_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/ask", response_model=ChatMessageRead)
async def ask_jarvis(
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Отправляет запрос локальному Ollama и сохраняет ответ."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3", "prompt": data.content, "stream": False},
            )
            resp.raise_for_status()
            ai_content = resp.json().get("response", "")
    except Exception as e:
        logger.error(f"Ollama request failed: {e}")
        raise HTTPException(status_code=503, detail="Ollama service unavailable")

    user_msg = save_message(
        db=db,
        project_id=data.project_id,
        role=data.role,
        content=data.content,
        author=current_user.username,
        attachments=data.attachments,
        is_deleted=data.is_deleted,
    )

    ai_msg = save_message(
        db=db,
        project_id=data.project_id,
        role="jarvis",
        content=ai_content,
        author="jarvis",
    )
    return ai_msg

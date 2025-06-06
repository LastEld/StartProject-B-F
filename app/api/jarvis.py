#app/api/jarvis.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.jarvis import (
    ChatMessageCreate, ChatMessageRead, ChatMessageUpdate, ChatMessageShort,
    JarvisRequest, JarvisResponse  # Added JarvisRequest, JarvisResponse
)
from app.crud.jarvis import (
    save_message,
    get_history,
    delete_history_for_project,
    ask_ollama,  # Added ask_ollama
    ChatControllerError  # Added ChatControllerError
)
from app.dependencies import get_db, get_current_active_user
from app.schemas.response import SuccessResponse
from app.models.user import User as UserModel

import logging

router = APIRouter(prefix="/jarvis", tags=["Jarvis"])
logger = logging.getLogger("DevOS.JarvisAPI")


@router.post("/ask", response_model=JarvisResponse)
async def api_ask_jarvis(
    request_data: JarvisRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Handles a request to the Jarvis Ollama interaction endpoint.
    """
    logger.info(f"User '{current_user.username}' is asking Jarvis: '{request_data.prompt[:50]}...'")
    try:
        jarvis_response = await ask_ollama(
            db=db,
            request=request_data,
            current_user_username=current_user.username
        )
        return jarvis_response
    except ChatControllerError as e:
        logger.error(f"ChatControllerError in /ask endpoint for user '{current_user.username}': {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in /ask endpoint for user '{current_user.username}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


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

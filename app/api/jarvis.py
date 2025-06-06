from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from app.schemas.jarvis import (
    ChatMessageCreate, ChatMessageRead, ChatMessageUpdate, ChatMessageShort,
    JarvisAskRequest, JarvisAskResponse
)
from app.crud.jarvis import (
    save_message as crud_save_message,
    get_history as crud_get_history,
    delete_history_for_project as crud_delete_history_for_project,
    ChatControllerError
)
from app.dependencies import get_db, get_current_active_user
from app.schemas.response import SuccessResponse
from app.models.user import User as UserModel
from app.services.ollama_service import get_ollama_response, SimpleChatMessage
from app.models.project import Project as ProjectModel
from app.crud.project import get_project as crud_get_project
from app.core.exceptions import ProjectNotFound

import logging
import datetime

router = APIRouter(prefix="/api/jarvis", tags=["Jarvis"])
logger = logging.getLogger("DevOS.JarvisAPI")

async def get_project_from_db_for_jarvis(project_id: int, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_active_user)) -> ProjectModel:
    try:
        project = crud_get_project(db, project_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with id {project_id} not found.")

    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active.")
    # Add more specific project access logic here if needed.
    return project

@router.post("/ask", response_model=JarvisAskResponse)
async def ask_jarvis(
    data: JarvisAskRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    project = await get_project_from_db_for_jarvis(data.project_id, db, current_user)

    try:
        user_msg_db = crud_save_message(
            db=db, project_id=project.id, role="user", content=data.content,
            author=current_user.username, timestamp=datetime.datetime.now(datetime.timezone.utc),
            attachments=data.attachments or []
        )

        history_db = crud_get_history(db, project_id=project.id, limit=10)
        simple_history = [SimpleChatMessage(role=msg.role, content=msg.content) for msg in history_db]

        ai_response_content = await get_ollama_response(
            project_id=project.id, user_prompt=data.content, chat_history=simple_history
        )

        ai_msg_db = crud_save_message(
            db=db, project_id=project.id, role="assistant", content=ai_response_content,
            author="Jarvis", timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        return JarvisAskResponse(user_message=ChatMessageRead.from_orm(user_msg_db), jarvis_response=ChatMessageRead.from_orm(ai_msg_db))

    except ChatControllerError as e:
        logger.error(f"Jarvis ask controller error for project {project.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in ask_jarvis for project {project.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred with Jarvis.")

@router.post("/chat/", response_model=ChatMessageRead)
async def post_message_to_history(
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    project = await get_project_from_db_for_jarvis(data.project_id, db, current_user)
    try:
        msg = crud_save_message(
            db=db, project_id=project.id, role=data.role, content=data.content,
            timestamp=data.timestamp or datetime.datetime.now(datetime.timezone.utc),
            metadata=data.metadata, author=data.author or current_user.username,
            ai_notes=data.ai_notes, attachments=data.attachments or [],
            is_deleted=data.is_deleted or False
        )
        return msg
    except ChatControllerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save message.")

@router.get("/chat/", response_model=List[ChatMessageRead])
async def get_chat_history_for_project(
    project_id: int = Query(...),
    limit: Optional[int] = Query(None, ge=1, le=200),
    offset: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    await get_project_from_db_for_jarvis(project_id, db, current_user)
    try:
        history = crud_get_history(db, project_id, limit=limit, offset=offset)
        return history
    except ChatControllerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch chat history.")

@router.delete("/chat/history/{project_id_in_path}", response_model=SuccessResponse)
async def delete_project_chat_history(
    project_id_in_path: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    project = await get_project_from_db_for_jarvis(project_id_in_path, db, current_user)
    try:
        deleted_count = crud_delete_history_for_project(db, project.id, hard=False)
        return SuccessResponse(result=deleted_count, detail=f"Chat history for project {project.id} deleted ({deleted_count} messages).")
    except ChatControllerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete chat history.")

@router.get("/chat/history/{project_id_in_path}/last", response_model=List[ChatMessageShort])
async def get_last_chat_messages(
    project_id_in_path: int,
    n: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    project = await get_project_from_db_for_jarvis(project_id_in_path, db, current_user)
    try:
        history = crud_get_history(db, project.id, limit=n, offset=None)
        return [ChatMessageShort(id=msg.id, role=msg.role, content=msg.content, timestamp=msg.timestamp.isoformat() if msg.timestamp else None) for msg in history]
    except ChatControllerError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch last messages.")

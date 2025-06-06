#app/api/ai_context.py
from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.schemas.ai_context import (
    AIContextCreate,
    AIContextUpdate,
    AIContextRead,
)
from app.crud.ai_context import (
    create_ai_context,
    get_ai_context,
    get_ai_contexts,
    update_ai_context,
    delete_ai_context,
    get_latest_ai_context,
)
from app.dependencies import get_db, get_current_active_user
from app.schemas.response import SuccessResponse

router = APIRouter(prefix="/ai-context", tags=["AI Context"])

@router.post("/", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_ai_ctx(
    data: AIContextCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """
    Создать новый AI-контекст (проект, задача, devlog, пользователь и т.д.).
    """
    try:
        ai_ctx = create_ai_context(
            db=db,
            object_type=data.object_type,
            object_id=data.object_id,
            context_data=data.context_data,
            created_by=data.created_by or user.username,
            request_id=data.request_id,
            notes=data.notes,
        )
        return SuccessResponse(result=ai_ctx.id, detail="AIContext created")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{ai_context_id}", response_model=AIContextRead)
def get_one_ai_ctx(
    ai_context_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """
    Получить один AI-контекст по ID.
    """
    ai_ctx = get_ai_context(db, ai_context_id)
    if not ai_ctx:
        raise HTTPException(status_code=404, detail="AIContext not found")
    return ai_ctx

@router.get("/latest/", response_model=AIContextRead)
def get_latest_ctx(
    object_type: str = Query(..., description="Тип объекта (project, task, ...)", example="project"),
    object_id: int = Query(..., description="ID объекта"),
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """
    Получить последний AI-контекст для заданного object_type/object_id.
    """
    ai_ctx = get_latest_ai_context(db, object_type, object_id)
    if not ai_ctx:
        raise HTTPException(status_code=404, detail="AIContext not found")
    return ai_ctx

@router.get("/", response_model=List[AIContextRead])
def list_ai_contexts(
    object_type: Optional[str] = None,
    object_id: Optional[int] = None,
    created_by: Optional[str] = None,
    request_id: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """
    Получить список AI-контекстов по фильтрам.
    """
    filters = {}
    if object_type: filters["object_type"] = object_type
    if object_id: filters["object_id"] = object_id
    if created_by: filters["created_by"] = created_by
    if request_id: filters["request_id"] = request_id
    if created_after: filters["created_after"] = created_after
    if created_before: filters["created_before"] = created_before
    return get_ai_contexts(db, filters=filters, limit=limit, offset=offset)

@router.patch("/{ai_context_id}", response_model=SuccessResponse)
def patch_ai_context(
    ai_context_id: int,
    data: AIContextUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """
    Обновить существующий AI-контекст (partial update).
    """
    try:
        ai_ctx = update_ai_context(db, ai_context_id, data.dict(exclude_unset=True))
        return SuccessResponse(result=ai_ctx.id, detail="AIContext updated")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{ai_context_id}", response_model=SuccessResponse)
def delete_ai_ctx(
    ai_context_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """
    Удалить AI-контекст по ID.
    """
    try:
        delete_ai_context(db, ai_context_id)
        return SuccessResponse(result=ai_context_id, detail="AIContext deleted")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

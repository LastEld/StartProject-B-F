#app/crud/ai_context.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from app.models.ai_context import AIContext
from app.core.exceptions import ProjectValidationError
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

import logging
logger = logging.getLogger("DevOS.AIContext")

def create_ai_context(
    db: Session,
    object_type: str,
    object_id: int,
    context_data: Dict[str, Any],
    created_by: Optional[str] = None,
    request_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> AIContext:
    """
    Создать новый AIContext для объекта.
    """
    ai_ctx = AIContext(
        object_type=object_type,
        object_id=object_id,
        context_data=context_data,
        created_by=created_by,
        request_id=request_id,
        notes=notes
    )
    db.add(ai_ctx)
    try:
        db.commit()
        db.refresh(ai_ctx)
        logger.info(f"Created AIContext (object_type={object_type}, object_id={object_id})")
        return ai_ctx
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating AIContext: {e}")
        raise ProjectValidationError("AIContext for this object already exists.")
    except Exception as e:
        db.rollback()
        logger.error(f"DB error creating AIContext: {e}")
        raise ProjectValidationError("Database error while creating AIContext.")

def get_ai_context(db: Session, ai_context_id: int, include_deleted: bool = False) -> Optional[AIContext]:
    """
    Получить AIContext по ID (по умолчанию только не удалённые).
    """
    q = db.query(AIContext).filter(AIContext.id == ai_context_id)
    if not include_deleted:
        q = q.filter(AIContext.is_deleted == False)
    return q.first()

def get_latest_ai_context(
    db: Session,
    object_type: str,
    object_id: int,
    include_deleted: bool = False
) -> Optional[AIContext]:
    """
    Получить самый свежий AIContext для object_type/object_id.
    """
    q = db.query(AIContext).filter(
        AIContext.object_type == object_type,
        AIContext.object_id == object_id
    )
    if not include_deleted:
        q = q.filter(AIContext.is_deleted == False)
    return q.order_by(AIContext.created_at.desc()).first()

def get_ai_contexts(
    db: Session,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 50,
    offset: int = 0,
    include_deleted: bool = False
) -> List[AIContext]:
    """
    Получить список AIContext c фильтрацией и пагинацией.
    """
    filters = filters or {}
    query = db.query(AIContext)
    if not include_deleted:
        query = query.filter(AIContext.is_deleted == False)
    if "object_type" in filters:
        query = query.filter(AIContext.object_type == filters["object_type"])
    if "object_id" in filters:
        query = query.filter(AIContext.object_id == filters["object_id"])
    if "created_by" in filters:
        query = query.filter(AIContext.created_by == filters["created_by"])
    if "request_id" in filters:
        query = query.filter(AIContext.request_id == filters["request_id"])
    if "created_after" in filters:
        query = query.filter(AIContext.created_at >= filters["created_after"])
    if "created_before" in filters:
        query = query.filter(AIContext.created_at <= filters["created_before"])
    return query.order_by(AIContext.created_at.desc()).limit(limit).offset(offset).all()

def update_ai_context(
    db: Session,
    ai_context_id: int,
    data: Dict[str, Any],
    merge_context_data: bool = True
) -> AIContext:
    """
    Обновить AIContext по id. По умолчанию обновляет только переданные поля.
    merge_context_data — если True, context_data сливается, иначе полностью заменяется.
    """
    ai_ctx = get_ai_context(db, ai_context_id)
    if not ai_ctx:
        raise ProjectValidationError("AIContext not found.")

    # Top-level fields
    for field_name in ["object_type", "object_id", "created_by", "request_id", "notes", "is_deleted"]:
        if field_name in data:
            setattr(ai_ctx, field_name, data[field_name])

    # context_data logic
    if "context_data" in data and data["context_data"] is not None:
        if merge_context_data and ai_ctx.context_data:
            ai_ctx.context_data.update(data["context_data"])
        else:
            ai_ctx.context_data = data["context_data"]
        flag_modified(ai_ctx, "context_data")

    ai_ctx.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(ai_ctx)
        logger.info(f"Updated AIContext {ai_ctx.id}")
        return ai_ctx
    except Exception as e:
        db.rollback()
        logger.error(f"DB error updating AIContext: {e}")
        raise ProjectValidationError("Database error while updating AIContext.")

def delete_ai_context(db: Session, ai_context_id: int, soft: bool = True) -> bool:
    """
    Удалить AIContext (по умолчанию soft-delete: is_deleted=True, deleted_at=now()).
    """
    ai_ctx = get_ai_context(db, ai_context_id, include_deleted=True)
    if not ai_ctx:
        raise ProjectValidationError("AIContext not found.")

    if soft:
        ai_ctx.is_deleted = True
        ai_ctx.deleted_at = datetime.now(timezone.utc)
    else:
        db.delete(ai_ctx)
    try:
        db.commit()
        logger.info(f"{'Soft-deleted' if soft else 'Hard-deleted'} AIContext {ai_ctx.id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"DB error deleting AIContext: {e}")
        raise ProjectValidationError("Database error while deleting AIContext.")

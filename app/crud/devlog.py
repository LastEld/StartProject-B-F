#app/crud/devlog.py
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.devlog import DevLogEntry
from app.models.user import User as UserModel
from app.core.exceptions import DevLogNotFound, DevLogValidationError, ProjectNotFound, TaskNotFound
from app.core.custom_fields import CUSTOM_FIELDS_SCHEMA
from app.crud.project import get_project
from app.crud.task import get_task
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("DevOS.DevLog")

def validate_custom_fields_payload(custom_fields: dict):
    """
    Валидация кастомных полей через CUSTOM_FIELDS_SCHEMA.
    """
    for key, value in custom_fields.items():
        schema = CUSTOM_FIELDS_SCHEMA.get(key)
        if not schema:
            raise DevLogValidationError(f"Unknown custom field: {key}")
        if not schema["validator"](value):
            raise DevLogValidationError(f"Invalid value for '{key}': {value} (expected {schema['type']})")

def create_entry(db: Session, data: dict, author_id: int) -> DevLogEntry:
    """
    Создаёт новую запись DevLog с валидацией всех полей, ссылок и кастомных полей.
    """
    if not data.get("content") or not data.get("content").strip():
        raise DevLogValidationError("DevLog entry content cannot be empty.")

    project_id = data.get("project_id")
    if project_id is not None:
        get_project(db, project_id)  # Может кинуть ProjectNotFound

    task_id = data.get("task_id")
    if task_id is not None:
        get_task(db, task_id)  # Может кинуть TaskNotFound

    custom_fields = data.get("custom_fields", {})
    if custom_fields:
        validate_custom_fields_payload(custom_fields)

    entry = DevLogEntry(
        project_id=project_id,
        task_id=task_id,
        entry_type=data.get("entry_type", "note"),
        content=data["content"].strip(),
        author_id=author_id,
        tags=data.get("tags") or [],
        custom_fields=custom_fields,
        is_deleted=False,
        edit_reason=data.get("edit_reason"),
        attachments=data.get("attachments", []),
        ai_notes=data.get("ai_notes"),
    )
    try:
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info(f"Created DevLog entry {entry.id} (project_id={entry.project_id}, author_id={entry.author_id})")
        return entry
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to create DevLog entry: {e}")
        raise DevLogValidationError(f"DB error: {e}")

def get_entry(db: Session, entry_id: int) -> DevLogEntry:
    """
    Получить запись DevLog по id (поднимает исключение, если не найдено).
    """
    entry = db.query(DevLogEntry).filter(DevLogEntry.id == entry_id).first()
    if not entry:
        raise DevLogNotFound(f"DevLogEntry {entry_id} not found")
    return entry

def update_entry(db: Session, entry_id: int, data: dict) -> DevLogEntry:
    """
    Обновить DevLogEntry по id, без возможности менять автора.
    """
    entry = get_entry(db, entry_id)
    if entry.is_deleted:
        raise DevLogValidationError("Cannot update an archived DevLog entry. Please restore it first.")

    updated = False
    list_fields = {"tags", "attachments"}
    for field in ["content", "entry_type", "tags", "edit_reason", "attachments", "ai_notes"]:
        if field in data:
            new_value = data[field] if data[field] is not None else ([] if field in list_fields else None)
            if getattr(entry, field) != new_value:
                setattr(entry, field, new_value)
                updated = True

    # Update project_id/task_id if provided
    if "project_id" in data:
        new_project_id = data["project_id"]
        if new_project_id is not None:
            get_project(db, new_project_id)
        if entry.project_id != new_project_id:
            entry.project_id = new_project_id
            updated = True

    if "task_id" in data:
        new_task_id = data["task_id"]
        if new_task_id is not None:
            get_task(db, new_task_id)
        if entry.task_id != new_task_id:
            entry.task_id = new_task_id
            updated = True

    # Update custom_fields
    if "custom_fields" in data:
        cf = data["custom_fields"]
        if isinstance(cf, dict):
            validate_custom_fields_payload(cf)
            if entry.custom_fields is None or entry.custom_fields != cf:
                entry.custom_fields = {**(entry.custom_fields or {}), **cf}
                updated = True
        elif cf is None and entry.custom_fields not in (None, {}):
            entry.custom_fields = {}
            updated = True

    if updated:
        entry.updated_at = datetime.now(timezone.utc)
        try:
            db.commit()
            db.refresh(entry)
            logger.info(f"Updated DevLog entry {entry.id}")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to update DevLog entry: {e}")
            raise DevLogValidationError(f"DB error: {e}")
    return entry

def soft_delete_entry(db: Session, entry_id: int) -> bool:
    """
    Помечает DevLogEntry как удалённую (soft-delete).
    """
    entry = db.query(DevLogEntry).filter(DevLogEntry.id == entry_id).first()
    if not entry:
        raise DevLogNotFound(f"DevLogEntry {entry_id} not found for deletion.")
    if entry.is_deleted:
        raise DevLogValidationError("DevLog entry already archived.")
    entry.is_deleted = True
    entry.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        logger.info(f"Archived DevLog entry {entry_id}")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to archive DevLog entry: {e}")
        raise DevLogValidationError(f"DB error: {e}")

def restore_entry(db: Session, entry_id: int) -> bool:
    """
    Восстанавливает DevLogEntry из архива.
    """
    entry = db.query(DevLogEntry).filter(DevLogEntry.id == entry_id).first()
    if not entry:
        raise DevLogNotFound(f"DevLogEntry {entry_id} not found for restore.")
    if not entry.is_deleted:
        raise DevLogValidationError("DevLog entry is not archived.")
    entry.is_deleted = False
    entry.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        logger.info(f"Restored DevLog entry {entry_id}")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to restore DevLog entry: {e}")
        raise DevLogValidationError(f"DB error: {e}")

def get_entries(
    db: Session,
    current_user: UserModel,
    filters: Optional[Dict[str, Any]] = None,
    page: int = 1,
    per_page: int = 20
) -> dict:
    """
    Получить список DevLogEntry с фильтрами, видимостью и пагинацией.
    Только свои записи для обычных пользователей, все для суперюзеров.
    """
    query = db.query(DevLogEntry)
    filters = filters or {}

    if not current_user.is_superuser:
        query = query.filter(DevLogEntry.author_id == current_user.id)

    show_archived = filters.get("show_archived", False)
    if not show_archived:
        query = query.filter(DevLogEntry.is_deleted == False)

    if "project_id" in filters:
        query = query.filter(DevLogEntry.project_id == filters["project_id"])
    if "task_id" in filters:
        query = query.filter(DevLogEntry.task_id == filters["task_id"])
    if "entry_type" in filters and filters["entry_type"] != "all":
        query = query.filter(DevLogEntry.entry_type == filters["entry_type"])
    if "author_id" in filters and filters["author_id"]:
        query = query.filter(DevLogEntry.author_id == filters["author_id"])
    if "tag" in filters and filters["tag"]:
        from sqlalchemy import cast, String as SQLString
        tag_to_find = filters["tag"]
        query = query.filter(cast(DevLogEntry.tags, SQLString).like(f'%"{tag_to_find}"%'))
    if "date_from" in filters and filters["date_from"]:
        try:
            date_from_obj = datetime.strptime(str(filters["date_from"]), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(DevLogEntry.created_at >= date_from_obj)
        except ValueError:
            logger.warning(f"Invalid date_from format: {filters['date_from']}. Expected YYYY-MM-DD.")
    if "date_to" in filters and filters["date_to"]:
        try:
            date_to_obj = datetime.strptime(str(filters["date_to"]), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_of_day_to = date_to_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(DevLogEntry.created_at <= end_of_day_to)
        except ValueError:
            logger.warning(f"Invalid date_to format: {filters['date_to']}. Expected YYYY-MM-DD.")
    if "search" in filters and filters["search"]:
        search_term = f"%{filters['search']}%"
        query = query.filter(DevLogEntry.content.ilike(search_term))
    if "custom_fields" in filters and filters["custom_fields"]:
        for key, value in filters["custom_fields"].items():
            if key and value:
                query = query.filter(DevLogEntry.custom_fields[key].astext.ilike(f"%{str(value)}%"))

    total_count = query.count()
    query = query.order_by(DevLogEntry.created_at.desc())
    if page < 1: page = 1
    if per_page < 1: per_page = 1
    offset = (page - 1) * per_page
    entries = query.limit(per_page).offset(offset).all()
    return {"entries": entries, "total_count": total_count}

def summarize_entry(db: Session, entry_id: int) -> str:
    """
    Возвращает краткое описание записи DevLog (для списка, уведомлений).
    """
    entry = get_entry(db, entry_id)
    author_identifier = f"AuthorID:{entry.author_id}"
    if hasattr(entry, "author") and entry.author:
        author_identifier = entry.author.username
    return (
        f"[{entry.created_at.strftime('%Y-%m-%d %H:%M')}] "
        f"{author_identifier}: {entry.entry_type.upper()} - {entry.content[:180]}"
        + (f" (tags: {', '.join(entry.tags or [])})" if entry.tags else "")
    )

def get_ai_context(db: Session, entry_id: int) -> dict:
    """
    Формирует контекст DevLogEntry для передачи в AI/внешние системы.
    """
    entry = get_entry(db, entry_id)
    author_identifier = f"AuthorID:{entry.author_id}"
    if hasattr(entry, "author") and entry.author:
        author_identifier = entry.author.username

    return {
        "id": entry.id,
        "project_id": entry.project_id,
        "task_id": entry.task_id,
        "entry_type": entry.entry_type,
        "content": entry.content,
        "author_identifier": author_identifier,
        "author_id": entry.author_id,
        "tags": entry.tags or [],
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
        "custom_fields": entry.custom_fields or {},
        "is_deleted": entry.is_deleted,
        "edit_reason": entry.edit_reason,
        "attachments": entry.attachments or [],
        "ai_notes": entry.ai_notes,
    }

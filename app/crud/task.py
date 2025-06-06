#app/crud/tasks.py
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import cast, String as SQLString, func, or_
from app.models.task import Task
from app.core.exceptions import (
    TaskNotFound,
    TaskValidationError,
)
from app.core.custom_fields import CUSTOM_FIELDS_SCHEMA
import logging
from typing import List, Dict, Any

logger = logging.getLogger("DevOS.Tasks")

def validate_custom_fields_payload(custom_fields: dict):
    """
    Проверяет кастомные поля на соответствие глобальной схеме.
    """
    for key, value in custom_fields.items():
        schema = CUSTOM_FIELDS_SCHEMA.get(key)
        if not schema:
            raise TaskValidationError(f"Unknown custom field: {key}")
        if not schema["validator"](value):
            raise TaskValidationError(f"Invalid value for '{key}': {value} (expected {schema['type']})")

def create_task(db: Session, data: dict) -> Task:
    """
    Создать новую задачу.
    """
    title = data.get("title", "").strip()
    if not title:
        raise TaskValidationError("Title is required.")

    project_id = data.get("project_id")
    if project_id is None:
        raise TaskValidationError("Project ID is required.")
    try:
        project_id = int(project_id)
    except ValueError:
        raise TaskValidationError("Project ID must be an integer.")

    if db.query(Task).filter_by(project_id=project_id, title=title).first():
        raise TaskValidationError("Task title must be unique within a project.")

    deadline = data.get("deadline")
    if deadline and not isinstance(deadline, date):
        try:
            deadline = date.fromisoformat(str(deadline))
        except ValueError:
            raise TaskValidationError("Invalid deadline date format. Use YYYY-MM-DD.")
    if deadline and deadline < date.today():
        raise TaskValidationError("Deadline cannot be in the past.")

    priority = int(data.get("priority", 3))
    if not 1 <= priority <= 5:
        raise TaskValidationError("Priority must be an integer between 1 and 5.")

    custom_fields = data.get("custom_fields", {})
    if not isinstance(custom_fields, dict):
        raise TaskValidationError("Custom fields must be a dictionary (JSON object).")
    if custom_fields:
        validate_custom_fields_payload(custom_fields)

    tags_data = data.get("tags") or []
    if not isinstance(tags_data, list) or not all(isinstance(tag, str) for tag in tags_data):
        raise TaskValidationError("Tags must be a list of strings.")

    assignees = data.get("assignees", [])
    if not isinstance(assignees, list):
        raise TaskValidationError("Assignees must be a list.")

    attachments = data.get("attachments", [])
    is_favorite = data.get("is_favorite", False)
    ai_notes = data.get("ai_notes")
    external_id = data.get("external_id")
    reviewed = data.get("reviewed", False)

    task = Task(
        title=title,
        description=data.get("description", "").strip(),
        task_status=data.get("task_status","todo"),
        priority=priority,
        deadline=deadline,
        assignees=assignees,
        tags=tags_data,
        project_id=project_id,
        parent_task_id=data.get("parent_task_id"),
        custom_fields=custom_fields,
        is_deleted=False,
        attachments=attachments,
        is_favorite=is_favorite,
        ai_notes=ai_notes,
        external_id=external_id,
        reviewed=reviewed
    )
    db.add(task)
    try:
        db.commit()
        logger.info(f"Created task {task.id} for project {task.project_id}")
        return task
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to create task: {e}")
        raise TaskValidationError("Database error while creating task.")

def get_task(db: Session, task_id: int, include_deleted: bool = False) -> Task:
    """
    Получить задачу по ID (учитывать или нет soft-delete).
    """
    query = db.query(Task).filter(Task.id == task_id)
    if not include_deleted:
        query = query.filter(Task.is_deleted == False)
    task = query.first()
    if not task:
        raise TaskNotFound(f"Task {task_id} not found{' (or is deleted)' if not include_deleted else ''}.")
    return task

def get_all_tasks(db: Session, filters: dict = None, sort_by: str = "deadline") -> List[Task]:
    """
    Возвращает список задач с фильтрами, soft-delete, сортировкой.
    """
    query = db.query(Task)
    filters = filters or {}

    if not filters.get("show_archived", False):
        query = query.filter(Task.is_deleted == False)

    if "project_id" in filters:
        query = query.filter(Task.project_id == filters["project_id"])
    print("TASKS FILTERS:", filters)
    if "task_status" in filters and filters["task_status"] != "all":
        query = query.filter(Task.task_status == filters["task_status"])
    if "search" in filters:
        val = f"%{filters['search']}%"
        query = query.filter(Task.title.ilike(val) | Task.description.ilike(val))
    if "deadline_before" in filters:
        query = query.filter(Task.deadline <= filters["deadline_before"])
    if "deadline_after" in filters:
        query = query.filter(Task.deadline >= filters["deadline_after"])
    if "parent_task_id" in filters:
        query = query.filter(Task.parent_task_id == filters["parent_task_id"])
    if "priority" in filters:
        query = query.filter(Task.priority == filters["priority"])
    if "tag" in filters:
        tag = filters["tag"]
        query = query.filter(cast(Task.tags, SQLString).like(f'%"{tag}"%'))
    if "custom_fields" in filters:
        for key, value in filters["custom_fields"].items():
            query = query.filter(cast(func.json_extract(Task.custom_fields, f'$.{key}'), SQLString) == str(value))
    if "assignee_id" in filters:
        assignee_id_val = int(filters["assignee_id"])
        pattern1 = f'%{{"user_id":{assignee_id_val},%'
        pattern2 = f'%{{"user_id": {assignee_id_val},%'
        pattern3 = f'%{{"user_id":{assignee_id_val}}}%'
        pattern4 = f'%{{"user_id": {assignee_id_val}}}%'
        query = query.filter(
            or_(
                cast(Task.assignees, SQLString).like(pattern1),
                cast(Task.assignees, SQLString).like(pattern2),
                cast(Task.assignees, SQLString).like(pattern3),
                cast(Task.assignees, SQLString).like(pattern4)
            )
        )
    if "is_favorite" in filters:
        query = query.filter(Task.is_favorite == filters["is_favorite"])
    if "external_id" in filters:
        query = query.filter(Task.external_id == filters["external_id"])
    if "reviewed" in filters:
        query = query.filter(Task.reviewed == filters["reviewed"])

    if hasattr(Task, sort_by):
        if sort_by == "priority":
            query = query.order_by(getattr(Task, sort_by).asc())
        else:
            query = query.order_by(getattr(Task, sort_by).desc())
    else:
        query = query.order_by(Task.deadline.asc())

    return query.all()

def update_task(db: Session, task_id: int, data: dict) -> Task:
    """
    Обновить задачу по ID с полной валидацией.
    """
    task = get_task(db, task_id)
    pre_update = {k: v for k, v in task.__dict__.items() if not k.startswith('_sa_')}

    for field in [
        "title", "description", "task_status", "priority", "deadline",
        "assignees", "tags", "parent_task_id", "attachments", "is_favorite",
        "ai_notes", "external_id", "reviewed"
    ]:
        if field in data:
            setattr(task, field, data[field] if field != "title" else data[field].strip())

    if "custom_fields" in data:
        cf = data["custom_fields"]
        if not isinstance(cf, dict):
            raise TaskValidationError("Custom fields must be a dictionary (JSON object).")
        if cf:
            validate_custom_fields_payload(cf)
        new_custom_fields = task.custom_fields.copy() if task.custom_fields is not None else {}
        new_custom_fields.update(cf)
        task.custom_fields = new_custom_fields

    if not task.title:
        raise TaskValidationError("Task title is required.")
    if task.deadline and task.deadline < date.today() and task.task_status != "done":
        raise TaskValidationError("Deadline cannot be set to a past date.")

    task.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        post_update = {k: v for k, v in task.__dict__.items() if not k.startswith('_sa_')}
        changes = {
            k: (pre_update[k], post_update[k])
            for k in post_update
            if pre_update.get(k) != post_update[k]
        }
        if changes:
            logger.info(f"Updated task {task.id} fields: {changes}")
        else:
            logger.info(f"Update called but no changes for task {task.id}")
        return task
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update task: {e}")
        raise TaskValidationError("Database error while updating task.")

def soft_delete_task(db: Session, task_id: int) -> Task:
    """
    Помечает задачу как удалённую (soft-delete).
    """
    task = get_task(db, task_id, include_deleted=True)
    if task.is_deleted:
        raise TaskValidationError("Task already archived.")
    task.is_deleted = True
    task.deleted_at = datetime.now(timezone.utc)
    task.task_status = "archived"
    try:
        db.commit()
        db.refresh(task)
        logger.info(f"Archived task {task_id}")
        return task
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to archive task: {e}")
        raise TaskValidationError("Database error while archiving task.")

def restore_task(db: Session, task_id: int) -> Task:
    """
    Восстанавливает soft-deleted задачу.
    """
    task = get_task(db, task_id, include_deleted=True)
    if not task.is_deleted:
        raise TaskValidationError(f"Task with id={task_id} is not archived/deleted.")
    task.is_deleted = False
    task.deleted_at = None
    task.task_status = "todo"
    try:
        db.commit()
        db.refresh(task)
        logger.info(f"Restored task {task_id}")
        return task
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to restore task: {e}")
        raise TaskValidationError("Database error while restoring task.")

def get_ai_context(db: Session, task_id: int) -> Dict[str, Any]:
    """
    Возвращает AI-контекст задачи (для AI-ассистента, аналитики).
    """
    task = get_task(db, task_id)
    is_overdue = bool(task.deadline and task.deadline < date.today() and task.task_status != "done")
    ctx = {
        "id": task.id,
        "project_id": task.project_id,
        "parent_task_id": task.parent_task_id,
        "title": task.title,
        "description": task.description,
        "task_status": task.task_status,
        "priority": task.priority,
        "deadline": str(task.deadline) if task.deadline else None,
        "assignees": task.assignees,
        "tags": task.tags or [],
        "custom_fields": task.custom_fields or {},
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "is_overdue": is_overdue,
        "is_deleted": task.is_deleted,
        "attachments": task.attachments or [],
        "is_favorite": task.is_favorite,
        "ai_notes": task.ai_notes,
        "external_id": task.external_id,
        "reviewed": task.reviewed,
    }
    logger.info(f"Generated AI context for task: {task.id}")
    return ctx

def summarize_task(db: Session, task_id: int, style: str = "default") -> str:
    """
    Возвращает краткое описание задачи (для уведомлений, AI и т.д.).
    """
    ctx = get_ai_context(db, task_id)
    overdue_str = "⚠️ OVERDUE!\n" if ctx.get("is_overdue") else ""
    parent_str = f"Parent Task ID: {ctx.get('parent_task_id')}\n" if ctx.get('parent_task_id') else ""
    summary = (
        f"{overdue_str}"
        f"Task '{ctx['title']}' — {ctx['description']}\n"
        f"Task_tatus: {ctx['task_status']}, Priority: {ctx['priority']}, Deadline: {ctx['deadline']}\n"
        f"Assignees: {', '.join([a['name'] for a in ctx.get('assignees', []) if 'name' in a])}\n"
        f"Tags: {', '.join(ctx.get('tags', []))}\n"
        f"{parent_str}"
        f"AI Notes: {ctx.get('ai_notes') or '-'}\n"
        f"Attachments: {len(ctx.get('attachments', []))}\n"
        f"Created at: {ctx['created_at']}\n"
    )
    return summary

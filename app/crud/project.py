# app/crud/project.py
from sqlalchemy.orm import Session
from sqlalchemy import cast, String as SQLString
from datetime import date, datetime, timezone
from app.models.project import Project
from app.core.exceptions import (
    ProjectNotFound,
    DuplicateProjectName,
    ProjectValidationError,
)
from app.core.custom_fields import CUSTOM_FIELDS_SCHEMA
import logging
from typing import Optional, List, Dict, Any
from app.models.user import User as UserModel

logger = logging.getLogger("DevOS.Projects")

def validate_custom_fields_payload(custom_fields: dict):
    """
    Проверяет валидность кастомных полей через схему CUSTOM_FIELDS_SCHEMA.
    """
    for key, value in custom_fields.items():
        schema = CUSTOM_FIELDS_SCHEMA.get(key)
        if not schema:
            raise ProjectValidationError(f"Unknown custom field: {key}")
        if not schema["validator"](value):
            raise ProjectValidationError(f"Invalid value for '{key}': {value} (expected {schema['type']})")

def create_project(db: Session, data: dict) -> Project:
    """
    Создаёт новый проект с валидацией имени, дедлайна и кастомных полей.
    """
    name = data.get("name", "").strip()
    if not name:
        raise ProjectValidationError("Project name is required.")

    if db.query(Project).filter_by(name=name).first():
        raise DuplicateProjectName(f"Project with name '{name}' already exists.")

    if data.get("deadline") and data["deadline"] < date.today():
        raise ProjectValidationError("Deadline cannot be in the past.")

    custom_fields = data.get("custom_fields", {})
    if custom_fields:
        validate_custom_fields_payload(custom_fields)

    project = Project(
        name=name,
        description=data.get("description", ""),
        project_status=data.get("project_status", "active"),
        deadline=data.get("deadline"),
        author_id=data.get("author_id"),
        team_id=data.get("team_id"),
        priority=data.get("priority", 3),
        tags=data.get("tags", []),
        linked_repo=data.get("linked_repo"),
        color=data.get("color"),
        participants=data.get("participants", []),
        custom_fields=custom_fields,
        is_deleted=False,
        attachments=data.get("attachments", []),
        is_favorite=data.get("is_favorite", False),
        ai_notes=data.get("ai_notes"),
        external_id=data.get("external_id"),
        subscription_level=data.get("subscription_level"),
        parent_project_id=data.get("parent_project_id"),
    )
    db.add(project)
    try:
        db.commit()
        db.refresh(project)
        logger.info(f"Created project '{project.name}' (ID: {project.id})")
        return project
    except Exception as e:
        db.rollback()
        logger.error(f"Exception during save: {e}")
        raise ProjectValidationError("Database error while creating project.")

def get_all_projects(
    db: Session,
    current_user: UserModel,
    filters: Optional[Dict[str, Any]] = None,
    sort_by: str = "created_at"
) -> List[Project]:
    """
    Возвращает список проектов пользователя (или все, если суперюзер) с фильтрами.
    """
    query = db.query(Project)
    filters = filters or {}

    if not current_user.is_superuser:
        query = query.filter(Project.author_id == current_user.id)

    if not filters.get("show_archived", False):
        query = query.filter(Project.is_deleted == False)

    if "project_status" in filters:
        query = query.filter(Project.project_status == filters["project_status"])
    if "search" in filters:
        search = f"%{filters['search']}%"
        query = query.filter(
            (Project.name.ilike(search)) | (Project.description.ilike(search))
        )
    if "tag" in filters:
        tag_value = filters["tag"]
        query = query.filter(cast(Project.tags, SQLString).like(f'%"{tag_value}"%'))
    if "deadline" in filters:
        query = query.filter(Project.deadline == filters["deadline"])
    if "deadline_from" in filters:
        query = query.filter(Project.deadline >= filters["deadline_from"])
    if "deadline_to" in filters:
        query = query.filter(Project.deadline <= filters["deadline_to"])
    if "priority" in filters:
        query = query.filter(Project.priority == filters["priority"])
    if "custom_fields" in filters:
        for key, value in filters["custom_fields"].items():
            query = query.filter(Project.custom_fields[key].astext == str(value))
    if "is_favorite" in filters:
        query = query.filter(Project.is_favorite == filters["is_favorite"])
    if "subscription_level" in filters:
        query = query.filter(Project.subscription_level == filters["subscription_level"])
    if "external_id" in filters:
        query = query.filter(Project.external_id == filters["external_id"])

    # Сортировка
    if hasattr(Project, sort_by):
        if sort_by == "priority":
            query = query.order_by(getattr(Project, sort_by).asc())
        else:
            query = query.order_by(getattr(Project, sort_by).desc())
    else:
        query = query.order_by(Project.created_at.desc())

    return query.all()

def get_project(db: Session, project_id: int, include_deleted: bool = False) -> Project:
    """
    Возвращает проект по ID, по умолчанию не удалённый (soft-delete).
    """
    query = db.query(Project).filter(Project.id == project_id)
    if not include_deleted:
        query = query.filter(Project.is_deleted == False)
    project = query.first()
    if not project:
        raise ProjectNotFound(f"Project with id={project_id} not found{' (or is deleted)' if not include_deleted else ''}.")
    return project

def update_project(db: Session, project_id: int, data: dict) -> Project:
    """
    Обновляет проект по ID, с полной валидацией.
    """
    project = get_project(db, project_id)
    pre_update_snapshot = {
        k: v for k, v in project.__dict__.items()
        if not k.startswith('_sa_')
    }
    updatable_fields = [
        "name", "description", "project_status", "deadline", "priority",
        "tags", "linked_repo", "color", "participants", "parent_project_id",
        "attachments", "is_favorite", "ai_notes", "external_id", "subscription_level"
    ]
    for field in updatable_fields:
        if field in data:
            setattr(project, field, data[field])

    if "custom_fields" in data:
        cf_data_to_update = data["custom_fields"]
        validate_custom_fields_payload(cf_data_to_update)
        new_custom_fields = project.custom_fields.copy() if project.custom_fields is not None else {}
        new_custom_fields.update(cf_data_to_update)
        project.custom_fields = new_custom_fields

    if not project.name:
        raise ProjectValidationError("Project name is required.")
    if project.deadline and project.deadline < date.today():
        raise ProjectValidationError("Deadline cannot be in the past.")

    project.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        post_update_snapshot = {
            k: v for k, v in project.__dict__.items()
            if not k.startswith('_sa_')
        }
        changes = {
            k: (pre_update_snapshot[k], post_update_snapshot[k])
            for k in post_update_snapshot
            if pre_update_snapshot.get(k) != post_update_snapshot[k]
        }
        if changes:
            logger.info(f"Updated project {project.id} fields: {changes}")
        else:
            logger.info(f"Update called but no changes for project {project.id}")
        return project
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update project: {e}")
        raise ProjectValidationError("Database error while updating project.")

def soft_delete_project(db: Session, project_id: int) -> Project:
    """
    Помечает проект как удалённый (soft-delete).
    """
    project = get_project(db, project_id, include_deleted=True)
    if project.is_deleted:
        raise ProjectValidationError("Project already archived.")
    project.is_deleted = True
    project.deleted_at = datetime.now(timezone.utc)
    project.project_status = "archived"
    try:
        db.commit()
        db.refresh(project)
        logger.info(f"Soft-deleted project {project.id}")
        return project
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to archive project: {e}")
        raise ProjectValidationError("Database error while archiving project.")

def restore_project(db: Session, project_id: int) -> Project:
    """
    Восстанавливает soft-deleted проект.
    """
    project = get_project(db, project_id, include_deleted=True)
    if not project.is_deleted:
        raise ProjectValidationError(f"Project with id={project_id} is not archived/deleted.")
    project.is_deleted = False
    project.deleted_at = None
    project.project_status = "active"
    try:
        db.commit()
        db.refresh(project)
        logger.info(f"Restored project {project.id}")
        return project
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to restore project: {e}")
        raise ProjectValidationError("Database error while restoring project.")

def get_ai_context(db: Session, project_id: int) -> Dict[str, Any]:
    """
    Возвращает AI-контекст для проекта (для интеграции с AI/аналитикой).
    """
    project = get_project(db, project_id)
    is_overdue = bool(project.deadline and project.deadline < date.today())
    ctx = {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "project_status": project.project_status,
        "deadline": str(project.deadline) if project.deadline else None,
        "priority": project.priority,
        "participants": project.participants or [],
        "tags": project.tags or [],
        "linked_repo": project.linked_repo,
        "parent_project_id": project.parent_project_id,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "custom_fields": project.custom_fields or {},
        "is_overdue": is_overdue,
        "is_deleted": project.is_deleted,
        "attachments": project.attachments or [],
        "is_favorite": project.is_favorite,
        "ai_notes": project.ai_notes,
        "external_id": project.external_id,
        "subscription_level": project.subscription_level,
    }
    logger.info(f"Generated AI context for project: {project.id}")
    return ctx

def summarize_project(db: Session, project_id: int, style: str = "default") -> str:
    """
    Возвращает текстовое краткое описание проекта (для уведомлений, AI и т.д.).
    """
    ctx = get_ai_context(db, project_id)
    parent_str = f"Parent project ID: {ctx.get('parent_project_id')}\n" if ctx.get('parent_project_id') else ""
    overdue_str = "⚠️ OVERDUE!\n" if ctx.get("is_overdue") else ""
    summary = (
        f"{overdue_str}"
        f"Project '{ctx.get('name')}' — {ctx.get('description')}\n"
        f"Status: {ctx.get('project_status')}, Priority: {ctx.get('priority')}, Deadline: {ctx.get('deadline')}\n"
        f"Tags: {', '.join(ctx.get('tags', []))}\n"
        f"Participants: {', '.join([p['name'] for p in ctx.get('participants', []) if 'name' in p])}\n"
        f"{parent_str}"
        f"Linked repo: {ctx.get('linked_repo')}\n"
        f"Created at: {ctx.get('created_at')}\n"
        f"AI Notes: {ctx.get('ai_notes') or '-'}\n"
        f"Subscription Level: {ctx.get('subscription_level') or 'Free'}\n"
        f"Attachments: {len(ctx.get('attachments', []))}\n"
    )
    return summary or ""

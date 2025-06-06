#app/crud/template.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.template import Template
from app.models.project import Project
from app.models.user import User as UserModel
from app.core.exceptions import (
    SpecificTemplateNotFoundError,
    DuplicateProjectName,
    ProjectValidationError,
    TemplateValidationError, # Добавь в core/exceptions если нет
)
from typing import List, Optional, Dict
from datetime import datetime, timezone
from sqlalchemy import or_, cast, String as SQLString
import logging

logger = logging.getLogger("DevOS.Templates")

def create_template(db: Session, data: dict, author_id: int) -> Template:
    """
    Создать новый шаблон проекта (Template) с уникальным именем.
    """
    name = data.get("name", "").strip()
    if not name:
        raise ProjectValidationError("Template name is required.")
    if db.query(Template).filter(Template.name == name).first():
        raise DuplicateProjectName(f"Template with name '{name}' already exists.")
    structure = data.get("structure")
    if not structure:
        raise ProjectValidationError("Template structure is required.")

    template = Template(
        name=name,
        description=data.get("description"),
        version=data.get("version", "1.0.0"),
        author_id=author_id,
        is_active=data.get("is_active", True),
        tags=data.get("tags", []),
        structure=structure,
        ai_notes=data.get("ai_notes"),
        subscription_level=data.get("subscription_level"),
        is_private=data.get("is_private", False),
        
    )
    db.add(template)
    try:
        db.commit()
        db.refresh(template)
        logger.info(f"Created template '{template.name}' (ID: {template.id}) by author {author_id}")
        return template
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating template '{name}': {e}")
        raise DuplicateProjectName(f"Template with name '{name}' already exists.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating template '{name}': {e}")
        raise ProjectValidationError("Database error while creating template.")

def get_template(db: Session, template_id: int, include_deleted: bool = False) -> Template:
    """
    Получить шаблон по ID (опционально включая удалённые).
    """
    query = db.query(Template).filter(Template.id == template_id)
    if not include_deleted:
        query = query.filter(Template.is_deleted == False)
    template = query.first()
    if not template:
        raise SpecificTemplateNotFoundError(detail=f"Template with id={template_id} not found{' (or is deleted)' if not include_deleted else ''}.")
    return template

def get_all_templates(db: Session, current_user: UserModel, filters: Optional[Dict] = None) -> List[Template]:
    """
    Получить список шаблонов с учётом видимости (приватность, статус, фильтры).
    """
    filters = filters or {}
    query = db.query(Template)

    # Visibility
    if not current_user.is_superuser:
        query = query.filter(
            or_(
                Template.is_private == False,
                Template.author_id == current_user.id
            )
        ).filter(Template.is_deleted == False)
        if "is_active" in filters:
            query = query.filter(Template.is_active == filters["is_active"])
        else:
            query = query.filter(Template.is_active == True)
    else:
        if filters.get("show_archived", False):
            if "is_active" in filters:
                query = query.filter(Template.is_active == filters["is_active"])
        else:
            query = query.filter(Template.is_deleted == False)
            if "is_active" in filters:
                query = query.filter(Template.is_active == filters["is_active"])
            else:
                query = query.filter(Template.is_active == True)

    if "name" in filters and filters["name"]:
        query = query.filter(Template.name.ilike(f"%{filters['name']}%"))
    if "tag" in filters and filters["tag"]:
        query = query.filter(cast(Template.tags, SQLString).like(f'%"{filters["tag"]}"%'))
    if "subscription_level" in filters and filters["subscription_level"]:
        query = query.filter(Template.subscription_level == filters["subscription_level"])
    if "author_id" in filters and filters["author_id"]:
        query = query.filter(Template.author_id == filters["author_id"])

    return query.order_by(Template.created_at.desc()).all()

def update_template(db: Session, template_id: int, data: dict) -> Template:
    """
    Обновить шаблон проекта (без смены автора).
    """
    template = get_template(db, template_id)
    updatable_fields = [
        "name", "description", "version", "is_active", "tags", "structure",
        "ai_notes", "subscription_level", "is_private"
    ]
    for field in updatable_fields:
        if field in data:
            val = data[field]
            if field == "tags" and val is None:
                val = []
            setattr(template, field, val)

    if not template.name:
        raise ProjectValidationError("Template name cannot be empty.")
    if not template.structure:
        raise ProjectValidationError("Template structure cannot be empty.")

    template.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(template)
        logger.info(f"Updated template '{template.name}' (ID: {template.id})")
        return template
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating template {template.id}: {e}")
        raise ProjectValidationError("Database error while updating template.")

def soft_delete_template(db: Session, template_id: int) -> Template:
    """
    Soft-delete шаблон (делает неактивным и скрывает).
    """
    template = get_template(db, template_id, include_deleted=True)
    if template.is_deleted:
        logger.info(f"Template '{template.name}' (ID: {template.id}) is already soft-deleted.")
        return template

    template.is_deleted = True
    template.deleted_at = datetime.now(timezone.utc)
    template.is_active = False
    try:
        db.commit()
        db.refresh(template)
        logger.info(f"Soft-deleted template '{template.name}' (ID: {template.id})")
        return template
    except Exception as e:
        db.rollback()
        logger.error(f"Error soft-deleting template {template.id}: {e}")
        raise TemplateValidationError(f"Error during soft delete: {str(e)}")

def restore_template(db: Session, template_id: int) -> Template:
    """
    Восстановить soft-deleted шаблон.
    """
    template = get_template(db, template_id, include_deleted=True)
    if not template.is_deleted:
        raise ProjectValidationError(f"Template '{template.name}' (ID: {template.id}) is not deleted. No action taken.")
    template.is_deleted = False
    template.deleted_at = None
    try:
        db.commit()
        db.refresh(template)
        logger.info(f"Restored template '{template.name}' (ID: {template.id})")
        return template
    except Exception as e:
        db.rollback()
        logger.error(f"Error restoring template {template.id}: {e}")
        raise TemplateValidationError(f"Error during restore: {str(e)}")

def hard_delete_template(db: Session, template_id: int) -> bool:
    """
    Удалить шаблон из базы (безвозвратно).
    """
    template = get_template(db, template_id, include_deleted=True)
    db.delete(template)
    try:
        db.commit()
        logger.info(f"Hard-deleted template {template_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error hard-deleting template {template_id}: {e}")
        raise TemplateValidationError(f"Error during hard delete: {str(e)}")

from app.schemas.project import ProjectCreate
from app.crud.project import create_project as crud_create_project
from app.models.task import Task
from app.crud.task import create_task as crud_create_task

def clone_template_to_project(
    db: Session,
    source_template: Template,
    project_create_data: ProjectCreate,
    new_project_author_id: int
) -> Project:
    """
    Клонирует шаблон (Template) в новый проект с задачами.
    """
    project_dict = project_create_data.model_dump(exclude_unset=True)
    project_dict["author_id"] = new_project_author_id

    if not project_dict.get("description") and isinstance(source_template.structure, dict):
        project_dict["description"] = source_template.structure.get("description", "")

    new_project = crud_create_project(db=db, data=project_dict)
    db.flush()

    if isinstance(source_template.structure, dict) and "tasks" in source_template.structure:
        for task_def in source_template.structure.get("tasks", []):
            if not isinstance(task_def, dict) or not task_def.get("title"):
                logger.warning(f"Skipping invalid task definition in template {source_template.id}: {task_def}")
                continue
            task_create_data = {
                "title": task_def["title"],
                "description": task_def.get("description", ""),
                "status": task_def.get("status", "todo"),
                "priority": task_def.get("priority", 3),
                "project_id": new_project.id,
                "assignees": task_def.get("assignees", []),
                "tags": task_def.get("tags", []),
                "custom_fields": task_def.get("custom_fields", {}),
            }
            if task_def.get("deadline"):
                try:
                    task_create_data["deadline"] = datetime.strptime(task_def["deadline"], "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"Invalid deadline format in template task: {task_def.get('deadline')}")
            crud_create_task(db=db, data=task_create_data)
    db.commit()
    db.refresh(new_project)
    logger.info(f"Project {new_project.id} ('{new_project.name}') created from template {source_template.id}.")
    return new_project

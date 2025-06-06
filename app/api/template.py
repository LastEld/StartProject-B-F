#app/api/template.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.schemas.template import (
    TemplateCreate, TemplateRead, TemplateUpdate, TemplateShort
)
from app.crud import template as crud_template
from app.models.user import User as UserModel
from app.core.exceptions import (
    SpecificTemplateNotFoundError,
    DuplicateProjectName as DuplicateTemplateName,
    ProjectValidationError as TemplateValidationError,
)
from app.dependencies import get_db, get_current_active_user
from app.schemas.response import SuccessResponse
from app.schemas.project import ProjectCreate, ProjectRead
from app.crud.project import create_project as crud_create_project_from_template_logic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])

@router.post("/", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
def create_new_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """Создать новый шаблон. Автор назначается автоматически."""
    try:
        template = crud_template.create_template(db, data.model_dump(), author_id=user.id)
        return template
    except DuplicateTemplateName as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TemplateValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating template: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")

@router.get("/{template_id}", response_model=TemplateRead)
def get_one_template(
    template_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """Получить шаблон по ID. Приватные шаблоны доступны только автору или суперюзеру."""
    try:
        template = crud_template.get_template(db, template_id)
        if template.is_private and not user.is_superuser and template.author_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this private template.")
        return template
    except SpecificTemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in get_one_template: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")

@router.get("/", response_model=List[TemplateShort])
def list_templates(
    is_active: Optional[bool] = Query(None),
    subscription_level: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    author_id: Optional[int] = Query(None),
    show_archived: Optional[bool] = Query(False, description="Include archived (soft-deleted) templates. Superuser only."),
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """Получить список шаблонов. Приватные шаблоны видны только авторам или суперюзеру."""
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if subscription_level:
        filters["subscription_level"] = subscription_level
    if tag:
        filters["tag"] = tag
    if name:
        filters["name"] = name
    if author_id is not None:
        filters["author_id"] = author_id
    if show_archived and user.is_superuser:
        filters["show_archived"] = True

    return crud_template.get_all_templates(db, current_user=user, filters=filters)

@router.patch("/{template_id}", response_model=TemplateRead)
def update_one_template(
    template_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """Обновить шаблон. Доступно только автору или суперюзеру."""
    try:
        template = crud_template.get_template(db, template_id)
        if not user.is_superuser and template.author_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this template.")
        updated_template = crud_template.update_template(db, template_id, data.model_dump(exclude_unset=True))
        return updated_template
    except SpecificTemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    except TemplateValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")

@router.delete("/{template_id}", response_model=SuccessResponse)
def delete_one_template(
    template_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """Удалить шаблон. Доступно только автору или суперюзеру."""
    try:
        template = crud_template.get_template(db, template_id)
        if not user.is_superuser and template.author_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this template.")
        crud_template.soft_delete_template(db, template_id)
        return SuccessResponse(result=template_id, detail="Template archived (soft-deleted)")
    except SpecificTemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting template: {str(e)}")

@router.post("/{template_id}/restore", response_model=TemplateRead)
def restore_one_template(
    template_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """Восстановить шаблон. Доступно только автору или суперюзеру."""
    try:
        template = crud_template.get_template(db, template_id, include_deleted=True)
        if not user.is_superuser and template.author_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to restore this template.")
        return crud_template.restore_template(db, template_id)
    except SpecificTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TemplateValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error restoring template {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred during restore.")

@router.post("/{template_id}/clone", response_model=ProjectRead)
def clone_template(
    template_id: int,
    project_create_data: ProjectCreate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """
    Клонировать шаблон в новый проект. Пользователь должен иметь доступ к шаблону.
    Новый проект будет принадлежать текущему пользователю.
    """
    try:
        template = crud_template.get_template(db, template_id)
        if template.is_private and not user.is_superuser and template.author_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to clone this private template.")
        new_project = crud_template.clone_template_to_project(
            db=db,
            source_template=template,
            project_create_data=project_create_data,
            new_project_author_id=user.id
        )
        return new_project
    except SpecificTemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    except DuplicateTemplateName as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TemplateValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create project from template: {str(e)}")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error cloning template {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred during clone operation.")

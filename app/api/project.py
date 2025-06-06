#app/api/project.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.schemas.project import (
    ProjectCreate, ProjectRead, ProjectUpdate, ProjectShort
)
from app.crud.project import (
    create_project,
    get_project,
    get_all_projects,
    update_project,
    soft_delete_project,
    restore_project,
    get_ai_context,
    summarize_project,
)
from app.dependencies import (
    get_db, get_current_active_user,
    get_project_for_user_or_404_403, get_deleted_project_for_user_or_404_403
)
from app.schemas.response import SuccessResponse
from app.core.exceptions import ProjectNotFound, ProjectValidationError, DuplicateProjectName
from app.models.user import User as DBUser
from app.models.project import Project as ProjectModel

import logging

router = APIRouter(prefix="/projects", tags=["Projects"])
logger = logging.getLogger("DevOS.ProjectsAPI")

@router.post("/", response_model=ProjectRead)
def create_new_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Создать новый проект.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create projects")
    try:
        project = create_project(db, data.model_dump())
        return project
    except (ProjectValidationError, DuplicateProjectName) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in create_new_project: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while creating the project.")

@router.get("/{project_id}", response_model=ProjectRead)
async def get_one_project(
    project: ProjectModel = Depends(get_project_for_user_or_404_403)
):
    """
    Получить проект по ID.
    """
    return project

@router.get("/", response_model=List[ProjectShort])
def list_projects(
    project_status: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    deadline: Optional[str] = Query(None),
    deadline_from: Optional[str] = Query(None),
    deadline_to: Optional[str] = Query(None),
    priority: Optional[int] = Query(None, ge=1, le=5),
    custom_fields: Optional[Dict[str, Any]] = None,
    is_favorite: Optional[bool] = Query(None),
    show_archived: bool = Query(False),
    sort_by: Optional[str] = Query("created_at"),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Получить список проектов с фильтрацией.
    """
    filters = {
        "project_status": project_status,
        "tag": tag,
        "search": search,
        "deadline": deadline,
        "deadline_from": deadline_from,
        "deadline_to": deadline_to,
        "priority": priority,
        "custom_fields": custom_fields,
        "is_favorite": is_favorite,
        "show_archived": show_archived,
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    try:
        return get_all_projects(db, current_user=current_user, filters=filters, sort_by=sort_by)
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch projects.")

@router.patch("/{project_id}", response_model=ProjectRead)
async def update_one_project(
    data: ProjectUpdate,
    project_to_update: ProjectModel = Depends(get_project_for_user_or_404_403),
    db: Session = Depends(get_db)
):
    """
    Обновить проект.
    """
    try:
        updated_project = update_project(db, project_to_update.id, data.model_dump(exclude_unset=True))
        return updated_project
    except HTTPException as http_exc:
        raise http_exc
    except ProjectValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update project {project_to_update.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during project update.")

@router.delete("/{project_id}", response_model=SuccessResponse)
async def delete_project(
    project_to_delete: ProjectModel = Depends(get_deleted_project_for_user_or_404_403),
    db: Session = Depends(get_db)
):
    """
    Архивировать проект (soft-delete).
    """
    try:
        soft_delete_project(db, project_to_delete.id)
        return SuccessResponse(result=project_to_delete.id, detail="Project archived")
    except HTTPException as http_exc:
        raise http_exc
    except ProjectValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to soft-delete project {project_to_delete.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during project deletion.")

@router.post("/{project_id}/restore", response_model=SuccessResponse)
async def restore_deleted_project(
    project_to_restore: ProjectModel = Depends(get_deleted_project_for_user_or_404_403),
    db: Session = Depends(get_db)
):
    """
    Восстановить архивированный проект.
    """
    try:
        restored_project_obj = restore_project(db, project_to_restore.id)
        return SuccessResponse(result=restored_project_obj.id, detail="Project restored")
    except HTTPException as http_exc:
        raise http_exc
    except ProjectValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore project {project_to_restore.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during project restoration.")

@router.get("/{project_id}/ai_context", response_model=Dict[str, Any])
async def get_project_ai_context(
    project: ProjectModel = Depends(get_project_for_user_or_404_403),
    db: Session = Depends(get_db)
):
    """
    Получить AI-контекст по проекту.
    """
    try:
        return get_ai_context(db, project.id)
    except ProjectNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get AI context for project {project.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while fetching AI context.")

@router.get("/{project_id}/summary", response_model=str)
async def project_summary(
    project: ProjectModel = Depends(get_project_for_user_or_404_403),
    db: Session = Depends(get_db)
):
    """
    Краткое описание проекта для AI/сводки.
    """
    try:
        return summarize_project(db, project.id)
    except Exception as e:
        logger.error(f"Failed to summarize project {project.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during project summary.")

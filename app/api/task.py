#app/api/task.py
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.schemas.task import (
    TaskCreate, TaskRead, TaskUpdate, TaskShort
)
from app.crud.task import (
    create_task,
    get_task,
    get_all_tasks,
    update_task,
    soft_delete_task,
    restore_task,
    get_ai_context,
    summarize_task,
)
from app.dependencies import get_db, get_current_active_user
from app.schemas.response import SuccessResponse
from app.crud.project import get_project
from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.core.exceptions import ProjectNotFound, TaskNotFound, TaskValidationError

logger = logging.getLogger("DevOS.TasksAPI")

router = APIRouter(prefix="/tasks", tags=["Tasks"])

def _check_project_permission_and_get_project(db: Session, project_id: int, current_user: UserModel) -> ProjectModel:
    try:
        project = get_project(db, project_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with id {project_id} not found.")
    if not current_user.is_superuser and project.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions for the parent project."
        )
    return project

@router.post("/", response_model=TaskRead)
def create_new_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    task_status: Optional[str] = Query(None),
):
    """
    Создать новую задачу.
    """
    _check_project_permission_and_get_project(db, data.project_id, current_user)
    try:
        task = create_task(db, data.model_dump())
        return task
    except TaskValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error during task creation.")

@router.get("/{task_id}", response_model=TaskRead)
def get_one_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    task_status: Optional[str] = Query(None),
):
    """
    Получить задачу по ID.
    """
    try:
        task = get_task(db, task_id)
    except TaskNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    _check_project_permission_and_get_project(db, task.project_id, current_user)
    return task

@router.get("/", response_model=List[TaskShort])
def list_tasks(
    project_id: Optional[int] = Query(None),
    task_status: Optional[str] = Query(None),  # <-- вот так!
    #status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    deadline_before: Optional[str] = Query(None),
    deadline_after: Optional[str] = Query(None),
    parent_task_id: Optional[int] = Query(None),
    priority: Optional[int] = Query(None, ge=1, le=5),
    tag: Optional[str] = Query(None),
    custom_fields: Optional[Dict[str, Any]] = None,
    assignee_id: Optional[int] = Query(None),
    show_archived: bool = Query(False),
    sort_by: Optional[str] = Query("deadline"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Получить список задач с фильтрацией и поиском.
    """
    if project_id:
        _check_project_permission_and_get_project(db, project_id, current_user)
    elif not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to all tasks is restricted. Please specify a project_id."
        )

    filters = {
        "project_id": project_id,
        "task_status": task_status,
        "search": search,
        "deadline_before": deadline_before,
        "deadline_after": deadline_after,
        "parent_task_id": parent_task_id,
        "priority": priority,
        "tag": tag,
        "custom_fields": custom_fields,
        "assignee_id": assignee_id,
        "show_archived": show_archived,
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    return get_all_tasks(db, filters=filters, sort_by=sort_by)

@router.patch("/{task_id}", response_model=TaskRead)
def update_one_task(
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    task_status: Optional[str] = Query(None),
):
    """
    Обновить задачу.
    """
    try:
        task_to_update = get_task(db, task_id)
    except TaskNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    _check_project_permission_and_get_project(db, task_to_update.project_id, current_user)

    try:
        task = update_task(db, task_id, data.model_dump(exclude_unset=True))
        return task
    except TaskValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")

@router.delete("/{task_id}", response_model=SuccessResponse)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    task_status: Optional[str] = Query(None),
):
    """
    Архивировать задачу (soft-delete).
    """
    try:
        task_to_delete = get_task(db, task_id, include_deleted=True)
    except TaskNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    _check_project_permission_and_get_project(db, task_to_delete.project_id, current_user)
    try:
        soft_delete_task(db, task_id)
        return SuccessResponse(result=task_id, detail="Task archived")
    except TaskValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error during task deletion.")

@router.post("/{task_id}/restore", response_model=SuccessResponse)
def restore_deleted_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    task_status: Optional[str] = Query(None),
):
    """
    Восстановить архивированную задачу.
    """
    try:
        task_to_restore = get_task(db, task_id, include_deleted=True)
        _check_project_permission_and_get_project(db, task_to_restore.project_id, current_user)
        restore_task(db, task_id)
        return SuccessResponse(result=task_id, detail="Task restored")
    except TaskNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TaskValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ProjectNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error restoring task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error during task restore.")

@router.get("/{task_id}/ai_context", response_model=Dict[str, Any])
def get_task_ai_context(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    task_status: Optional[str] = Query(None),
):
    """
    Получить AI-контекст по задаче.
    """
    try:
        task = get_task(db, task_id)
    except TaskNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    _check_project_permission_and_get_project(db, task.project_id, current_user)
    return get_ai_context(db, task_id)

@router.get("/{task_id}/summary", response_model=str)
def task_summary(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    task_status: Optional[str] = Query(None),
):
    """
    Краткое описание задачи для AI/сводки.
    """
    try:
        task = get_task(db, task_id)
    except TaskNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    _check_project_permission_and_get_project(db, task.project_id, current_user)
    return summarize_task(db, task_id)

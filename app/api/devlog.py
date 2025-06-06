#app/api/devlog.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.schemas.devlog import DevLogCreate, DevLogRead, DevLogUpdate, DevLogShort
from app.crud import devlog as crud_devlog
from app.crud import project as crud_project
from app.crud import task as crud_task
from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.models.task import Task as TaskModel
from app.schemas.response import SuccessResponse
from app.dependencies import get_db, get_current_active_user
from app.core.exceptions import (
    ProjectNotFound,
    TaskNotFound,
    DevLogNotFound,
    DevLogValidationError,
    DuplicateProjectName,
)
import logging

router = APIRouter(prefix="/devlog", tags=["DevLog"])
logger = logging.getLogger("DevOS.DevLog")

def check_project_access(db: Session, project_id: int, current_user: UserModel) -> ProjectModel:
    try:
        project = crud_project.get_project(db, project_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with id {project_id} not found.")
    if not current_user.is_superuser and project.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this project.")
    return project

@router.post("/", response_model=DevLogRead)
def create_devlog_entry(
    data: DevLogCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    project_id_to_check = data.project_id
    task_id_to_check = data.task_id
    if task_id_to_check and not project_id_to_check:
        try:
            task = crud_task.get_task(db, task_id_to_check)
            project_id_to_check = task.project_id
        except TaskNotFound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {task_id_to_check} not found.")

    if project_id_to_check:
        check_project_access(db, project_id_to_check, current_user)
    try:
        entry = crud_devlog.create_entry(db, data.model_dump(), author_id=current_user.id)
        return entry
    except (ProjectNotFound, TaskNotFound) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DevLogValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DuplicateProjectName as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating devlog: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.get("/{entry_id}", response_model=DevLogRead)
def read_devlog_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    try:
        entry = crud_devlog.get_entry(db, entry_id)
    except DevLogNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DevLog entry not found")

    if entry.is_deleted and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DevLog entry not found or has been archived.")

    can_access_via_project = False
    if entry.project_id:
        try:
            check_project_access(db, entry.project_id, current_user)
            can_access_via_project = True
        except HTTPException:
            pass
    elif entry.task_id:
        try:
            task = crud_task.get_task(db, entry.task_id)
            check_project_access(db, task.project_id, current_user)
            can_access_via_project = True
        except (TaskNotFound, HTTPException):
            pass

    if not (current_user.is_superuser or entry.author_id == current_user.id or can_access_via_project):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to read this DevLog entry.")

    return entry

@router.patch("/{entry_id}", response_model=DevLogRead)
def update_devlog_entry(
    entry_id: int,
    data: DevLogUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    try:
        entry_to_update = crud_devlog.get_entry(db, entry_id)
    except DevLogNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DevLog entry not found.")

    if entry_to_update.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update an archived DevLog entry. Please restore it first.")

    if not (current_user.is_superuser or entry_to_update.author_id == current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this DevLog entry.")

    update_data = data.model_dump(exclude_unset=True)
    new_project_id_to_check = update_data.get("project_id")
    new_task_id_to_check = update_data.get("task_id")

    if new_task_id_to_check and not new_project_id_to_check:
        try:
            task = crud_task.get_task(db, new_task_id_to_check)
            new_project_id_to_check = task.project_id
        except TaskNotFound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target task with id {new_task_id_to_check} not found.")

    if new_project_id_to_check and new_project_id_to_check != entry_to_update.project_id:
        check_project_access(db, new_project_id_to_check, current_user)

    try:
        updated_entry = crud_devlog.update_entry(db, entry_id, update_data)
        return updated_entry
    except (ProjectNotFound, TaskNotFound) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DevLogValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DevLogNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DevLog entry not found.")
    except Exception as e:
        logger.error(f"Unexpected error updating devlog: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during update.")

@router.delete("/{entry_id}", response_model=SuccessResponse)
def delete_devlog_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    try:
        entry_to_delete = crud_devlog.get_entry(db, entry_id)
    except DevLogNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DevLog entry not found.")

    if entry_to_delete.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DevLog entry already archived.")

    if not (current_user.is_superuser or entry_to_delete.author_id == current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this DevLog entry.")

    try:
        crud_devlog.soft_delete_entry(db, entry_id)
        return SuccessResponse(result=entry_id, detail="DevLog entry archived")
    except DevLogValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting devlog: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during deletion.")

@router.post("/{entry_id}/restore", response_model=SuccessResponse)
def restore_devlog_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    try:
        entry_to_restore = crud_devlog.get_entry(db, entry_id)
    except DevLogNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DevLog entry not found.")

    if not entry_to_restore.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DevLog entry is not archived.")

    if not (current_user.is_superuser or entry_to_restore.author_id == current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to restore this DevLog entry.")

    try:
        crud_devlog.restore_entry(db, entry_id)
        return SuccessResponse(result=entry_id, detail="DevLog entry restored")
    except DevLogValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error restoring devlog: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during restoration.")

@router.get("/", response_model=List[DevLogShort])
def list_devlog_entries(
    project_id: Optional[int] = Query(None),
    task_id: Optional[int] = Query(None),
    entry_type: Optional[str] = Query(None),
    author_id: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    show_archived: Optional[bool] = Query(False, description="Set to true to include archived entries"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    filters = {
        "project_id": project_id,
        "task_id": task_id,
        "entry_type": entry_type,
        "author_id": author_id,
        "tag": tag,
        "date_from": date_from,
        "date_to": date_to,
        "search": search,
        "show_archived": show_archived,
    }
    active_filters = {k: v for k, v in filters.items() if v is not None}
    if project_id is not None and not current_user.is_superuser:
        try:
            check_project_access(db, project_id, current_user)
        except HTTPException:
            pass
    result = crud_devlog.get_entries(db, current_user=current_user, filters=active_filters, page=page, per_page=per_page)
    return result["entries"]

@router.get("/{entry_id}/ai_context", response_model=Dict[str, Any])
def get_entry_ai_context(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    try:
        entry = read_devlog_entry(entry_id, db, current_user)
        return crud_devlog.get_ai_context(db, entry.id)
    except HTTPException:
        raise
    except DevLogNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DevLog entry not found for AI context.")

@router.get("/{entry_id}/summary", response_model=str)
def summarize_devlog_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    try:
        entry = read_devlog_entry(entry_id, db, current_user)
        return crud_devlog.summarize_entry(db, entry.id)
    except HTTPException:
        raise
    except DevLogNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DevLog entry not found for summary.")

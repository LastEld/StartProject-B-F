#app/api/plugin.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.plugin import (
    PluginCreate, PluginRead, PluginUpdate, PluginShort
)
from app.crud.plugin import (
    create_plugin,
    get_plugin,
    get_all_plugins,
    update_plugin,
    soft_delete_plugin,
    restore_plugin,
    activate_plugin,
    deactivate_plugin,
    get_active_plugins_summary,
    run_plugin_action,
)
from app.dependencies import get_db, get_current_active_user
from app.schemas.response import SuccessResponse
from app.models.user import User as UserModel
from app.core.exceptions import PluginNotFoundError, PluginValidationError

import logging

router = APIRouter(prefix="/plugins", tags=["Plugins"])
logger = logging.getLogger("DevOS.PluginAPI")

@router.post("/", response_model=PluginRead)
def create_new_plugin(
    data: PluginCreate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform this action.")
    try:
        plugin = create_plugin(db, data.dict())
        return plugin
    except PluginValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create plugin: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.get("/{plugin_id}", response_model=PluginRead)
def get_one_plugin(
    plugin_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    try:
        plugin = get_plugin(db, plugin_id)
        return plugin
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get plugin {plugin_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.get("/", response_model=List[PluginShort])
def list_plugins(
    is_active: Optional[bool] = Query(None),
    subscription_level: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if subscription_level:
        filters["subscription_level"] = subscription_level
    if tag:
        filters["tag"] = tag
    try:
        return get_all_plugins(db, filters=filters)
    except Exception as e:
        logger.error(f"Failed to list plugins: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.patch("/{plugin_id}", response_model=PluginRead)
def update_one_plugin(
    plugin_id: int,
    data: PluginUpdate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform this action.")
    try:
        updated_data = data.dict(exclude_unset=True)
        plugin = update_plugin(db, plugin_id, updated_data)
        return plugin
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PluginValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update plugin {plugin_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.delete("/{plugin_id}", response_model=SuccessResponse)
def delete_one_plugin(
    plugin_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform this action.")
    try:
        deleted_plugin = soft_delete_plugin(db, plugin_id)
        if not deleted_plugin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found or already deleted.")
        return SuccessResponse(result=plugin_id, detail="Plugin archived (soft-deleted)")
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to soft-delete plugin {plugin_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.post("/{plugin_id}/restore", response_model=PluginRead)
def restore_one_plugin(
    plugin_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform this action.")
    try:
        restored_plugin = restore_plugin(db, plugin_id)
        return restored_plugin
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PluginValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore plugin {plugin_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.post("/{plugin_id}/activate", response_model=PluginRead)
def activate_plugin_endpoint(
    plugin_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform this action.")
    try:
        return activate_plugin(db, plugin_id)
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PluginValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to activate plugin {plugin_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.post("/{plugin_id}/deactivate", response_model=PluginRead)
def deactivate_plugin_endpoint(
    plugin_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform this action.")
    try:
        return deactivate_plugin(db, plugin_id)
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PluginValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to deactivate plugin {plugin_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.get("/active/summary", response_model=str)
def get_plugins_summary(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    try:
        return get_active_plugins_summary(db)
    except Exception as e:
        logger.error(f"Failed to get active plugins summary: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.post("/run/{plugin_name}/{action_name}", response_model=str)
def run_plugin(
    plugin_name: str,
    action_name: str,
    project_context: dict,
    plugin_params: Optional[dict] = None,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform this action.")
    try:
        return run_plugin_action(db, plugin_name, action_name, project_context, plugin_params or {})
    except Exception as e:
        logger.error(f"Failed to run plugin action '{action_name}' for '{plugin_name}': {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

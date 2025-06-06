#app/api/plugin.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.plugin import (
    PluginCreate, PluginRead, PluginUpdate, PluginShort
)
from app.crud.plugin import ( # Ensure all used CRUD functions are imported
    create_plugin,
    get_plugin,
    get_plugin_by_name, # Added for completeness, though not directly used by new API logic
    get_all_plugins,
    update_plugin,
    soft_delete_plugin,
    restore_plugin,
    activate_plugin,
    deactivate_plugin,
    get_active_plugins_summary,
    run_plugin_action,
    hard_delete_plugin # Import hard_delete_plugin
)
from app.dependencies import get_db, get_current_active_user, get_superuser # Import get_superuser
from app.schemas.response import SuccessResponse # For delete responses
from app.models.user import User as UserModel
from app.core.exceptions import PluginNotFoundError, PluginValidationError, ForbiddenError # Added ForbiddenError

import logging

router = APIRouter(prefix="/plugins", tags=["Plugins"])
logger = logging.getLogger("DevOS.PluginAPI")

@router.post("/", response_model=PluginRead)
def create_new_plugin(
    data: PluginCreate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    # No superuser check needed here, any authenticated user can attempt to create.
    # CRUD layer will handle setting author_id.
    try:
        plugin = create_plugin(db, data.dict(), author_id=user.id)
        return plugin
    except PluginValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create plugin: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during plugin creation.")

@router.get("/{plugin_id}", response_model=PluginRead)
def get_one_plugin(
    plugin_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user) # Renamed for clarity
):
    try:
        # CRUD function now handles permission check
        plugin = get_plugin(db, plugin_id, current_user=current_user)
        return plugin
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get plugin {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.get("/", response_model=List[PluginShort]) # Using PluginShort for lists
def list_plugins(
    is_active: Optional[bool] = Query(None),
    is_private: Optional[bool] = Query(None), # New filter for privacy
    subscription_level: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None), # New search filter
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user) # Renamed
):
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if is_private is not None:
        filters["is_private"] = is_private
    if subscription_level:
        filters["subscription_level"] = subscription_level
    if tag:
        filters["tag"] = tag

    try:
        # CRUD function now handles permission-based filtering and search
        plugins = get_all_plugins(db, current_user=current_user, filters=filters, search=search)
        return plugins # FastAPI will handle converting List[Plugin] to List[PluginShort]
    except Exception as e:
        logger.error(f"Failed to list plugins: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.patch("/{plugin_id}", response_model=PluginRead)
def update_one_plugin(
    plugin_id: int,
    data: PluginUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user) # Renamed
):
    # Permission check (author or superuser) is handled by crud.update_plugin
    try:
        updated_data = data.dict(exclude_unset=True)
        plugin = update_plugin(db, plugin_id, updated_data, current_user=current_user)
        return plugin
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PluginValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update plugin {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.delete("/{plugin_id}", response_model=SuccessResponse)
def delete_one_plugin(
    plugin_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user) # Renamed
):
    # Permission check (author or superuser) is handled by crud.soft_delete_plugin
    try:
        # soft_delete_plugin now takes current_user
        deleted_plugin = soft_delete_plugin(db, plugin_id, current_user=current_user)
        # No need to check if deleted_plugin, exception will be raised by CRUD if not found or no access
        return SuccessResponse(result=plugin_id, detail="Plugin archived (soft-deleted)")
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to soft-delete plugin {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.post("/{plugin_id}/restore", response_model=SuccessResponse) # Changed response_model
def restore_one_plugin(
    plugin_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user) # Renamed
):
    # Permission check (author or superuser) is handled by crud.restore_plugin
    try:
        # restore_plugin now takes current_user
        restored_plugin = restore_plugin(db, plugin_id, current_user=current_user)
        # Ensure restored_plugin is not None if restore_plugin could return None on failure,
        # but it raises exceptions instead.
        return SuccessResponse(result=restored_plugin.id, detail="Plugin restored successfully")
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PluginValidationError as e: # e.g. if plugin is not deleted
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore plugin {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.post("/{plugin_id}/activate", response_model=PluginRead)
def activate_plugin_endpoint(
    plugin_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user) # Renamed
):
    # Permission check (author or superuser) is handled by crud.activate_plugin
    try:
        # activate_plugin now takes current_user
        plugin = activate_plugin(db, plugin_id, current_user=current_user)
        return plugin
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PluginValidationError as e: # e.g. if plugin is deleted
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to activate plugin {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.post("/{plugin_id}/deactivate", response_model=PluginRead)
def deactivate_plugin_endpoint(
    plugin_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user) # Renamed
):
    # Permission check (author or superuser) is handled by crud.deactivate_plugin
    try:
        # deactivate_plugin now takes current_user
        plugin = deactivate_plugin(db, plugin_id, current_user=current_user)
        return plugin
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PluginValidationError as e: # e.g. if plugin is deleted
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to deactivate plugin {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.get("/active/summary", response_model=str) # No user context needed for this global summary
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
    project_context: dict, # Consider making this a Pydantic model for validation
    plugin_params: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user) # Renamed
):
    # Access control for running plugin actions might be complex:
    # - Is the plugin globally runnable?
    # - Does the user have rights to run actions for this specific plugin (if private)?
    # - Does the user have rights in the project_context?
    # The current crud.run_plugin_action has basic checks (exists, active).
    # A superuser check here is a simplification.
    if not current_user.is_superuser: # Simplified: only superuser can run any plugin action for now
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to run plugin actions.")
    try:
        result = run_plugin_action(db, plugin_name, action_name, project_context, plugin_params or {})
        return result
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PluginValidationError as e: # e.g. plugin not active
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to run plugin action '{action_name}' for '{plugin_name}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error running plugin action: {str(e)}")


@router.delete("/{plugin_id}/force", status_code=status.HTTP_204_NO_CONTENT)
def force_delete_one_plugin(
    plugin_id: int,
    db: Session = Depends(get_db),
    # Use get_superuser dependency to ensure only superusers can call this
    current_superuser: UserModel = Depends(get_superuser)
):
    """
    Permanently deletes a plugin from the database. Superuser access required.
    """
    try:
        # crud.hard_delete_plugin already checks if current_user is superuser.
        # Pass current_superuser to satisfy the function signature in CRUD.
        success = hard_delete_plugin(db, plugin_id, current_user=current_superuser)
        if not success: # Should not happen if exception handling is correct in CRUD
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Hard delete failed but no exception was raised.")
        # Return No Content response for successful deletion
        return None
    except PluginNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e: # Should be caught by get_superuser or crud if not superuser
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except PluginValidationError as e: # Other validation errors from CRUD
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to force-delete plugin {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during force delete.")

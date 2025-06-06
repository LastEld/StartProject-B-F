#app/api/settings.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from app.schemas.settings import SettingCreate, SettingUpdate, SettingRead
from app.crud.settings import (
    create_setting,
    get_setting,
    update_setting,
    delete_setting,
    get_all_settings
)
from app.dependencies import get_db, get_current_active_user
from app.schemas.response import SuccessResponse
from app.core.exceptions import ProjectValidationError
from app.models.user import User as UserModel
from app.models.settings import Setting as SettingModel
import logging

logger = logging.getLogger("DevOS.SettingsAPI")

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.post("/", response_model=SettingRead)
def create_new_setting(
    data: SettingCreate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """
    Создать новую настройку (глобальную или пользовательскую).
    """
    create_data_dict = data.model_dump()
    # Не суперюзер не может создать настройку для другого пользователя
    if not user.is_superuser:
        if create_data_dict.get("user_id") is not None and create_data_dict.get("user_id") != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create settings for another user.")
        create_data_dict["user_id"] = user.id
    try:
        setting = create_setting(db, create_data_dict)
        return setting
    except ProjectValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating setting: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")

@router.put("/{key}", response_model=SettingRead)
def upsert_setting(
    key: str,
    data: SettingCreate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """
    Создать или обновить настройку по ключу (upsert).
    """
    upsert_data_dict = data.model_dump()
    target_user_id = upsert_data_dict.get("user_id")
    if not user.is_superuser:
        if target_user_id is not None and target_user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to upsert settings for another user.")
        upsert_data_dict["user_id"] = user.id
        target_user_id = user.id
    try:
        existing = get_setting(db, key, user_id=target_user_id)
        if existing:
            update_payload = data.model_dump(exclude={"key"}, exclude_unset=True)
            return update_setting(db, existing.id, update_payload)
        else:
            create_payload = data.model_dump(exclude_unset=True)
            create_payload["key"] = key
            create_payload["user_id"] = target_user_id
            return create_setting(db, create_payload)
    except ProjectValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error upserting setting: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")



@router.get("/effective/{key}", response_model=SettingRead)
def get_effective_setting(
    key: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    setting = get_setting(db, key, user_id=user.id)
    if not setting:
        setting = get_setting(db, key, user_id=None)  # Фолбек на глобальное значение
    if not setting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Setting with key '{key}' not found.")
    return setting

@router.get("/{key}", response_model=SettingRead)
def get_one_setting(
    key: str,
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    target_user_id = user_id
    if not current_user.is_superuser:
        if target_user_id is not None and target_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access settings of another user.")
        target_user_id = current_user.id
    setting = get_setting(db, key, user_id=target_user_id)
    if not setting:
        detail_msg = f"Setting with key '{key}'"
        if target_user_id is not None:
            detail_msg += f" for user_id {target_user_id}"
        else:
            detail_msg += " (global)"
        detail_msg += " not found."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail_msg)
    return setting

@router.patch("/{setting_id}", response_model=SettingRead)
def update_one_setting(
    setting_id: int,
    data: SettingUpdate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    # 1. Находим настройку заранее
    setting_to_update = db.query(SettingModel).filter(SettingModel.id == setting_id).first()
    if not setting_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found.")
    if not user.is_superuser:
        if setting_to_update.user_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update global settings.")
        if setting_to_update.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update settings for another user.")
    # 2. Теперь только пробуем апдейт
    try:
        updated_setting = update_setting(db, setting_id, data.model_dump(exclude_unset=True))
        return updated_setting
    except ProjectValidationError as e:
        if "Setting not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{setting_id}", response_model=SuccessResponse)
def delete_one_setting(
    setting_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    setting_to_delete = db.query(SettingModel).filter(SettingModel.id == setting_id).first()
    if not setting_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found.")
    if not user.is_superuser:
        if setting_to_delete.user_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete global settings.")
        if setting_to_delete.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete settings for another user.")
    try:
        delete_setting(db, setting_id)
        return SuccessResponse(result=setting_id, detail="Setting deleted")
    except ProjectValidationError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        
@router.get("/", response_model=List[SettingRead])
def list_settings(
    user_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    target_user_id = user_id
    if not current_user.is_superuser:
        if target_user_id is not None and target_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to list settings for another user.")
        target_user_id = current_user.id
    settings = get_all_settings(db, user_id=target_user_id, limit=limit, skip=skip)
    return settings
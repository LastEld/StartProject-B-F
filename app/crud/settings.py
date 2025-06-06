#app/crud/settings.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.settings import Setting
from app.core.exceptions import ProjectValidationError
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger("DevOS.Settings")

def create_setting(db: Session, data: dict) -> Setting:
    """
    Создаёт новую настройку (глобальную или пользовательскую).
    """
    if db.query(Setting).filter(Setting.key == data["key"], Setting.user_id == data.get("user_id")).first():
        raise ProjectValidationError("Setting with this key already exists for this user.")
    setting = Setting(
        key=data["key"],
        value=data["value"],
        description=data.get("description"),
        user_id=data.get("user_id"),
        is_active=data.get("is_active", True)
    )
    db.add(setting)
    try:
        db.commit()
        db.refresh(setting)
        logger.info(f"Created setting '{setting.key}' (user_id={setting.user_id})")
        return setting
    except IntegrityError:
        db.rollback()
        logger.warning(f"Setting with key '{data['key']}' already exists for user_id={data.get('user_id')}")
        raise ProjectValidationError("Setting already exists.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating setting: {e}")
        raise ProjectValidationError("Database error while creating setting.")

def get_setting(db: Session, key: str, user_id: Optional[int] = None) -> Optional[Setting]:
    """
    Получить настройку по ключу и (опционально) user_id.
    """
    query = db.query(Setting).filter(Setting.key == key)
    if user_id is not None:
        query = query.filter(Setting.user_id == user_id)
    else:
        query = query.filter(Setting.user_id == None)
    return query.first()

def update_setting(db: Session, setting_id: int, data: dict) -> Setting:
    """
    Обновляет существующую настройку.
    """
    setting = db.query(Setting).filter(Setting.id == setting_id).first()
    if not setting:
        raise ProjectValidationError("Setting not found.")
    for field in ["value", "description", "is_active"]:
        if field in data:
            setattr(setting, field, data[field])
    setting.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(setting)
        logger.info(f"Updated setting {setting.key} (ID: {setting.id})")
        return setting
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating setting: {e}")
        raise ProjectValidationError("Database error while updating setting.")

def delete_setting(db: Session, setting_id: int) -> bool:
    """
    Удаляет настройку по ID.
    """
    setting = db.query(Setting).filter(Setting.id == setting_id).first()
    if not setting:
        raise ProjectValidationError("Setting not found.")
    try:
        db.delete(setting)
        db.commit()
        logger.info(f"Deleted setting (ID: {setting.id})")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting setting: {e}")
        raise ProjectValidationError("Database error while deleting setting.")

def get_all_settings(db: Session, user_id: Optional[int] = None, limit: int = 100, skip: int = 0) -> List[Setting]:
    query = db.query(Setting)
    if user_id is not None:
        query = query.filter(Setting.user_id == user_id)
    else:
        query = query.filter(Setting.user_id == None)
    return query.order_by(Setting.key).offset(skip).limit(limit).all()
    


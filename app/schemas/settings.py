#app/schemas/settings.py
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

class SettingBase(BaseModel):
    """
    SettingBase — базовая схема для системной/пользовательской настройки.
    """
    key: str = Field(..., example="theme", description="Ключ настройки")
    value: Any = Field(..., example="dark", description="Значение настройки")
    description: Optional[str] = Field(None, example="UI theme for the app", description="Описание настройки")
    is_active: Optional[bool] = Field(True, description="Включена ли настройка")

class SettingCreate(SettingBase):
    """
    SettingCreate — создание настройки (user_id может быть передан отдельно).
    """
    user_id: Optional[int] = Field(None, description="ID пользователя (NULL = глобальная настройка)")

class SettingUpdate(BaseModel):
    """
    SettingUpdate — обновление настройки (все поля опциональны).
    """
    value: Optional[Any] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class SettingRead(SettingBase):
    """
    SettingRead — чтение настройки с метаданными (id, user_id, timestamps).
    """
    id: int
    user_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

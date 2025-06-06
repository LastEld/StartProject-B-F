#app/schemas/plugin.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class PluginBase(BaseModel):
    """
    PluginBase — основная схема для плагинов системы (мета, конфиг, soft-delete, доступ).
    """
    name: str = Field(..., example="kanban", description="Уникальное имя плагина")
    description: Optional[str] = Field(None, example="Task Kanban board", description="Описание плагина")
    config_json: Dict[str, Any] = Field(default_factory=dict, example={"columns": ["To Do", "In Progress", "Done"]}, description="Основная конфигурация")
    is_active: Optional[bool] = Field(True, description="Включен ли плагин?")
    version: Optional[str] = Field(None, example="1.0.0", description="Версия плагина")
    author: Optional[str] = Field(None, example="lasteld@devos.io", description="Автор/Email")
    subscription_level: Optional[str] = Field(None, example="Pro", description="Уровень подписки: Free/Pro/VIP")
    is_private: Optional[bool] = Field(False, description="Приватный плагин?")
    ui_component: Optional[str] = Field(None, example="KanbanBoard", description="Компонент фронта")
    tags: List[str] = Field(default_factory=list, example=["kanban", "board"], description="Теги для поиска/фильтрации")
    is_deleted: bool = Field(False, description="Soft-delete флаг")
    deleted_at: Optional[datetime] = Field(None, description="Дата soft-delete")

class PluginCreate(BaseModel):
    """
    PluginCreate — создание нового плагина.
    """
    name: str = Field(..., example="kanban")
    description: Optional[str] = Field(None, example="Task Kanban board")
    config_json: Dict[str, Any] = Field(default_factory=dict, example={"columns": ["To Do", "In Progress", "Done"]})
    is_active: Optional[bool] = Field(True, description="Включен ли плагин?")
    version: Optional[str] = Field(None, example="1.0.0")
    author: Optional[str] = Field(None, example="lasteld@devos.io")
    subscription_level: Optional[str] = Field(None, example="Pro")
    is_private: Optional[bool] = Field(False, description="Приватный плагин?")
    ui_component: Optional[str] = Field(None, example="KanbanBoard")
    tags: List[str] = Field(default_factory=list, example=["kanban", "board"])

class PluginUpdate(BaseModel):
    """
    PluginUpdate — обновление плагина (все поля опциональные).
    """
    name: Optional[str] = None
    description: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    version: Optional[str] = None
    author: Optional[str] = None
    subscription_level: Optional[str] = None
    is_private: Optional[bool] = None
    ui_component: Optional[str] = None
    tags: Optional[List[str]] = None

class PluginShort(BaseModel):
    """
    PluginShort — сокращённая схема для списка плагинов.
    """
    id: int
    name: str
    is_active: bool
    is_deleted: bool = Field(False)

    class Config:
        orm_mode = True

class PluginRead(PluginBase):
    """
    PluginRead — полная схема плагина для выдачи в API.
    """
    id: int

    class Config:
        orm_mode = True

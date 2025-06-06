#app/schemas/plugin.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class PluginBase(BaseModel):
    """
    PluginBase — Defines core, user-editable fields for a plugin.
    Does not include system-managed fields like id, author_id, audit stamps, or soft-delete status.
    """
    name: str = Field(
        ...,
        example="kanban",
        description="Уникальное имя плагина",
        min_length=3,
        max_length=50
    )
    description: Optional[str] = Field(None, example="Task Kanban board", description="Описание плагина", max_length=500)
    config_json: Dict[str, Any] = Field(default_factory=dict, example={"columns": ["To Do", "In Progress", "Done"]}, description="Основная конфигурация")
    is_active: Optional[bool] = Field(True, description="Включен ли плагин? (по умолчанию True при создании)")
    version: Optional[str] = Field(
        None,
        example="1.0.0",
        description="Версия плагина (например, семантическое версионирование X.Y.Z)",
        pattern=r"^\d+\.\d+\.\d+$" # Example: Semantic Versioning (e.g., 1.0.0, 0.2.1)
    )
    subscription_level: Optional[str] = Field(None, example="Pro", description="Уровень подписки: Free/Pro/VIP", max_length=32)
    is_private: Optional[bool] = Field(False, description="Приватный плагин? (по умолчанию False при создании)")
    ui_component: Optional[str] = Field(None, example="KanbanBoard", description="Компонент фронта")
    tags: List[str] = Field(default_factory=list, example=["kanban", "board"], description="Теги для поиска/фильтрации")

class PluginCreate(PluginBase):
    """
    PluginCreate — Schema for creating a new plugin. Inherits editable fields from PluginBase.
    author_id is set by the system (current user) in the CRUD layer, not part of this payload.
    """
    pass # Inherits all fields from PluginBase

class PluginUpdate(BaseModel):
    """
    PluginUpdate — обновление плагина (все поля опциональные).
    """
    name: Optional[str] = Field(None, min_length=3, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    config_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    version: Optional[str] = Field(None, pattern=r"^\d+\.\d+\.\d+$")
    # author_id typically should not be updated directly via this schema.
    subscription_level: Optional[str] = Field(None, max_length=32)
    is_private: Optional[bool] = None
    ui_component: Optional[str] = Field(None, max_length=64) # Added max_length from model
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
    PluginRead — Полная схема плагина для выдачи в API.
    Inherits from PluginBase and adds system-managed fields.
    """
    id: int
    author_id: int = Field(..., description="ID автора плагина (пользователя)")

    # Fields inherited from PluginBase are fine if their optionality is acceptable for read.
    # Override fields from PluginBase if they must be non-optional in Read model
    name: str # from PluginBase, but ensuring it's here
    is_active: bool # from PluginBase, but ensuring it's non-optional
    is_private: bool # from PluginBase, but ensuring it's non-optional

    # System-managed fields
    is_deleted: bool = Field(..., description="Soft-delete флаг")
    deleted_at: Optional[datetime] = Field(None, description="Дата soft-delete")
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

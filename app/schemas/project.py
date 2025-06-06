#app/schemas/project.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

from app.schemas.participant import Participant
from app.schemas.attachment import Attachment

class ProjectBase(BaseModel):
    """
    ProjectBase — базовая схема проекта.
    """
    name: str = Field(..., example="My Project", description="Название проекта")
    description: Optional[str] = Field("", example="Project description", description="Описание")
    project_status: Optional[str] = Field("active", example="active", description="Статус: active, archived, done")
    deadline: Optional[date] = Field(None, example="2024-12-31", description="Дедлайн")
    priority: int = Field(3, ge=1, le=5, example=3, description="Приоритет (1-5)")
    tags: List[str] = Field(default_factory=list, example=["python", "startup"], description="Теги проекта")
    linked_repo: Optional[str] = Field(None, example="https://github.com/username/repo", description="Ссылка на репозиторий")
    color: Optional[str] = Field(None, example="#FFAA00", description="Цветовая метка (HEX)")
    participants: List[Participant] = Field(default_factory=list, description="Участники проекта")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Кастомные поля")
    parent_project_id: Optional[int] = Field(None, example=123, description="ID родительского проекта")
    attachments: List[Attachment] = Field(default_factory=list, description="Вложения")
    is_favorite: bool = Field(False, description="В избранном")
    ai_notes: Optional[str] = Field(None, example="AI project summary or prompt", description="AI summary/prompt")
    external_id: Optional[str] = Field(None, example="PRJ-4567", description="Внешний ID")
    subscription_level: Optional[str] = Field(None, example="Pro", description="Подписка: Free, Pro, VIP")
    author_id: Optional[int] = Field(None, description="ID автора проекта")
    team_id: Optional[int] = Field(None, description="ID команды")

class ProjectCreate(ProjectBase):
    """
    ProjectCreate — схема для создания проекта.
    """
    pass  # Все поля и так унаследованы, author_id выставляется на сервере

class ProjectUpdate(BaseModel):
    """
    ProjectUpdate — схема для обновления проекта (все поля опциональны).
    """
    name: Optional[str] = None
    description: Optional[str] = None
    project_status: Optional[str] = None
    deadline: Optional[date] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    linked_repo: Optional[str] = None
    color: Optional[str] = None
    participants: Optional[List[Participant]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    parent_project_id: Optional[int] = None
    attachments: Optional[List[Attachment]] = None
    is_favorite: Optional[bool] = None
    ai_notes: Optional[str] = None
    external_id: Optional[str] = None
    subscription_level: Optional[str] = None
    author_id: Optional[int] = None
    team_id: Optional[int] = None

class ProjectShort(BaseModel):
    """
    ProjectShort — сокращённая схема для списка проектов.
    """
    id: int
    name: str
    author_id: Optional[int] = None

    class Config:
        orm_mode = True

class ProjectRead(ProjectBase):
    """
    ProjectRead — схема полного вывода проекта (response).
    """
    id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        orm_mode = True

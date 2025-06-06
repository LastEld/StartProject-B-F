#app/schemas/task.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

from app.schemas.assignee import Assignee
from app.schemas.attachment import Attachment

class TaskBase(BaseModel):
    """
    TaskBase — базовая схема задачи (используется для create/read).
    """
    title: str = Field(..., example="Implement login page", description="Название задачи")
    description: Optional[str] = Field("", example="Detailed description", description="Описание задачи")
    task_status: str = Field("todo", example="todo", description="Статус задачи: todo, in progress, done, blocked, cancelled")
    priority: int = Field(3, ge=1, le=5, example=3, description="Приоритет (1-5)")
    deadline: Optional[date] = Field(None, example="2024-12-31", description="Дедлайн")
    assignees: List[Assignee] = Field(default_factory=list, description="Назначенные исполнители")
    tags: List[str] = Field(default_factory=list, description="Теги задачи")
    project_id: int = Field(..., example=1, description="ID проекта")
    parent_task_id: Optional[int] = Field(None, example=2, description="ID родительской задачи (если есть)")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Кастомные поля задачи")
    attachments: List[Attachment] = Field(default_factory=list, description="Вложения (файлы)")
    is_favorite: bool = Field(False, description="В избранном у пользователя?")
    ai_notes: Optional[str] = Field(None, example="AI suggestions for this task.", description="AI-заметки/подсказки")
    external_id: Optional[str] = Field(None, example="TASK-1001", description="Внешний идентификатор")
    reviewed: bool = Field(False, description="Задача проверена менеджером/QA?")

class TaskCreate(TaskBase):
    """
    TaskCreate — создание новой задачи.
    """
    pass

class TaskUpdate(BaseModel):
    """
    TaskUpdate — обновление задачи (все поля опциональны).
    """
    title: Optional[str] = None
    description: Optional[str] = None
    task_status: Optional[str] = None
    priority: Optional[int] = None
    deadline: Optional[date] = None
    assignees: Optional[List[Assignee]] = None
    tags: Optional[List[str]] = None
    project_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    custom_fields: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Attachment]] = None
    is_favorite: Optional[bool] = None
    ai_notes: Optional[str] = None
    external_id: Optional[str] = None
    reviewed: Optional[bool] = None

class TaskShort(BaseModel):
    """
    TaskShort — короткая схема задачи для списков/выборок.
    """
    id: int
    title: str
    project_id: int
    task_status: str
    
    class Config:
        orm_mode = True

class TaskRead(TaskBase):
    """
    TaskRead — полная схема задачи для ответа (response).
    """
    id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    task_status: str

    class Config:
        orm_mode = True

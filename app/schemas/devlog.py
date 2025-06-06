#app/schemas/devlog.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schemas.attachment import Attachment
from app.schemas.user import UserRead

class DevLogBase(BaseModel):
    """
    DevLogBase — базовая схема для записи devlog (журнала разработки).
    """
    project_id: Optional[int] = Field(None, example=1, description="ID проекта")
    task_id: Optional[int] = Field(None, example=2, description="ID задачи")
    entry_type: str = Field("note", example="note", description="Тип записи: note, action, decision, meeting")
    content: str = Field(..., example="Implemented project structure.", description="Текст записи")
    author_id: Optional[int] = Field(None, description="ID пользователя-автора (устанавливается автоматически)")
    tags: List[str] = Field(default_factory=list, description="Теги записи")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Кастомные поля")
    attachments: List[Attachment] = Field(default_factory=list, description="Вложения")
    edit_reason: Optional[str] = Field(None, example="Fixed typo", description="Причина редактирования")
    ai_notes: Optional[str] = Field(None, example="AI summary for this entry.", description="AI-заметка")

class DevLogCreate(BaseModel):
    """
    DevLogCreate — для создания новой записи devlog.
    """
    project_id: Optional[int] = Field(None, example=1)
    task_id: Optional[int] = Field(None, example=2)
    entry_type: str = Field("note", example="note")
    content: str = Field(..., example="Implemented project structure.")
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    attachments: List[Attachment] = Field(default_factory=list)
    edit_reason: Optional[str] = Field(None, example="Fixed typo")
    ai_notes: Optional[str] = Field(None, example="AI summary for this entry.")

class DevLogUpdate(BaseModel):
    """
    DevLogUpdate — для обновления записи devlog.
    """
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    entry_type: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Attachment]] = None
    edit_reason: Optional[str] = None
    ai_notes: Optional[str] = None

class DevLogShort(BaseModel):
    """
    DevLogShort — сокращённая версия записи devlog для списков.
    """
    id: int
    entry_type: str
    content: str
    author_id: int
    created_at: Optional[datetime] = None
    author: Optional[UserRead] = None

    class Config:
        orm_mode = True

class DevLogRead(DevLogBase):
    """
    DevLogRead — полная запись devlog с автором и статусом.
    """
    id: int
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool
    author: Optional[UserRead] = None

    class Config:
        orm_mode = True

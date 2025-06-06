#app/schemas/jarvis.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schemas.attachment import Attachment

class ChatMessageBase(BaseModel):
    """
    ChatMessageBase — базовая схема для сообщений чата (Jarvis).
    """
    project_id: int = Field(..., example=1, description="ID проекта")
    role: str = Field(..., example="user", description="Роль: user, assistant, system")
    content: str = Field(..., example="Let's plan our next sprint!", description="Текст сообщения")
    timestamp: Optional[datetime] = Field(None, example="2024-06-01T15:00:00Z", description="Время сообщения")
    metadata: Optional[Dict[str, Any]] = Field(None, example={"action": "ref", "source": "gpt"}, description="Служебные метаданные")
    author: Optional[str] = Field(None, example="john.doe", description="Имя/логин автора (если не user_id)")
    ai_notes: Optional[str] = Field(None, example="AI summary of the conversation.", description="AI-комментарии")
    attachments: List[Attachment] = Field(default_factory=list, description="Вложения (файлы, картинки и пр.)")
    is_deleted: bool = Field(False, description="Soft-delete flag")

class ChatMessageCreate(ChatMessageBase):
    """
    ChatMessageCreate — схема для создания сообщения.
    """
    pass

class ChatMessageUpdate(BaseModel):
    """
    ChatMessageUpdate — схема для обновления сообщения.
    """
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    author: Optional[str] = None
    ai_notes: Optional[str] = None
    attachments: Optional[List[Attachment]] = None
    is_deleted: Optional[bool] = None

class ChatMessageRead(ChatMessageBase):
    """
    ChatMessageRead — схема для отдачи сообщения в API (response).
    """
    id: int

    class Config:
        orm_mode = True

class ChatMessageShort(BaseModel):
    """
    ChatMessageShort — укороченная схема для списка сообщений.
    """
    id: int
    role: str
    content: str
    timestamp: Optional[datetime] = None

    class Config:
        orm_mode = True

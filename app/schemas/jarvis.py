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


class JarvisRequest(BaseModel):
    """
    JarvisRequest — схема для запроса к Jarvis API.
    """
    prompt: str = Field(..., description="The user's prompt for Ollama3")
    project_id: Optional[int] = Field(None, description="To provide project-specific context if available")
    session_id: Optional[str] = Field(None, description="To maintain conversation history with Ollama3 if supported")
    model: Optional[str] = Field(None, description="Specify which Ollama model to use, e.g., 'ollama3'")
    stream: Optional[bool] = Field(False, description="Whether to stream the response, default to False for now")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional Ollama parameters")


class JarvisResponse(BaseModel):
    """
    JarvisResponse — схема для ответа от Jarvis API.
    """
    response: str = Field(..., description="The text response from Ollama3")
    model: str = Field(..., description="The model that generated the response")
    created_at: datetime = Field(..., description="Timestamp of the response")
    done: bool = Field(..., description="Indicates if the response is complete, especially for streaming")
    context: Optional[List[int]] = Field(None, description="Context used for generation, if applicable from Ollama")
    total_duration: Optional[int] = Field(None, description="Total time taken for the response in nanoseconds")
    load_duration: Optional[int] = Field(None, description="Time to load the model")
    prompt_eval_count: Optional[int] = Field(None, description="Number of tokens in the prompt")
    prompt_eval_duration: Optional[int] = Field(None, description="Time to evaluate the prompt")
    eval_count: Optional[int] = Field(None, description="Number of tokens in the response")
    eval_duration: Optional[int] = Field(None, description="Time to generate the response")

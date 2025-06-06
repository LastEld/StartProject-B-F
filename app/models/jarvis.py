#app/models/jarvis.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, JSON, func, Boolean, Index
)
from app.models.base import Base

class ChatMessage(Base):
    """
    ChatMessage — сообщение чата Jarvis/AI-помощника, связано с проектом.
    Хранит role (user/assistant/system), текст, метаданные и вложения.
    """
    __tablename__ = "chat_messages"

    id: int = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_id: int = Column(Integer, ForeignKey("projects.id", ondelete='CASCADE'), nullable=False, index=True)
    timestamp: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    role: str = Column(String(20), nullable=False, doc="Роль сообщения: user, assistant, system")
    content: str = Column(Text, nullable=False)
    metadata_: dict = Column("metadata", JSON, nullable=True, doc="Служебные метаданные (например, ids, source и т.д.)")
    author: str = Column(String(64), nullable=True, doc="Имя автора, если не user из системы")
    ai_notes: str = Column(Text, nullable=True, doc="AI-комментарии")
    attachments: list = Column(JSON, nullable=False, default=lambda: [], doc="Вложения (ссылки/имена)")
    is_deleted: bool = Column(Boolean, default=False, nullable=False, doc="Флаг soft-delete")
    deleted_at: datetime = Column(DateTime(timezone=True), nullable=True, doc="Дата удаления")

    __table_args__ = (
        Index("ix_chat_messages_project_id_timestamp", "project_id", "timestamp"),
    )

    def __repr__(self):
        return (
            f"<ChatMessage(id={self.id}, project_id={self.project_id}, role='{self.role}', timestamp='{self.timestamp}')>"
        )

    def to_dict(self):
        """Конвертирует объект в словарь для чата."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata_,
            "author": self.author,
            "ai_notes": self.ai_notes,
            "attachments": self.attachments,
            "is_deleted": self.is_deleted,
        }

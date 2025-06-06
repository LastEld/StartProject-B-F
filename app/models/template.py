#app/models/template.py
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, JSON, Text, func, ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import Base

class Template(Base):
    """
    Template — шаблон для быстрого создания проектов/тасков/структуры. Поддерживает soft-delete, версионность, кастомные структуры.
    """
    __tablename__ = "templates"

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(128), nullable=False, unique=True, index=True, doc="Имя шаблона")
    description: str = Column(Text, nullable=True, doc="Описание")
    version: str = Column(String(32), nullable=False, default="1.0.0", doc="Версия шаблона")
    author_id: int = Column(Integer, ForeignKey("users.id", name="fk_template_author_id_users"), nullable=False, index=True, doc="Автор шаблона (user_id)")
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, doc="Дата создания")
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, doc="Дата изменения")
    is_active: bool = Column(Boolean, default=True, nullable=False, doc="Включен ли шаблон")
    tags: list = Column(JSON, nullable=False, default=lambda: [], doc="Теги шаблона")
    structure: dict = Column(JSON, nullable=False, doc="Структура проекта (json)")
    ai_notes: str = Column(Text, nullable=True, doc="AI-заметки")
    subscription_level: str = Column(String(32), nullable=True, doc="Подписка (Free/Pro/VIP)")
    is_private: bool = Column(Boolean, default=False, nullable=False, doc="Приватный шаблон")
    is_deleted: bool = Column(Boolean, default=False, server_default=sa.false(), nullable=False, index=True, doc="Soft-delete")
    deleted_at: datetime = Column(DateTime(timezone=True), nullable=True, doc="Дата удаления")

    author = relationship("User", backref="templates")

    def __repr__(self):
        return (
            f"<Template(id={self.id}, name='{self.name}', version='{self.version}', "
            f"author_id={self.author_id}, active={self.is_active}, deleted={self.is_deleted})>"
        )

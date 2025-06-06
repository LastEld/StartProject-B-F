#app/models/project.py
from datetime import datetime, date
from app.models.base import Base
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Text, JSON, ForeignKey, Boolean, Index, func
)

class Project(Base):
    """
    Project — основная единица управления (проект), поддерживает soft-delete, кастомные поля, теги, вложения, фавориты.
    """
    __tablename__ = "projects"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String(128), nullable=False, index=True, doc="Название проекта")
    description: str = Column(Text, nullable=True, doc="Описание")
    project_status: str = Column(String(32), nullable=False, default="active", index=True, doc="Статус: active, archived, closed и т.д.")
    deadline: date = Column(Date, nullable=True, doc="Дедлайн")
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, doc="Дата создания")
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, doc="Дата изменения")

    participants: list = Column(JSON, nullable=False, default=lambda: [], doc="Список участников [{name, email, role}]")
    tags: list = Column(JSON, nullable=False, default=lambda: [], doc="Теги проекта")
    custom_fields: dict = Column(JSON, nullable=False, default=lambda: {}, doc="Кастомные поля")
    priority: int = Column(Integer, default=3, doc="Приоритет")
    linked_repo: str = Column(String(256), nullable=True, doc="Ссылка на репозиторий")
    color: str = Column(String(7), nullable=True, doc="Цветовая метка (#hex)")
    parent_project_id: int = Column(Integer, ForeignKey('projects.id', ondelete="CASCADE"), nullable=True, doc="ID родительского проекта")
    author_id: int = Column(Integer, ForeignKey("users.id", ondelete='SET NULL'), nullable=True, doc="Автор проекта")
    team_id: int = Column(Integer, ForeignKey("teams.id", ondelete='SET NULL'), nullable=True, doc="ID команды")
    is_deleted: bool = Column(Boolean, default=False, nullable=False, doc="Soft-delete")
    is_favorite: bool = Column(Boolean, default=False, nullable=False, doc="В избранном")
    ai_notes: str = Column(Text, nullable=True, doc="AI-заметки по проекту")
    attachments: list = Column(JSON, nullable=False, default=lambda: [], doc="Вложения")
    deleted_at: datetime = Column(DateTime(timezone=True), nullable=True, doc="Дата удаления")
    external_id: str = Column(String(64), nullable=True, doc="Внешний ID")
    subscription_level: str = Column(String(32), nullable=True, doc="Подписка: Free/Pro/VIP")

    __table_args__ = (
        Index("ix_projects_deadline", "deadline"),
        Index("ix_projects_external_id", "external_id"),
    )

    def __repr__(self):
        return (
            f"<Project(id={self.id}, name='{self.name}', project_status='{self.status}', priority={self.priority})>"
        )

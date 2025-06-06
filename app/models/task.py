#app/models/task.py
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey, JSON, Boolean, Index, func
)
from sqlalchemy.orm import relationship
from app.models.base import Base

class Task(Base):
    """
    Task — универсальная задача. Поддерживает субтаски, кастомные поля, soft-delete, вложения, AI-пометки.
    """
    __tablename__ = "tasks"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    project_id: int = Column(Integer, ForeignKey("projects.id", ondelete='CASCADE'), nullable=False, index=True, doc="ID проекта")
    parent_task_id: int = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True, doc="ID родительской задачи")
    title: str = Column(String(160), nullable=False, doc="Название задачи")
    description: str = Column(String(2000), default="", doc="Описание")
    task_status: str = Column(String(24), default="todo", doc="Статус: todo, in_progress, done, ...")
    priority: int = Column(Integer, default=3, doc="Приоритет")
    deadline: date = Column(Date, nullable=True, doc="Дедлайн")
    assignees: list = Column(JSON, nullable=False, default=lambda: [], doc="Назначенные пользователи")
    tags: list = Column(JSON, nullable=False, default=lambda: [], doc="Теги задачи")
    custom_fields: dict = Column(JSON, nullable=False, default=lambda: {}, doc="Кастомные поля")
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, doc="Дата создания")
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, doc="Дата изменения")
    is_deleted: bool = Column(Boolean, default=False, nullable=False, doc="Soft-delete")
    is_favorite: bool = Column(Boolean, default=False, nullable=False, doc="В избранном")
    ai_notes: str = Column(String(2000), nullable=True, doc="AI-заметки по задаче")
    attachments: list = Column(JSON, nullable=False, default=lambda: [], doc="Вложения")
    external_id: str = Column(String(64), nullable=True, doc="Внешний ID")
    reviewed: bool = Column(Boolean, default=False, nullable=False, doc="Прошёл ли review")
    deleted_at: datetime = Column(DateTime(timezone=True), nullable=True, doc="Дата удаления")

    # Сабтаски (self-referencing)
    subtasks = relationship("Task", backref="parent", remote_side=[id], cascade="all, delete")

    __table_args__ = (
        Index("ix_tasks_deadline", "deadline"),
        Index("ix_tasks_external_id", "external_id"),
        Index("ix_tasks_status", "task_status"),
        Index("ix_tasks_priority", "priority"),
    )

    def __repr__(self):
        return (
            f"<Task(id={self.id}, title='{self.title}', status={self.status}, "
            f"project_id={self.project_id}, priority={self.priority}, "
            f"deadline={self.deadline}, assignees={self.assignees})>"
        )

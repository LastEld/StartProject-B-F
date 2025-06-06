#app/models/devlog.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Index, func
)
from sqlalchemy.orm import relationship
from app.models.base import Base

class DevLogEntry(Base):
    """
    DevLogEntry — запись в журнале разработки (devlog).
    Связывает любые текстовые, action или AI-события с проектом/таском.
    """
    __tablename__ = "devlog_entries"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    project_id: int = Column(Integer, ForeignKey("projects.id", ondelete='CASCADE'), nullable=True, index=True)
    task_id: int = Column(Integer, ForeignKey("tasks.id", ondelete='CASCADE'), nullable=True, index=True)

    entry_type: str = Column(String(24), nullable=False, default="note", doc="Тип записи: note, action, decision, meeting")
    content: str = Column(String(5000), nullable=False)
    author_id: int = Column(Integer, ForeignKey("users.id", name="fk_devlog_author_id_users"), nullable=False, index=True)
    tags: list = Column(JSON, nullable=False, default=lambda: [], doc="Теги записи")
    custom_fields: dict = Column(JSON, nullable=False, default=lambda: {}, doc="Кастомные поля")
    edit_reason: str = Column(String(256), nullable=True, doc="Причина редактирования")
    attachments: list = Column(JSON, nullable=False, default=lambda: [], doc="Ссылки на вложения")
    ai_notes: str = Column(String(2000), nullable=True, doc="AI-заметки по записи")

    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_deleted: bool = Column(Boolean, default=False, nullable=False, doc="Флаг soft-delete")
    deleted_at: datetime = Column(DateTime(timezone=True), nullable=True, doc="Дата удаления")

    # ORM-связи
    project = relationship("Project", backref="devlog_entries")
    task = relationship("Task", backref="devlog_entries")
    author = relationship("User", backref="devlog_entries")

    __table_args__ = (
        Index("ix_devlog_entries_created_at", "created_at"),
        Index("ix_devlog_entries_project_id_created_at", "project_id", "created_at"),
    )

    def __repr__(self):
        return (
            f"<DevLogEntry(id={self.id}, type={self.entry_type}, "
            f"project_id={self.project_id}, task_id={self.task_id}, "
            f"author_id='{self.author_id}')>"
        )

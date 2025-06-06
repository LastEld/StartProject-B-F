#app/models/ai_context.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, JSON, Boolean, func, Index
)
from app.models.base import Base

class AIContext(Base):
    """
    AIContext — универсальное хранилище контекста для любых сущностей проекта.
    Позволяет связывать дополнительные AI-данные (промпты, анализ, генерации и т.д.)
    с любым объектом (проект, задача, devlog, user и т.д.).
    """
    __tablename__ = "ai_contexts"

    id: int = Column(Integer, primary_key=True, autoincrement=True, index=True)
    object_type: str = Column(String(32), nullable=False, index=True, doc="Тип сущности ('project', 'task', 'devlog', ...')")
    object_id: int = Column(Integer, nullable=False, index=True, doc="ID связанной сущности")
    context_data: dict = Column(JSON, nullable=False, doc="AI-контекст в JSON-формате")
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by: str = Column(String(128), nullable=True, doc="Генератор (user/system/AI)")
    request_id: str = Column(String(64), nullable=True, doc="ID запроса для трекинга")
    notes: str = Column(String(512), nullable=True, doc="Дополнительные заметки")
    is_deleted: bool = Column(Boolean, default=False, nullable=False, doc="Флаг soft-delete")
    deleted_at: datetime = Column(DateTime(timezone=True), nullable=True, doc="Дата soft-delete")

    __table_args__ = (
        # Ускоряем выборки по object_type/object_id
        Index("ix_ai_context_object", "object_type", "object_id"),
        # (опционально) Ограничиваем уникальность одной пары
        # UniqueConstraint("object_type", "object_id", name="uq_ai_context_object"),
    )

    def __repr__(self):
        return (
            f"<AIContext(id={self.id}, object_type='{self.object_type}', object_id={self.object_id})>"
        )

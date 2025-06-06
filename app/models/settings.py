#app/models/settings.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, JSON, Boolean, ForeignKey, func
)
from app.models.base import Base

class Setting(Base):
    """
    Setting — системная или пользовательская настройка (глобальные и user-specific параметры, произвольный JSON).
    """
    __tablename__ = "settings"

    id: int = Column(Integer, primary_key=True, index=True)
    key: str = Column(String(128), unique=True, nullable=False, index=True, doc="Ключ настройки ('theme', 'ai.max_tokens', ...)")
    value: dict = Column(JSON, nullable=False, default=lambda: {}, doc="Значение (произвольная структура)")
    description: str = Column(String(512), nullable=True, doc="Описание настройки")
    user_id: int = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=True, doc="ID пользователя (NULL=глобальная настройка)")
    is_active: bool = Column(Boolean, default=True, nullable=False, doc="Включена ли настройка")
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, doc="Дата создания")
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, doc="Дата изменения")

    def __repr__(self):
        return f"<Setting(key='{self.key}', value={self.value}, user_id={self.user_id})>"

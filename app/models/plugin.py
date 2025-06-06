#app/models/plugin.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, JSON, DateTime, func, Index
)
import sqlalchemy as sa  # Для server_default=sa.false()
from app.models.base import Base

class Plugin(Base):
    """
    Plugin — расширяемый модуль системы. Хранит метаинформацию, конфиг, статусы, права доступа, soft-delete.
    """
    __tablename__ = "plugins"

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(100), unique=True, nullable=False, index=True, doc="Уникальное имя плагина")
    description: str = Column(String(500), nullable=True, doc="Описание")
    config_json: dict = Column(JSON, nullable=False, default=lambda: {}, doc="Конфигурация (любая структура)")
    is_active: bool = Column(Boolean, default=True, nullable=False, doc="Включен ли плагин")
    version: str = Column(String(32), nullable=True, doc="Версия")
    author: str = Column(String(128), nullable=True, doc="Автор/Email")
    subscription_level: str = Column(String(32), nullable=True, doc="Free/Pro/VIP")
    is_private: bool = Column(Boolean, default=False, server_default=sa.false(), nullable=False, doc="Приватный плагин")
    ui_component: str = Column(String(64), nullable=True, doc="Фронт-компонент")
    tags: list = Column(JSON, default=lambda: [], nullable=False, doc="Теги поиска/фильтрации")
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_deleted: bool = Column(Boolean, default=False, server_default=sa.false(), nullable=False, index=True, doc="Soft-delete")
    deleted_at: datetime = Column(DateTime(timezone=True), nullable=True, doc="Дата удаления")

    __table_args__ = (
        Index("ix_plugins_is_deleted_name", "name", "is_deleted"),
    )

    def __repr__(self):
        return (
            f"<Plugin(id={self.id}, name='{self.name}', version={self.version}, "
            f"active={self.is_active}, deleted={self.is_deleted})>"
        )

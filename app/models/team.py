#app\models\team.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Boolean
from app.models.base import Base

class Team(Base):
    """
    Team — команда пользователей. Поддерживает soft-delete, owner, описание.
    """
    __tablename__ = "teams"

    id: int = Column(Integer, primary_key=True)
    name: str = Column(String(128), nullable=False, unique=True, index=True, doc="Название команды")
    description: str = Column(String(255), nullable=True, doc="Описание")
    owner_id: int = Column(Integer, ForeignKey("users.id", ondelete='SET NULL'), nullable=True, index=True, doc="ID владельца")
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, doc="Дата создания")
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, doc="Дата обновления")
    is_deleted: bool = Column(Boolean, default=False, nullable=False, doc="Soft-delete")
    deleted_at: datetime = Column(DateTime(timezone=True), nullable=True, doc="Дата soft-delete")

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}')>"

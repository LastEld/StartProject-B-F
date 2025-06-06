#app/models/user.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, JSON, func
)
from sqlalchemy.orm import relationship
from app.models.base import Base

class User(Base):
    """
    User — аккаунт пользователя, поддерживает    роли, аватар, soft-активацию, last_login, расширяемость.
    """
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True)
    username: str = Column(String(50), unique=True, nullable=False, index=True, doc="Уникальный username")
    email: str = Column(String(255), unique=True, nullable=False, index=True, doc="Email")
    full_name: str = Column(String(128), nullable=True, doc="Полное имя")
    password_hash: str = Column(String(128), nullable=False, doc="Хэш пароля (никогда не хранить сырой пароль!)")
    is_active: bool = Column(Boolean, default=True, nullable=False, doc="Аккаунт активен")
    is_superuser: bool = Column(Boolean, default=False, nullable=False, doc="Является ли суперюзером")
    roles: list = Column(JSON, default=lambda: [], nullable=False, doc="Список ролей (['developer', 'manager', ...])")
    avatar_url: str = Column(String(255), nullable=True, doc="URL аватара пользователя")
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, doc="Дата создания")
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, doc="Дата обновления")
    last_login_at: datetime = Column(DateTime(timezone=True), nullable=True, doc="Последний вход")

    # --- Связи ---
    teams = relationship("Team", backref="users", lazy="dynamic")
    settings = relationship("Setting", backref="user", lazy="dynamic")
    access_tokens = relationship(
    "AccessToken",
    back_populates="user",
    cascade="all, delete-orphan"
)
    def __repr__(self):
        return (
            f"<User(id={self.id}, username='{self.username}', email='{self.email}', roles={self.roles})>"
        )

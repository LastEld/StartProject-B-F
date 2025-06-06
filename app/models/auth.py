#app/models/auth.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.models.base import Base

class AccessToken(Base):
    """
    AccessToken — хранит данные access и refresh токенов для трекинга/отзыва/аудита.
    """
    __tablename__ = "access_tokens"

    id: int = Column(Integer, primary_key=True, index=True)
    user_id: int = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=False, index=True, doc="ID пользователя")
    token: str = Column(String(512), unique=True, nullable=False, index=True, doc="Строка токена (access или refresh)")
    jti: str = Column(String(255), unique=True, index=True, nullable=True, doc="JTI для refresh токенов")
    token_type: str = Column(String(50), nullable=True, doc="'access' или 'refresh'")
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, doc="Время создания")
    expires_at: datetime = Column(DateTime(timezone=True), nullable=True, doc="Время истечения токена")
    user_agent: str = Column(String(256), nullable=True, doc="User-Agent клиента")
    ip_address: str = Column(String(64), nullable=True, doc="IP-адрес клиента")
    is_active: bool = Column(Boolean, default=True, nullable=False, doc="Токен активен")
    revoked: bool = Column(Boolean, default=False, nullable=False, doc="Токен отозван")

    user = relationship("User", back_populates="access_tokens")

    def __repr__(self):
        return (
            f"<AccessToken(id={self.id}, user_id={self.user_id}, "
            f"type={self.token_type}, is_active={self.is_active}, revoked={self.revoked})>"
        )

    @property
    def is_expired(self) -> bool:
        """Проверяет, истёк ли токен."""
        return self.expires_at is not None and datetime.utcnow() > self.expires_at

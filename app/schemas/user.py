#app/schemas/user.py
from pydantic import BaseModel, Field, EmailStr, constr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    """
    UserBase — базовая схема пользователя (используется для create/read).
    """
    username: constr(min_length=3, max_length=50) = Field(..., example="john_doe", description="Уникальный username")
    email: EmailStr = Field(..., example="john.doe@example.com", description="Email пользователя")
    full_name: Optional[str] = Field(None, example="John Doe", description="Полное имя")
    is_active: bool = Field(True, description="Пользователь активен")
    is_superuser: bool = Field(False, description="Является суперюзером (админ)")
    roles: List[str] = Field(default_factory=list, example=["developer", "manager"], description="Роли пользователя")

class UserCreate(UserBase):
    """
    UserCreate — создание пользователя (пароль обязателен).
    """
    password: constr(min_length=8) = Field(..., example="StrongPassw0rd!", description="Пароль пользователя")

class UserUpdate(BaseModel):
    """
    UserUpdate — обновление пользователя (все поля опциональны).
    """
    email: Optional[EmailStr] = Field(None, description="Email")
    full_name: Optional[str] = Field(None, description="Полное имя")
    is_active: Optional[bool] = Field(None, description="Пользователь активен")
    is_superuser: Optional[bool] = Field(None, description="Является суперюзером (только для админов!)")
    roles: Optional[List[str]] = Field(None, description="Роли пользователя")
    password: Optional[constr(min_length=8)] = Field(None, description="Пароль (обновляется с хешированием)")

class UserRead(UserBase):
    """
    UserRead — схема для выдачи пользователя (response).
    """
    id: int
    created_at: datetime
    updated_at: datetime
    avatar_url: Optional[str] = Field(None, example="https://cdn.example.com/avatars/john.jpg", description="URL аватара")

    class Config:
        orm_mode = True

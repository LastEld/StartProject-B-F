#app/schemas/template.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from .user import UserRead

class TemplateBase(BaseModel):
    """
    TemplateBase — базовая схема шаблона проекта/тасков/структуры.
    """
    name: str = Field(..., example="Freelancer Project Template", description="Название шаблона")
    description: Optional[str] = Field(None, example="A template suited for freelance projects", description="Описание шаблона")
    version: Optional[str] = Field("1.0.0", example="1.0.0", description="Версия шаблона (semver)")
    created_at: Optional[datetime] = Field(None, example="2024-05-29T12:00:00Z", description="Дата создания")
    updated_at: Optional[datetime] = Field(None, example="2024-05-29T12:00:00Z", description="Дата изменения")
    is_active: Optional[bool] = Field(True, description="Доступен ли шаблон для использования")
    tags: List[str] = Field(default_factory=list, example=["freelance", "simple", "startup"], description="Теги шаблона")
    structure: Dict[str, Any] = Field(..., description="Основная структура шаблона (json: плагины, задачи, настройки и т.д.)")
    ai_notes: Optional[str] = Field(None, example="This template works best for small teams.", description="AI-комментарии")
    subscription_level: Optional[str] = Field(None, example="Pro", description="Подписка: Free, Pro, VIP")
    is_private: Optional[bool] = Field(False, description="Приватный шаблон (только для автора/суперюзеров)")
    is_deleted: bool = Field(False, description="Soft-delete")
    deleted_at: Optional[datetime] = Field(None, description="Дата soft-delete")

    @validator('version', pre=True, always=True)
    def version_must_be_semver(cls, v):
        if v is None:
            return "1.0.0"
        import re
        semver_regex = r'^\d+\.\d+\.\d+(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$'
        if not re.match(semver_regex, v):
            raise ValueError('Version must follow semantic versioning (e.g., 1.0.0, 1.0.0-alpha, 1.0.0+build)')
        return v

class TemplateCreate(BaseModel):
    """
    TemplateCreate — схема создания шаблона (author_id, is_deleted, deleted_at выставляются системой).
    """
    name: str = Field(..., example="Freelancer Project Template")
    description: Optional[str] = Field(None, example="A template suited for freelance projects")
    version: Optional[str] = Field("1.0.0", example="1.0.0")
    is_active: Optional[bool] = Field(True)
    tags: List[str] = Field(default_factory=list)
    structure: Dict[str, Any] = Field(..., description="Основная структура шаблона")
    ai_notes: Optional[str] = None
    subscription_level: Optional[str] = None
    is_private: Optional[bool] = Field(False)

    @validator('version', pre=True, always=True)
    def create_version_must_be_semver(cls, v):
        if v is None: return "1.0.0"
        import re
        semver_regex = r'^\d+\.\d+\.\d+(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$'
        if not re.match(semver_regex, v):
            raise ValueError('Version must follow semantic versioning')
        return v

class TemplateUpdate(BaseModel):
    """
    TemplateUpdate — обновление шаблона (все поля опциональны).
    """
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None
    structure: Optional[Dict[str, Any]] = None
    ai_notes: Optional[str] = None
    subscription_level: Optional[str] = None
    is_private: Optional[bool] = None

    @validator('version')
    def update_version_must_be_semver(cls, v):
        if v is not None:
            import re
            semver_regex = r'^\d+\.\d+\.\d+(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$'
            if not re.match(semver_regex, v):
                raise ValueError('Version must follow semantic versioning')
        return v

class TemplateShort(BaseModel):
    """
    TemplateShort — сокращённая схема для списка шаблонов.
    """
    id: int
    name: str
    is_active: bool
    is_private: bool
    author_id: int
    author: Optional[UserRead] = None
    is_deleted: bool = Field(False)

    class Config:
        orm_mode = True

class TemplateRead(TemplateBase):
    """
    TemplateRead — полная схема шаблона для response.
    """
    id: int
    author_id: int
    author: Optional[UserRead] = None

    class Config:
        orm_mode = True

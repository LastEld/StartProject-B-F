#app/schemas/team.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TeamBase(BaseModel):
    """
    TeamBase — базовая схема для команды.
    """
    name: str = Field(..., example="Dev Team", description="Название команды")
    description: Optional[str] = Field("", example="Development department", description="Описание команды")

class TeamCreate(TeamBase):
    """
    TeamCreate — создание новой команды.
    """
    pass

class TeamUpdate(BaseModel):
    """
    TeamUpdate — обновление данных команды (все поля опциональны).
    """
    name: Optional[str] = None
    description: Optional[str] = None

class TeamRead(TeamBase):
    """
    TeamRead — схема для выдачи команды (response).
    """
    id: int
    owner_id: Optional[int] = Field(None, description="ID владельца (user)")
    created_at: Optional[datetime] = Field(None, description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата обновления")
    is_deleted: Optional[bool] = Field(False, description="Soft-delete флаг")

    class Config:
        orm_mode = True

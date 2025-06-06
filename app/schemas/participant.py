#app/schemas/participant.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Participant(BaseModel):
    """
    Participant — участник проекта или задачи (может быть как человек, так и команда).
    """
    name: str = Field(..., example="Jane Smith", description="Имя участника")
    email: Optional[str] = Field(None, example="jane@company.com", description="Email участника")
    role: Optional[str] = Field(None, example="manager", description="Роль (manager, dev, reviewer и т.д.)")
    avatar_url: Optional[str] = Field(None, example="https://cdn.example.com/avatars/jane.jpg", description="Ссылка на аватар")
    is_team: Optional[bool] = Field(False, description="Участник — это команда?")
    is_active: Optional[bool] = Field(True, description="Активен ли участник")
    joined_at: Optional[datetime] = Field(None, example="2024-05-20T10:00:00Z", description="Дата присоединения")

    class Config:
        orm_mode = True

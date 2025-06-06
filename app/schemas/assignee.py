#app/schemas/assignee.py
from pydantic import BaseModel, Field
from typing import Optional

class Assignee(BaseModel):
    """
    Assignee — назначенный исполнитель/участник задачи или проекта.
    """
    user_id: Optional[int] = Field(None, example=17, description="ID пользователя")
    name: str = Field(..., example="John Doe", description="Имя участника")
    email: Optional[str] = Field(None, example="john@company.com", description="Email участника")
    role: Optional[str] = Field(None, example="developer", description="Роль (developer, manager, reviewer и т.д.)")
    avatar_url: Optional[str] = Field(None, example="https://example.com/avatar.jpg", description="URL аватара")
    is_active: Optional[bool] = Field(True, description="Активен ли пользователь (для фильтрации, AI)")

    class Config:
        orm_mode = True

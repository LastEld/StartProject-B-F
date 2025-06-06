#app/schemas/ai_context.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProjectAIContext(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[int] = None
    participants: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    linked_repo: Optional[str] = None
    parent_project_id: Optional[int] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    is_overdue: Optional[bool] = None
    is_deleted: Optional[bool] = None
    ai_notes: Optional[str] = None
    external_id: Optional[str] = None
    subscription_level: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class TaskAIContext(BaseModel):
    id: int
    project_id: int
    parent_task_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    deadline: Optional[str] = None
    assignees: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_overdue: Optional[bool] = None
    is_deleted: Optional[bool] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    is_favorite: Optional[bool] = None
    ai_notes: Optional[str] = None
    external_id: Optional[str] = None
    reviewed: Optional[bool] = None

class DevLogAIContext(BaseModel):
    id: int
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    entry_type: str
    content: str
    author: str
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    is_deleted: Optional[bool] = None
    edit_reason: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    ai_notes: Optional[str] = None

class UserAIContext(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    is_superuser: Optional[bool] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None
    avatar_url: Optional[str] = None

class PluginAIContext(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    config_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: Optional[bool] = None
    version: Optional[str] = None
    author: Optional[str] = None
    subscription_level: Optional[str] = None
    is_private: Optional[bool] = None
    ui_component: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

# --- AIContext CRUD schemas ---

class AIContextBase(BaseModel):
    object_type: str
    object_id: int
    context_data: Dict[str, Any]
    created_by: Optional[str] = None
    request_id: Optional[str] = None
    notes: Optional[str] = None

class AIContextCreate(AIContextBase):
    pass

class AIContextUpdate(BaseModel):
    object_type: Optional[str] = None
    object_id: Optional[int] = None
    context_data: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None
    request_id: Optional[str] = None
    notes: Optional[str] = None
    is_deleted: Optional[bool] = None

class AIContextRead(AIContextBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        orm_mode = True

#app/schemas/attachment.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Attachment(BaseModel):
    """
    Attachment — файл или вложение для задачи/проекта/записи.
    """
    url: str = Field(..., example="https://cdn.example.com/files/doc1.pdf", description="Ссылка на файл/вложение")
    type: Optional[str] = Field(None, example="pdf", description="Тип файла (pdf, image/png, screenshot, txt и т.д.)")
    name: Optional[str] = Field(None, example="Project Spec", description="Имя файла/вложения")
    size: Optional[int] = Field(None, example=102400, description="Размер файла в байтах")
    uploaded_by: Optional[str] = Field(None, example="john@company.com", description="Кто загрузил файл")
    uploaded_at: Optional[datetime] = Field(None, example="2024-05-29T15:20:00Z", description="Дата/время загрузки")
    description: Optional[str] = Field(None, example="Документация к проекту", description="Описание файла")
    preview_url: Optional[str] = Field(None, example="https://cdn.example.com/previews/doc1.png", description="Ссылка на превью/миниатюру")
    # Можно добавить thumbnail_url, external_id, checksum и т.д.

    class Config:
        orm_mode = True

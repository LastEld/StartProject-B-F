#app/schemas/response.py
from pydantic import BaseModel, Field
from typing import Any, Optional

class ErrorDetail(BaseModel):
    """
    ErrorDetail — детальное описание ошибки (код, сообщение, детали).
    """
    code: str = Field(..., example="validation_error", description="Код ошибки (machine-readable)")
    message: str = Field(..., example="Field X is required.", description="Сообщение об ошибке")
    details: Optional[Any] = Field(None, example={"field": "username"}, description="Дополнительные детали")

class ErrorResponse(BaseModel):
    """
    ErrorResponse — стандартная структура для ошибки.
    """
    error: ErrorDetail

class SuccessResponse(BaseModel):
    """
    SuccessResponse — универсальный ответ с результатом выполнения операции.
    """
    result: Any = Field(..., description="Результат запроса (может быть любым объектом)")
    detail: Optional[str] = Field(None, example="Operation successful", description="Дополнительная информация")

class ListResponse(BaseModel):
    """
    ListResponse — универсальный ответ для списков (пагинация).
    """
    results: Any = Field(..., description="Список результатов (обычно List[SomeSchema])")
    total_count: Optional[int] = Field(None, description="Общее количество результатов (для пагинации)")
    detail: Optional[str] = Field(None, description="Дополнительная информация")

class SimpleMessage(BaseModel):
    """
    SimpleMessage — простое сообщение для подтверждения действия.
    """
    message: str = Field(..., example="Action completed successfully", description="Текстовое сообщение")

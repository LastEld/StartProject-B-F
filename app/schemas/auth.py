#app/schemas/auth.py
from pydantic import BaseModel, Field
from typing import Optional

class Token(BaseModel):
    """
    Token — базовая схема access-токена для авторизации.
    """
    access_token: str = Field(..., example="eyJhbGciOi...", description="JWT access token")
    token_type: str = Field("bearer", example="bearer", description="Тип токена (обычно bearer)")
    expires_in: Optional[int] = Field(None, description="Время жизни токена (секунды)", example=3600)

class TokenPayload(BaseModel):
    """
    TokenPayload — полезная нагрузка access/refresh токена (JWT claims).
    """
    sub: Optional[str] = Field(None, description="User identifier (обычно user_id)", example="1")
    exp: Optional[int] = Field(None, description="Expiration UNIX timestamp", example=1717000000)

class LoginRequest(BaseModel):
    """
    LoginRequest — тело запроса для входа (логин).
    """
    username: str = Field(..., example="john_doe", description="Имя пользователя")
    password: str = Field(..., example="StrongPassw0rd!", description="Пароль")

class LoginResponse(BaseModel):
    """
    LoginResponse — ответ на успешный логин (access + refresh).
    """
    access_token: str = Field(..., example="eyJhbGciOi...", description="JWT access token")
    token_type: str = Field("bearer", example="bearer", description="Тип токена")
    expires_in: int = Field(..., description="Время жизни access токена (секунды)", example=3600)
    refresh_token: Optional[str] = Field(None, example="eyJ0eXAiOiJKV...", description="JWT refresh token")

class TokenRefreshRequest(BaseModel):
    """
    TokenRefreshRequest — тело запроса для обновления токена.
    """
    refresh_token: str = Field(..., example="eyJ0eXAiOiJKV...", description="JWT refresh token")

class TokenRefreshResponse(BaseModel):
    """
    TokenRefreshResponse — ответ на обновление (access + refresh токены, с ротацией).
    """
    access_token: str = Field(..., example="eyJhbGciOi...", description="JWT access token")
    token_type: str = Field("bearer", example="bearer", description="Тип токена")
    expires_in: int = Field(..., description="Время жизни access токена (секунды)", example=3600)
    refresh_token: str = Field(..., example="eyJ0eXAiOiJKV...", description="JWT refresh token")

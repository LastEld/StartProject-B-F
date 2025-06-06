#app/core/settings.py
# app/core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pydantic import field_validator

class Settings(BaseSettings):
    """
    Основные переменные окружения и настройки приложения.
    Все значения берутся из .env.
    """
    # Database
    DATABASE_URL: str

    # JWT / Security
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # First Superuser (можно через env)
    FIRST_SUPERUSER_USERNAME: str
    FIRST_SUPERUSER_EMAIL: str
    FIRST_SUPERUSER_PASSWORD: str

    # App meta
    ENV: str = "development"
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Авто-сплит строкового списка ALLOWED_ORIGINS из .env
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Можно добавлять новые параметры здесь:
    # SMTP_HOST: Optional[str] = None
    # STRIPE_API_KEY: Optional[str] = None
    # OPENAI_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()

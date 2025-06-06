# app/database.py
# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.core.settings import settings

# Для alembic миграций импортируй settings.DATABASE_URL только в run_migrations_online (если alembic >= 1.5)
# Здесь — для обычного использования

# Создаем движок подключения к БД
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,  # Включает SQLAlchemy 2.0 API, если совместимо
)

# Создаем фабрику сессий (scoped_session для потокобезопасности)
SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,  # Рекомендация для современных FastAPI приложений
    )
)

# Dependency для FastAPI (можно использовать так)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#app/models/base.py
"""
Базовый класс для всех ORM-моделей проекта.

Использовать как Base при описании моделей:
    from app.models.base import Base
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

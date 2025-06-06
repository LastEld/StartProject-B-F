# app/dependencies.py
# app/dependencies.py

from typing import Generator, AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.core.security import SECRET_KEY, ALGORITHM, oauth2_scheme
from app.core.settings import settings
from app.models.user import User
from app.database import SessionLocal
from app.crud.user import get_user_by_username, get_user as get_user_crud

def get_db() -> Generator[Session, None, None]:
    """
    Создает и возвращает сессию базы данных, гарантирует закрытие после использования.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Декодирует JWT-токен, получает пользователя из базы, если токен валиден.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Проверяет, что пользователь активен.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user

# Project dependencies
from app.models.project import Project as ProjectModel
from app.crud.project import get_project as get_project_crud
from app.core.exceptions import ProjectNotFound

async def get_project_for_user_or_404_403(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> ProjectModel:
    """
    Получить проект, если пользователь авторизован, иначе выдать 404/403.
    """
    try:
        project = get_project_crud(db, project_id)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not current_user.is_superuser and project.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project"
        )
    return project

async def get_deleted_project_for_user_or_404_403(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> ProjectModel:
    """
    Получить проект (в том числе архивный), если пользователь авторизован, иначе выдать 404/403.
    """
    try:
        project = get_project_crud(db, project_id, include_deleted=True)
    except ProjectNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not current_user.is_superuser and project.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project"
        )
    return project

async def get_target_user_or_404_403(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Получить пользователя (по id), если текущий пользователь — сам себя или суперюзер,
    иначе 404/403.
    """
    target_user = get_user_crud(db, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not current_user.is_superuser and target_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's information"
        )
    return target_user

#app/crud/user.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.core.exceptions import ProjectValidationError
from typing import List, Optional, Dict, Any
from passlib.context import CryptContext
import logging
from datetime import datetime, timezone

logger = logging.getLogger("DevOS.Users")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_user(db: Session, data: dict) -> User:
    """
    Создать нового пользователя (username/email уникальны).
    """
    if db.query(User).filter((User.username == data["username"]) | (User.email == data["email"])).first():
        raise ProjectValidationError("User with this username or email already exists.")

    password_hash = get_password_hash(data["password"])
    user = User(
        username=data["username"].strip(),
        email=data["email"].strip(),
        full_name=data.get("full_name"),
        password_hash=password_hash,
        is_active=data.get("is_active", True),
        is_superuser=data.get("is_superuser", False),
        roles=data.get("roles", []),
        avatar_url=data.get("avatar_url"),
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        logger.info(f"Created user {user.username}")
        return user
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating user: {e}")
        raise ProjectValidationError("User with this username or email already exists.")
    except Exception as e:
        db.rollback()
        logger.error(f"DB error creating user: {e}")
        raise ProjectValidationError("Database error while creating user.")

def get_user(db: Session, user_id: int) -> Optional[User]:
    """
    Получить пользователя по ID.
    """
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Получить пользователя по username.
    """
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Получить пользователя по email.
    """
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Аутентифицировать пользователя по username и паролю.
    """
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user

def update_user(db: Session, user_id: int, data: dict) -> User:
    """
    Обновить профиль пользователя.
    """
    user = get_user(db, user_id)
    if not user:
        raise ProjectValidationError("User not found.")
    for field in ["email", "full_name", "is_active", "is_superuser", "roles", "avatar_url"]:
        if field in data:
            setattr(user, field, data[field])
    if "password" in data and data["password"]:
        user.password_hash = get_password_hash(data["password"])
    user.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(user)
        logger.info(f"Updated user {user.username}")
        return user
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user: {e}")
        raise ProjectValidationError("Database error while updating user.")

def get_users(db: Session, filters: Dict[str, Any] = None) -> List[User]:
    """
    Получить список пользователей с фильтрами.
    """
    filters = filters or {}
    query = db.query(User)
    if "is_active" in filters:
        query = query.filter(User.is_active == filters["is_active"])
    if "role" in filters:
        query = query.filter(User.roles.contains([filters["role"]]))
    if "search" in filters:
        value = f"%{filters['search']}%"
        query = query.filter((User.username.ilike(value)) | (User.full_name.ilike(value)))
    return query.order_by(User.created_at.desc()).all()

def set_last_login(db: Session, user_id: int) -> None:
    """
    Обновить поле последнего входа пользователя.
    """
    user = get_user(db, user_id)
    if user:
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()

def soft_delete_user(db: Session, user_id: int) -> bool:
    """
    Деактивировать пользователя (soft delete, user остаётся в базе).
    """
    user = get_user(db, user_id)
    if not user:
        raise ProjectValidationError("User not found.")
    user.is_active = False
    try:
        db.commit()
        logger.info(f"Soft-deleted user {user.username}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to deactivate user {user.username}: {e}")
        raise ProjectValidationError("Database error while deactivating user.")


def update_password_for_reset(db: Session, user: User, new_password: str) -> bool:
    """
    Updates the user's password after a successful password reset.
    Also clears the password reset token fields.
    """
    if not user:
        raise ProjectValidationError("User not found.")

    user.password_hash = get_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_token_expires_at = None
    user.updated_at = datetime.now(timezone.utc)

    try:
        db.add(user) # Add user to session if it's not already there or has been detached
        db.commit()
        db.refresh(user)
        logger.info(f"Password updated successfully for user {user.username} after reset.")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating password for user {user.username} after reset: {e}")
        raise ProjectValidationError("Database error while updating password.")

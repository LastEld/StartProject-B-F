#app/core/security.py
# app/core/security.py

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
from jose import JWTError, jwt
from app.core.settings import settings
from sqlalchemy.orm import Session
from app.models.user import User

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Настройки
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> tuple[str, datetime]:
    """
    Генерирует access token (JWT) и возвращает (token, expire_time)
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire

def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> tuple[str, datetime, str]:
    """
    Генерирует refresh token (JWT) с уникальным jti и возвращает (token, expire_time, jti)
    """
    to_encode = data.copy()
    jti = uuid.uuid4().hex
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire, jti

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Декодирует и валидирует access token.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None

def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Декодирует и валидирует refresh token.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None

# FastAPI OAuth2 scheme (используется в Depends)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# === OPTIONAL ===
# Пример функции для получения пользователя по токену (если не реализовано отдельно)
# from app.dependencies import get_db
# def get_current_user_from_token(
#     token: str = Depends(oauth2_scheme),
#     db: Session = Depends(get_db)
# ) -> User:
#     payload = verify_access_token(token)
#     if payload is None or "user_id" not in payload:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Could not validate credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     user = db.query(User).filter(User.id == payload["user_id"]).first()
#     if user is None or not user.is_active:
#         raise HTTPException(status_code=401, detail="User not found or inactive")
#     return user


#app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    PasswordResetRequest,
    PasswordReset
)
from app.schemas.user import UserRead
from app.schemas.response import MessageResponse # For simple message responses
from app.crud.user import (
    authenticate_user,
    get_user_by_username,
    set_last_login,
    update_password_for_reset, # Import the new function
)
from app.crud import auth as crud_auth
from app.crud.auth import ( # Import specific functions for password reset
    get_user_by_email,
    create_password_reset_token,
    get_user_by_password_reset_token
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token
)
from app.dependencies import get_db, get_current_active_user
from app.core.settings import settings
from datetime import timedelta, timezone, datetime
import logging

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger("DevOS.Auth")

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Логин по username/email + password.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    access_token_str, access_token_expires_at = create_access_token(
        data={"sub": user.username, "user_id": user.id, "roles": user.roles},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    refresh_token_expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token_expires_at = datetime.now(timezone.utc) + refresh_token_expires_delta
    refresh_token_str, _, refresh_jti = create_refresh_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=refresh_token_expires_delta
    )

    # Store token info (access/refresh)
    try:
        crud_auth.store_token_info(
            db=db,
            user_id=user.id,
            token=access_token_str,
            token_type='access',
            expires_at=access_token_expires_at,
        )
        crud_auth.store_token_info(
            db=db,
            user_id=user.id,
            token=refresh_token_str,
            token_type='refresh',
            jti=refresh_jti,
            expires_at=refresh_token_expires_at,
        )
    except Exception as e:
        logger.error(f"Failed to store token info for user {user.id}: {e}")

    set_last_login(db, user.id)
    return LoginResponse(
        access_token=access_token_str,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token_str
    )

@router.post("/refresh", response_model=TokenRefreshResponse, status_code=status.HTTP_200_OK)
def refresh_token(
    data: TokenRefreshRequest,
    db: Session = Depends(get_db),
):
    """
    Обновить (ротация) access/refresh токенов по refresh_token.
    """
    payload = verify_refresh_token(data.refresh_token)
    if not payload or "user_id" not in payload or "jti" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token payload")

    token_jti = payload["jti"]
    if not crud_auth.is_refresh_token_active(db, token_jti=token_jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or invalid")

    user = get_user_by_username(db, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # Ревокация старого refresh токена (ротация)
    crud_auth.revoke_refresh_token(db, token_jti=token_jti)

    user_id_from_payload = payload["user_id"]
    new_access_token_str, new_access_token_expires_at = create_access_token(
        data={"sub": user.username, "user_id": user_id_from_payload, "roles": user.roles},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    try:
        crud_auth.store_token_info(
            db=db,
            user_id=user_id_from_payload,
            token=new_access_token_str,
            token_type='access',
            expires_at=new_access_token_expires_at
        )
    except Exception as e:
        logger.error(f"Failed to store new access token during refresh for user {user_id_from_payload}: {e}")

    new_refresh_token_expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token_expires_at = datetime.now(timezone.utc) + new_refresh_token_expires_delta
    new_refresh_token_str, _, new_refresh_jti = create_refresh_token(
        data={"sub": user.username, "user_id": user_id_from_payload},
        expires_delta=new_refresh_token_expires_delta
    )
    try:
        crud_auth.store_token_info(
            db=db,
            user_id=user_id_from_payload,
            token=new_refresh_token_str,
            token_type='refresh',
            jti=new_refresh_jti,
            expires_at=new_refresh_token_expires_at
        )
    except Exception as e:
        logger.error(f"Failed to store new refresh token during refresh for user {user_id_from_payload}: {e}")

    return TokenRefreshResponse(
        access_token=new_access_token_str,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=new_refresh_token_str
    )

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    data: TokenRefreshRequest,
    db: Session = Depends(get_db),
):
    """
    Logout и revoke refresh token (по refresh_token).
    """
    payload = verify_refresh_token(data.refresh_token)
    if not payload or "jti" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token for logout",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jti = payload["jti"]
    crud_auth.revoke_refresh_token(db, token_jti=jti)
    return {"message": "Logout successful (token already invalid or not found)."}

@router.get("/me", response_model=UserRead)
def get_me(current_user=Depends(get_current_active_user)):
    """
    Получить данные текущего пользователя.
    """
    return current_user

@router.post("/logout_all", status_code=status.HTTP_200_OK)
def logout_all(
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user)
):
    """
    Logout со всех устройств (ревок всех токенов пользователя).
    """
    count = crud_auth.revoke_all_tokens_for_user(db, user_id=user.id)
    return {"message": f"Logged out from {count} sessions."}


# --- Password Reset Endpoints ---

@router.post("/password-reset/request", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def request_password_reset(
    data: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """
    Запрос на сброс пароля. Пользователь предоставляет email.
    """
    user = get_user_by_email(db, email=data.email)
    if not user:
        # Не раскрываем, существует ли email, из соображений безопасности
        logger.info(f"Password reset requested for non-existent email: {data.email}")
        return MessageResponse(message="If an account with this email exists, a password reset link has been sent.")

    token = create_password_reset_token(db, user=user)

    # В реальном приложении здесь будет отправка email
    logger.info(f"Password reset token generated for user {user.email}: {token}")
    # Для целей этого задания, мы не отправляем email, а просто логируем токен.
    # В реальном приложении: send_password_reset_email(user.email, token)

    return MessageResponse(message="If an account with this email exists, a password reset link has been sent.")

@router.post("/password-reset/reset", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def reset_password(
    data: PasswordReset,
    db: Session = Depends(get_db),
):
    """
    Сброс пароля с использованием токена.
    """
    user = get_user_by_password_reset_token(db, token=data.token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive."
        )

    # Обновляем пароль и очищаем токен
    success = update_password_for_reset(db, user=user, new_password=data.new_password)
    if not success:
        # Это должно быть обработано внутри update_password_for_reset, но на всякий случай
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update password."
        )

    logger.info(f"Password has been reset for user {user.email}")
    return MessageResponse(message="Your password has been successfully reset.")

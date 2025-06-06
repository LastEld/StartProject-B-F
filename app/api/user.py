#app/api/user.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.user import UserCreate, UserUpdate, UserRead
from app.crud.user import (
    create_user,
    get_user,
    get_user_by_username,
    get_user_by_email,
    update_user,
    get_users,
    soft_delete_user,
)
from app.dependencies import get_db, get_current_active_user, get_target_user_or_404_403
from app.schemas.response import SuccessResponse
from app.models.user import User as DBUser
from app.core.exceptions import ProjectValidationError

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserRead)
def read_users_me(current_user: DBUser = Depends(get_current_active_user)):
    """
    Get current logged-in user profile.
    """
    return current_user

@router.post("/", response_model=UserRead)
def register_user(
    data: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new user.
    """
    try:
        user_obj = create_user(db, data.model_dump())
        return user_obj
    except ProjectValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during user registration.")

@router.get("/{user_id}", response_model=UserRead)
async def get_user_profile(
    target_user: DBUser = Depends(get_target_user_or_404_403)
):
    """
    Get user profile by ID (allowed self or admin).
    """
    return target_user

@router.get("/", response_model=List[UserRead])
def list_users(
    is_active: Optional[bool] = Query(None),
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Get list of users (admin only).
    Filter by active, role, search.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to list users")
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if role:
        filters["role"] = role
    if search:
        filters["search"] = search
    return get_users(db, filters=filters)

@router.patch("/{user_id}", response_model=UserRead)
async def patch_user(
    data: UserUpdate,
    target_user: DBUser = Depends(get_target_user_or_404_403),
    db: Session = Depends(get_db)
):
    """
    Update user info (self or admin).
    """
    try:
        user_obj = update_user(db, target_user.id, data.model_dump(exclude_unset=True))
        return user_obj
    except ProjectValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while updating user.")

@router.delete("/{user_id}", response_model=SuccessResponse)
async def deactivate_user(
    target_user: DBUser = Depends(get_target_user_or_404_403),
    db: Session = Depends(get_db)
):
    """
    Soft-delete/deactivate user (self or admin).
    """
    try:
        soft_delete_user(db, target_user.id)
        return SuccessResponse(result=target_user.id, detail="User deactivated")
    except ProjectValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while deactivating user.")

@router.get("/by-username/{username}", response_model=UserRead)
def get_by_username(
    username: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Get user by username (admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform this lookup")
    user_obj = get_user_by_username(db, username)
    if not user_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_obj

@router.get("/by-email/{email}", response_model=UserRead)
def get_by_email(
    email: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Get user by email (admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform this lookup")
    user_obj = get_user_by_email(db, email)
    if not user_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_obj

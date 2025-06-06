#app/api/team.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.team import TeamCreate, TeamRead, TeamUpdate
from app.crud.team import (
    create_team,
    get_team,
    get_all_teams,
    update_team,
    delete_team,
    restore_team,
    TeamError,
)
from app.dependencies import get_db, get_current_active_user
from app.schemas.response import SuccessResponse
from app.models.user import User as UserModel

router = APIRouter(prefix="/teams", tags=["Teams"])

@router.post("/", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team_api(
    data: TeamCreate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """
    Создать новую команду (автоматически владелец — текущий пользователь).
    """
    try:
        payload = data.dict()
        payload["owner_id"] = user.id
        team = create_team(db, payload)
        return team
    except TeamError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{team_id}", response_model=TeamRead)
def read_team(
    team_id: int,
    db: Session = Depends(get_db)
):
    """
    Получить команду по ID.
    """
    try:
        return get_team(db, team_id)
    except TeamError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[TeamRead])
def list_teams(
    include_deleted: bool = Query(False, description="Показать удаленные команды"),
    db: Session = Depends(get_db)
):
    """
    Список всех команд (по умолчанию только активные).
    """
    return get_all_teams(db, include_deleted=include_deleted)

@router.patch("/{team_id}", response_model=TeamRead)
def update_team_api(
    team_id: int,
    data: TeamUpdate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """
    Обновить команду.
    Только владелец или суперюзер может обновлять.
    """
    try:
        team = get_team(db, team_id)
        if not user.is_superuser and team.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions to update this team.")
        return update_team(db, team_id, data.dict(exclude_unset=True))
    except TeamError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{team_id}", response_model=SuccessResponse)
def soft_delete_team_api(
    team_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """
    Архивировать (soft-delete) команду.
    Только владелец или суперюзер может архивировать.
    """
    try:
        team = get_team(db, team_id)
        if not user.is_superuser and team.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions to archive this team.")
        delete_team(db, team_id, soft=True)
        return SuccessResponse(result=team_id, detail="Team archived")
    except TeamError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{team_id}/restore", response_model=SuccessResponse)
def restore_team_api(
    team_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """
    Восстановить архивированную команду.
    Только владелец или суперюзер может восстанавливать.
    """
    try:
        team = get_team(db, team_id)
        if not user.is_superuser and team.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions to restore this team.")
        restore_team(db, team_id)
        return SuccessResponse(result=team_id, detail="Team restored")
    except TeamError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{team_id}/hard", response_model=SuccessResponse)
def hard_delete_team_api(
    team_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user)
):
    """
    Полностью удалить команду (hard delete).
    Только владелец или суперюзер может удалять навсегда.
    """
    try:
        team = get_team(db, team_id)
        if not user.is_superuser and team.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions to hard-delete this team.")
        delete_team(db, team_id, soft=False)
        return SuccessResponse(result=team_id, detail="Team hard deleted")
    except TeamError as e:
        raise HTTPException(status_code=404, detail=str(e))

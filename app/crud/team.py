#app/crud/team.py
from sqlalchemy.orm import Session
from app.models.team import Team
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from typing import List, Optional
import logging

logger = logging.getLogger("DevOS.Team")

class TeamError(Exception):
    """Base exception for team CRUD errors."""
    pass

def create_team(db: Session, data: dict) -> Team:
    """
    Создать новую команду с уникальным именем.
    """
    name = data["name"].strip()
    if db.query(Team).filter_by(name=name).first():
        raise TeamError(f"Team with name '{name}' already exists.")
    team = Team(
        name=name,
        description=data.get("description", "").strip(),
        owner_id=data.get("owner_id")
    )
    db.add(team)
    try:
        db.commit()
        db.refresh(team)
        logger.info(f"Created team '{team.name}' (ID: {team.id})")
        return team
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error while creating team: {e}")
        raise TeamError(f"Error creating team: {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"Exception while creating team: {e}")
        raise TeamError(f"Unexpected error: {e}")

def get_team(db: Session, team_id: int, include_deleted: bool = False) -> Team:
    """
    Получить команду по ID (можно явно указать включать или нет удалённые).
    """
    query = db.query(Team).filter(Team.id == team_id)
    if not include_deleted:
        query = query.filter(Team.is_deleted == False)
    team = query.first()
    if not team:
        raise TeamError(f"Team with id={team_id} not found{' (or is deleted)' if not include_deleted else ''}.")
    return team

def get_all_teams(db: Session, include_deleted: bool = False) -> List[Team]:
    """
    Получить все команды (по умолчанию — только не удалённые).
    """
    query = db.query(Team)
    if not include_deleted:
        query = query.filter(Team.is_deleted == False)
    return query.order_by(Team.name).all()

def update_team(db: Session, team_id: int, data: dict) -> Team:
    """
    Обновить название/описание команды.
    """
    team = get_team(db, team_id)
    if "name" in data:
        new_name = data["name"].strip()
        existing = db.query(Team).filter(Team.name == new_name, Team.id != team_id).first()
        if existing:
            raise TeamError(f"Team with name '{new_name}' already exists.")
        team.name = new_name
    if "description" in data:
        team.description = data["description"].strip()
    team.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(team)
        logger.info(f"Updated team '{team.name}' (ID: {team.id})")
        return team
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating team {team_id}: {e}")
        raise TeamError("Database error while updating team.")

def delete_team(db: Session, team_id: int, soft: bool = True) -> bool:
    """
    Удалить команду: по умолчанию soft-delete, либо hard-delete.
    """
    team = get_team(db, team_id, include_deleted=True)
    if soft:
        if team.is_deleted:
            raise TeamError("Team already deleted.")
        team.is_deleted = True
        team.updated_at = datetime.now(timezone.utc)
        try:
            db.commit()
            logger.info(f"Soft-deleted team {team_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to soft-delete team {team_id}: {e}")
            raise TeamError("Database error while soft-deleting team.")
    else:
        try:
            db.delete(team)
            db.commit()
            logger.info(f"Hard-deleted team {team_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to hard-delete team {team_id}: {e}")
            raise TeamError("Database error while hard-deleting team.")

def restore_team(db: Session, team_id: int) -> bool:
    """
    Восстановить удалённую команду.
    """
    team = get_team(db, team_id, include_deleted=True)
    if not team.is_deleted:
        raise TeamError("Team is not deleted.")
    team.is_deleted = False
    team.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        logger.info(f"Restored team {team_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to restore team {team_id}: {e}")
        raise TeamError("Database error while restoring team.")

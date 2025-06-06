#app/crud/auth.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.auth import AccessToken
from app.models.user import User
from app.core.exceptions import ProjectValidationError
from typing import Optional, List
from datetime import datetime, timezone

import logging
logger = logging.getLogger("DevOS.Auth")

def store_token_info(
    db: Session,
    user_id: int,
    token: str,
    token_type: str,  # 'access' or 'refresh'
    expires_at: Optional[datetime] = None,
    jti: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AccessToken:
    """
    Сохраняет новый access или refresh токен для пользователя.
    """

    if token_type not in ['access', 'refresh']:
        raise ValueError("Invalid token_type. Must be 'access' or 'refresh'.")
    if token_type == 'refresh' and not jti:
        raise ValueError("JTI must be provided for refresh tokens.")

    token_obj_data = {
        "user_id": user_id,
        "token": token, # For access tokens, this is the token itself. For refresh, it's also the token string.
        "token_type": token_type,
        "expires_at": expires_at,
        "jti": jti if token_type == 'refresh' else None,
        "user_agent": user_agent,
        "ip_address": ip_address,
        "is_active": True, # New tokens are active by default
        "revoked": False, # New tokens are not revoked by default
    }

    # Ensure token is unique for access tokens, and JTI is unique for refresh tokens
    # This check is implicitly handled by unique constraints in the model,
    # but explicit checks can provide clearer error messages if desired.
    # For simplicity, relying on DB constraints for now.

    access_token_obj = AccessToken(**token_obj_data)
    db.add(access_token_obj)
    try:
        db.commit()
        db.refresh(access_token_obj)
        logger.info(f"Stored {token_type} token for user {user_id}")
        return access_token_obj
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error storing {token_type} token: {e}")
        err_str = str(e).lower()
        # Determine if it's a token or JTI conflict based on type
        if token_type == 'refresh' and "unique constraint failed: access_tokens.jti" in err_str:
            raise ProjectValidationError(f"Refresh token JTI '{jti}' already exists.")
        elif token_type == 'access' and "unique constraint failed: access_tokens.token" in err_str:
            raise ProjectValidationError("Access token already exists.")
        else: # General conflict
            raise ProjectValidationError(f"Failed to store {token_type} token due to a conflict.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error storing {token_type} token: {e}")
        raise ProjectValidationError(f"Database error while storing {token_type} token.")

def get_access_token(db: Session, token: str) -> Optional[AccessToken]:
    return db.query(AccessToken).filter(
        AccessToken.token == token,
        AccessToken.token_type == 'access', # Ensure it's an access token
        AccessToken.is_active == True,
        AccessToken.revoked == False
    ).first()

def get_active_tokens_by_user(db: Session, user_id: int) -> List[AccessToken]:
    return db.query(AccessToken).filter(
        AccessToken.user_id == user_id,
        AccessToken.is_active == True,
        AccessToken.revoked == False
    ).order_by(AccessToken.created_at.desc()).all()

def revoke_access_token(db: Session, token_str: str) -> bool: # Renamed token to token_str for clarity
    access_token = db.query(AccessToken).filter(
        AccessToken.token == token_str,
        AccessToken.token_type == 'access', # Ensure it's an access token
        AccessToken.is_active == True
    ).first()
    if not access_token:
        # Consider if this should raise an error or return False silently
        logger.warning(f"Access token {token_str} not found or not active for revocation.")
        return False # Or raise ProjectValidationError("Access token not found or already revoked.")

    access_token.revoked = True
    access_token.is_active = False # An active token cannot be revoked=True and active=True
    try:
        db.commit()
        logger.info(f"Revoked access token {token_str}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to revoke access token: {e}")
        raise ProjectValidationError("Database error while revoking access token.")

def revoke_refresh_token(db: Session, token_jti: str) -> bool:
    """Revokes a refresh token based on its JTI."""
    refresh_token_entry = db.query(AccessToken).filter(
        AccessToken.jti == token_jti,
        AccessToken.token_type == 'refresh',
        # AccessToken.is_active == True # A revoked token should not be active
    ).first()

    if not refresh_token_entry:
        logger.warning(f"Refresh token with JTI {token_jti} not found for revocation.")
        return False

    if refresh_token_entry.revoked: # Already revoked
        logger.info(f"Refresh token with JTI {token_jti} was already revoked.")
        return False # Return False if already revoked to allow API to differentiate

    refresh_token_entry.revoked = True
    refresh_token_entry.is_active = False # Ensure consistency
    try:
        db.commit()
        logger.info(f"Revoked refresh token with JTI {token_jti}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to revoke refresh token with JTI {token_jti}: {e}")
        # Avoid raising ProjectValidationError here if a simple boolean is expected for flow control
        return False # Indicate failure

def is_refresh_token_active(db: Session, token_jti: str) -> bool:
    """Checks if a refresh token (by JTI) is active and not revoked."""
    return db.query(AccessToken).filter(
        AccessToken.jti == token_jti,
        AccessToken.token_type == 'refresh',
        AccessToken.is_active == True, # Should be active
        AccessToken.revoked == False   # Should not be revoked
    ).first() is not None

def revoke_all_tokens_for_user(db: Session, user_id: int) -> int:
    # This function now revokes both access and refresh tokens
    tokens = db.query(AccessToken).filter(
        AccessToken.user_id == user_id,
        AccessToken.is_active == True,
        AccessToken.revoked == False
    ).all()
    count = 0
    for token in tokens:
        token.revoked = True
        token.is_active = False
        count += 1
    try:
        db.commit()
        logger.info(f"Revoked {count} total tokens for user {user_id}")
        return count
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to revoke tokens for user: {e}")
        raise ProjectValidationError("Database error while revoking tokens.")

def cleanup_expired_tokens(db: Session) -> int:
    """Deactivate all tokens (access and refresh) that expired before now."""
    now = datetime.now(timezone.utc)
    tokens = db.query(AccessToken).filter(
        AccessToken.is_active == True,
        AccessToken.revoked == False,
        AccessToken.expires_at != None, # expires_at must exist
        AccessToken.expires_at < now
    ).all()
    count = 0
    for token in tokens:
        token.is_active = False # Mark as inactive
        # Optionally mark as revoked too, or have a separate status for 'expired'
        # For now, is_active=False is the primary indicator of non-usability for active checks
        # Setting revoked=True for expired tokens ensures they can't be "un-expired"
        token.revoked = True
        count += 1
    try:
        db.commit()
        logger.info(f"Cleaned up {count} expired tokens")
        return count
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to clean up expired tokens: {e}")
        raise ProjectValidationError("Database error while cleaning up expired tokens.")

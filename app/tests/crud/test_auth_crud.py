import pytest
from sqlalchemy.orm import Session
from app.crud.auth import (
    store_token_info,
    get_access_token,
    get_active_tokens_by_user,
    revoke_access_token,
    revoke_refresh_token,
    is_refresh_token_active,
    revoke_all_tokens_for_user,
    cleanup_expired_tokens
)
from app.models.user import User as UserModel
from app.models.auth import AccessToken as AccessTokenModel
from app.core.exceptions import ProjectValidationError
from datetime import datetime, timedelta, timezone
import uuid

# Fixture for a sample user (can be imported or defined in conftest.py)
# Assuming test_user fixture is available from global conftest.py

def test_store_access_token_success(db: Session, test_user: UserModel):
    token_str = f"test_access_token_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    token_obj = store_token_info(
        db=db,
        user_id=test_user.id,
        token=token_str,
        token_type="access",
        expires_at=expires_at,
        user_agent="test-agent",
        ip_address="127.0.0.1"
    )

    assert token_obj is not None
    assert token_obj.user_id == test_user.id
    assert token_obj.token == token_str
    assert token_obj.token_type == "access"
    # Compare datetimes robustly (assuming token_obj.expires_at might be naive UTC)
    assert abs(token_obj.expires_at.replace(tzinfo=None) - expires_at.replace(tzinfo=None)).total_seconds() < 1
    assert token_obj.jti is None
    assert token_obj.user_agent == "test-agent"
    assert token_obj.ip_address == "127.0.0.1"
    assert token_obj.is_active is True
    assert token_obj.revoked is False

    # Verify it's in the DB
    db_token = db.query(AccessTokenModel).filter(AccessTokenModel.id == token_obj.id).first()
    assert db_token is not None
    assert db_token.token == token_str

def test_store_refresh_token_success(db: Session, test_user: UserModel):
    token_str = f"test_refresh_token_{uuid.uuid4().hex}"
    jti_val = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    token_obj = store_token_info(
        db=db,
        user_id=test_user.id,
        token=token_str, # Refresh token string itself
        token_type="refresh",
        jti=jti_val,
        expires_at=expires_at,
        user_agent="test-agent-refresh",
        ip_address="127.0.0.2"
    )

    assert token_obj is not None
    assert token_obj.user_id == test_user.id
    assert token_obj.token == token_str
    assert token_obj.token_type == "refresh"
    assert token_obj.jti == jti_val
    # Compare datetimes robustly
    assert abs(token_obj.expires_at.replace(tzinfo=None) - expires_at.replace(tzinfo=None)).total_seconds() < 1
    assert token_obj.user_agent == "test-agent-refresh"
    assert token_obj.ip_address == "127.0.0.2"
    assert token_obj.is_active is True
    assert token_obj.revoked is False

    # Verify it's in the DB
    db_token = db.query(AccessTokenModel).filter(AccessTokenModel.id == token_obj.id).first()
    assert db_token is not None
    assert db_token.jti == jti_val

def test_store_token_invalid_type(db: Session, test_user: UserModel):
    with pytest.raises(ValueError, match="Invalid token_type. Must be 'access' or 'refresh'."):
        store_token_info(
            db=db,
            user_id=test_user.id,
            token="some_token",
            token_type="invalid_type"
        )

def test_store_refresh_token_missing_jti(db: Session, test_user: UserModel):
    with pytest.raises(ValueError, match="JTI must be provided for refresh tokens."):
        store_token_info(
            db=db,
            user_id=test_user.id,
            token="refresh_token_no_jti",
            token_type="refresh"
            # JTI omitted
        )

def test_store_duplicate_access_token(db: Session, test_user: UserModel):
    token_str = f"duplicate_access_token_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    # Store first token
    store_token_info(
        db=db, user_id=test_user.id, token=token_str, token_type="access", expires_at=expires_at
    )

    # Attempt to store the same token again for the same or different user
    # The unique constraint is on (token, token_type) effectively, but store_token_info checks for 'access' type.
    # Let's use a different user_id to ensure it's the token itself causing conflict if user_id isn't part of unique key for token string.
    # However, AccessToken model has `UniqueConstraint('token', 'token_type', name='uix_token_type_value')`
    # So, user_id doesn't matter for uniqueness of token string itself.

    another_user_id = test_user.id + 100 # Assuming this ID doesn't exist or is different

    with pytest.raises(ProjectValidationError, match="Access token already exists."):
        store_token_info(
            db=db, user_id=another_user_id, token=token_str, token_type="access", expires_at=expires_at
        )

def test_store_duplicate_refresh_token_jti(db: Session, test_user: UserModel):
    jti_val = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    # Store first token
    store_token_info(
        db=db, user_id=test_user.id, token="refresh_token1_" + uuid.uuid4().hex, token_type="refresh", jti=jti_val, expires_at=expires_at
    )

    # Attempt to store another refresh token with the same JTI
    with pytest.raises(ProjectValidationError, match=f"Refresh token JTI '{jti_val}' already exists."):
        store_token_info(
            db=db, user_id=test_user.id, token="refresh_token2_" + uuid.uuid4().hex, token_type="refresh", jti=jti_val, expires_at=expires_at
        )

def test_get_access_token_found(db: Session, test_user: UserModel):
    token_str = f"get_access_token_found_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    stored_token = store_token_info(
        db=db, user_id=test_user.id, token=token_str, token_type="access", expires_at=expires_at
    )

    fetched_token = get_access_token(db, token_str)
    assert fetched_token is not None
    assert fetched_token.id == stored_token.id
    assert fetched_token.token == token_str

def test_get_access_token_not_found(db: Session):
    fetched_token = get_access_token(db, "non_existent_token")
    assert fetched_token is None

def test_get_access_token_revoked(db: Session, test_user: UserModel):
    token_str = f"get_access_token_revoked_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    stored_token = store_token_info(
        db=db, user_id=test_user.id, token=token_str, token_type="access", expires_at=expires_at
    )
    stored_token.revoked = True
    db.commit()

    fetched_token = get_access_token(db, token_str)
    assert fetched_token is None

def test_get_access_token_inactive(db: Session, test_user: UserModel):
    token_str = f"get_access_token_inactive_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    stored_token = store_token_info(
        db=db, user_id=test_user.id, token=token_str, token_type="access", expires_at=expires_at
    )
    stored_token.is_active = False
    db.commit()

    fetched_token = get_access_token(db, token_str)
    assert fetched_token is None # get_access_token specifically fetches active, non-revoked tokens

def test_get_access_token_wrong_type(db: Session, test_user: UserModel):
    # Store as a refresh token, try to fetch as access token
    token_str = f"get_access_token_wrong_type_{uuid.uuid4().hex}"
    jti_val = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    store_token_info(
        db=db, user_id=test_user.id, token=token_str, token_type="refresh", jti=jti_val, expires_at=expires_at
    )

    fetched_token = get_access_token(db, token_str) # This function filters for token_type='access'
    assert fetched_token is None

def test_get_active_tokens_by_user(db: Session, test_user: UserModel):
    # Token 1 (active access)
    token1_str = f"active_token1_user{test_user.id}_{uuid.uuid4().hex}"
    store_token_info(db, test_user.id, token1_str, "access", datetime.now(timezone.utc) + timedelta(hours=1))

    # Token 2 (active refresh) - should also be returned as it's an active token linked to user
    token2_str = f"active_token2_user{test_user.id}_{uuid.uuid4().hex}"
    store_token_info(db, test_user.id, token2_str, "refresh", datetime.now(timezone.utc) + timedelta(days=1), jti=uuid.uuid4().hex)

    # Token 3 (revoked access)
    token3_str = f"revoked_token3_user{test_user.id}_{uuid.uuid4().hex}"
    revoked_token = store_token_info(db, test_user.id, token3_str, "access", datetime.now(timezone.utc) + timedelta(hours=1))
    revoked_token.revoked = True
    db.commit()

    # Token 4 (inactive access)
    token4_str = f"inactive_token4_user{test_user.id}_{uuid.uuid4().hex}"
    inactive_token = store_token_info(db, test_user.id, token4_str, "access", datetime.now(timezone.utc) + timedelta(hours=1))
    inactive_token.is_active = False
    db.commit()

    # Token 5 (active access, but for another user)
    # Need another user for this. For simplicity, we'll assume test_user.id + 1 is different enough for this test.
    # In a more complex setup, create a distinct other_user.
    other_user_id = test_user.id + 1
    store_token_info(db, other_user_id, f"other_user_token_{uuid.uuid4().hex}", "access", datetime.now(timezone.utc) + timedelta(hours=1))

    active_tokens = get_active_tokens_by_user(db, test_user.id)
    assert len(active_tokens) == 2

    usernames_in_results = [t.token for t in active_tokens]
    assert token1_str in usernames_in_results
    assert token2_str in usernames_in_results
    assert token3_str not in usernames_in_results
    assert token4_str not in usernames_in_results

def test_get_active_tokens_by_user_none(db: Session, test_user: UserModel):
    # Ensure no tokens exist for this user initially or they are all inactive/revoked
    # For this test, let's revoke all if any exist from other tests (though db fixture should isolate)
    existing_tokens = db.query(AccessTokenModel).filter(AccessTokenModel.user_id == test_user.id).all()
    for token in existing_tokens:
        token.is_active = False
        token.revoked = True
    db.commit()

    active_tokens = get_active_tokens_by_user(db, test_user.id)
    assert len(active_tokens) == 0

def test_revoke_access_token(db: Session, test_user: UserModel):
    token_str = f"revoke_access_token_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    stored_token = store_token_info(db, test_user.id, token_str, "access", expires_at)

    assert stored_token.is_active is True
    assert stored_token.revoked is False

    result = revoke_access_token(db, token_str)
    assert result is True

    db.refresh(stored_token) # Refresh from DB
    assert stored_token.is_active is False
    assert stored_token.revoked is True

    # Try to get it via get_access_token (which only gets active, non-revoked)
    assert get_access_token(db, token_str) is None

def test_revoke_access_token_not_found(db: Session):
    result = revoke_access_token(db, "non_existent_for_revoke")
    assert result is False

def test_revoke_refresh_token(db: Session, test_user: UserModel):
    token_str = f"revoke_refresh_token_str_{uuid.uuid4().hex}"
    jti_val = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    stored_token = store_token_info(db, test_user.id, token_str, "refresh", expires_at, jti_val)

    assert stored_token.is_active is True
    assert stored_token.revoked is False

    result = revoke_refresh_token(db, jti_val)
    assert result is True

    db.refresh(stored_token)
    assert stored_token.is_active is False
    assert stored_token.revoked is True

    # Check with is_refresh_token_active
    assert is_refresh_token_active(db, jti_val) is False

def test_revoke_refresh_token_not_found(db: Session):
    result = revoke_refresh_token(db, "non_existent_jti_for_revoke")
    assert result is False

def test_revoke_refresh_token_already_revoked(db: Session, test_user: UserModel):
    jti_val = uuid.uuid4().hex
    stored_token = store_token_info(db, test_user.id, "token_already_revoked", "refresh", datetime.now(timezone.utc) + timedelta(days=1), jti_val)

    # First revocation
    assert revoke_refresh_token(db, jti_val) is True
    db.refresh(stored_token)
    assert stored_token.revoked is True

    # Second revocation attempt
    assert revoke_refresh_token(db, jti_val) is False # Should indicate False (already revoked)

def test_is_refresh_token_active(db: Session, test_user: UserModel):
    jti_active = uuid.uuid4().hex
    jti_revoked = uuid.uuid4().hex
    jti_inactive = uuid.uuid4().hex
    jti_expired = uuid.uuid4().hex
    jti_not_exist = uuid.uuid4().hex

    # Active token
    store_token_info(db, test_user.id, "token_active_jti", "refresh", datetime.now(timezone.utc) + timedelta(days=1), jti_active)
    assert is_refresh_token_active(db, jti_active) is True

    # Revoked token
    revoked_rt = store_token_info(db, test_user.id, "token_revoked_jti", "refresh", datetime.now(timezone.utc) + timedelta(days=1), jti_revoked)
    revoke_refresh_token(db, jti_revoked) # revoke_refresh_token sets is_active=False, revoked=True
    assert is_refresh_token_active(db, jti_revoked) is False

    # Inactive token (but not necessarily revoked by the is_refresh_token_active logic)
    inactive_rt = store_token_info(db, test_user.id, "token_inactive_jti", "refresh", datetime.now(timezone.utc) + timedelta(days=1), jti_inactive)
    inactive_rt.is_active = False
    db.commit()
    assert is_refresh_token_active(db, jti_inactive) is False

    # Expired token (should also be inactive after cleanup, but test is_refresh_token_active before cleanup)
    # is_refresh_token_active itself doesn't check expiry, only is_active and revoked flags.
    # So an expired token that hasn't been cleaned up yet would still be "active" by this function's check if flags are set.
    # To test this properly, we'd need to ensure flags are set as if it were expired and not cleaned.
    # For now, this is covered by the inactive_rt test.

    # Non-existent token
    assert is_refresh_token_active(db, jti_not_exist) is False

def test_revoke_all_tokens_for_user(db: Session, test_user: UserModel):
    user2 = UserModel(username="user2_for_revoke_all", email="user2_revoke@example.com", password_hash="test")
    db.add(user2)
    db.commit()

    # User 1 tokens
    store_token_info(db, test_user.id, f"u1_access1_{uuid.uuid4().hex}", "access", datetime.now(timezone.utc) + timedelta(hours=1))
    store_token_info(db, test_user.id, f"u1_refresh1_{uuid.uuid4().hex}", "refresh", datetime.now(timezone.utc) + timedelta(days=1), jti=uuid.uuid4().hex)

    # User 2 tokens
    store_token_info(db, user2.id, f"u2_access1_{uuid.uuid4().hex}", "access", datetime.now(timezone.utc) + timedelta(hours=1))

    assert len(get_active_tokens_by_user(db, test_user.id)) == 2
    assert len(get_active_tokens_by_user(db, user2.id)) == 1

    revoked_count = revoke_all_tokens_for_user(db, test_user.id)
    assert revoked_count == 2

    assert len(get_active_tokens_by_user(db, test_user.id)) == 0
    assert len(get_active_tokens_by_user(db, user2.id)) == 1 # User 2 tokens should be unaffected

def test_revoke_all_tokens_for_user_no_tokens(db: Session, test_user: UserModel):
    # Ensure user has no active tokens
    revoke_all_tokens_for_user(db, test_user.id) # Clear any existing
    revoked_count = revoke_all_tokens_for_user(db, test_user.id)
    assert revoked_count == 0

def test_cleanup_expired_tokens(db: Session, test_user: UserModel):
    now = datetime.now(timezone.utc)

    # Expired access token
    token_expired_access = f"expired_access_{uuid.uuid4().hex}"
    store_token_info(db, test_user.id, token_expired_access, "access", now - timedelta(hours=1))

    # Expired refresh token
    jti_expired_refresh = uuid.uuid4().hex
    store_token_info(db, test_user.id, f"expired_refresh_{uuid.uuid4().hex}", "refresh", now - timedelta(days=1), jti=jti_expired_refresh)

    # Active access token
    token_active_access = f"active_access_{uuid.uuid4().hex}"
    store_token_info(db, test_user.id, token_active_access, "access", now + timedelta(hours=1))

    # Active refresh token (no expiry, or future expiry)
    jti_active_refresh = uuid.uuid4().hex
    store_token_info(db, test_user.id, f"active_refresh_{uuid.uuid4().hex}", "refresh", now + timedelta(days=1), jti=jti_active_refresh)

    # Token with no expiry (should not be cleaned up by this function)
    token_no_expiry = f"no_expiry_{uuid.uuid4().hex}"
    store_token_info(db, test_user.id, token_no_expiry, "access", expires_at=None)

    cleaned_count = cleanup_expired_tokens(db)
    assert cleaned_count == 2 # Expired access and expired refresh

    assert get_access_token(db, token_expired_access) is None
    assert is_refresh_token_active(db, jti_expired_refresh) is False

    assert get_access_token(db, token_active_access) is not None
    assert is_refresh_token_active(db, jti_active_refresh) is True
    assert get_access_token(db, token_no_expiry) is not None # Should still be active

# TODO: Create app/tests/api/test_auth_api.py

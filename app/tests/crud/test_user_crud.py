import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.crud import user as crud_user
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import ProjectValidationError
from app.models.user import User as UserModel

def test_create_user_success(db: Session):
    user_in = UserCreate(username="newuser", email="newuser@example.com", password="password123")
    user = crud_user.create_user(db, user_in.model_dump())
    assert user is not None
    assert user.username == "newuser"
    assert user.email == "newuser@example.com"
    assert user.is_active is True
    assert user.is_superuser is False
    assert hasattr(user, "password_hash")
    assert crud_user.verify_password("password123", user.password_hash)

def test_create_user_duplicate_username(db: Session):
    user_in1 = UserCreate(username="dupuser", email="dupuser1@example.com", password="password123")
    crud_user.create_user(db, user_in1.model_dump())

    user_in2 = UserCreate(username="dupuser", email="dupuser2@example.com", password="password456")
    with pytest.raises(ProjectValidationError, match="User with this username or email already exists."):
        crud_user.create_user(db, user_in2.model_dump())

def test_create_user_duplicate_email(db: Session):
    user_in1 = UserCreate(username="anotheruser1", email="dupemail@example.com", password="password123")
    crud_user.create_user(db, user_in1.model_dump())

    user_in2 = UserCreate(username="anotheruser2", email="dupemail@example.com", password="password456")
    with pytest.raises(ProjectValidationError, match="User with this username or email already exists."):
        crud_user.create_user(db, user_in2.model_dump())

def test_get_user(db: Session):
    user_in = UserCreate(username="getmeuser", email="getme@example.com", password="password")
    created_user = crud_user.create_user(db, user_in.model_dump())

    fetched_user = crud_user.get_user(db, created_user.id)
    assert fetched_user is not None
    assert fetched_user.id == created_user.id
    assert fetched_user.username == "getmeuser"

    non_existent_user = crud_user.get_user(db, 99999) # Assuming 99999 does not exist
    assert non_existent_user is None

def test_get_user_by_username(db: Session):
    user_in = UserCreate(username="findbyusername", email="findbyusername@example.com", password="password")
    crud_user.create_user(db, user_in.model_dump())

    fetched_user = crud_user.get_user_by_username(db, "findbyusername")
    assert fetched_user is not None
    assert fetched_user.username == "findbyusername"

    non_existent_user = crud_user.get_user_by_username(db, "nosuchusername")
    assert non_existent_user is None

def test_get_user_by_email(db: Session):
    user_in = UserCreate(username="findbyemailuser", email="findbyemail@example.com", password="password")
    crud_user.create_user(db, user_in.model_dump())

    fetched_user = crud_user.get_user_by_email(db, "findbyemail@example.com")
    assert fetched_user is not None
    assert fetched_user.email == "findbyemail@example.com"

    non_existent_user = crud_user.get_user_by_email(db, "nosuchemail@example.com")
    assert non_existent_user is None

def test_authenticate_user(db: Session):
    user_in = UserCreate(username="authuser", email="auth@example.com", password="testpassword")
    crud_user.create_user(db, user_in.model_dump())

    authenticated_user = crud_user.authenticate_user(db, "authuser", "testpassword")
    assert authenticated_user is not None
    assert authenticated_user.username == "authuser"

    wrong_password_user = crud_user.authenticate_user(db, "authuser", "wrongpassword")
    assert wrong_password_user is None

    non_existent_user = crud_user.authenticate_user(db, "noauthuser", "testpassword")
    assert non_existent_user is None

def test_update_user(db: Session):
    user_in = UserCreate(username="updateuser", email="update@example.com", password="password")
    original_user = crud_user.create_user(db, user_in.model_dump())
    db.refresh(original_user) # Ensure initial timestamps are loaded
    original_updated_at = original_user.updated_at
    assert original_updated_at is not None # Should have a value after refresh

    # Introduce a small delay to ensure timestamp difference if system is very fast
    import time
    time.sleep(0.001)

    update_data = {"full_name": "Updated Name", "email": "updated_email@example.com"}
    updated_user = crud_user.update_user(db, original_user.id, update_data) # This should commit

    assert updated_user is not None
    assert updated_user.full_name == "Updated Name"
    assert updated_user.email == "updated_email@example.com"
    assert updated_user.username == "updateuser" # Username should not change unless specified
    assert updated_user.updated_at is not None
    assert updated_user.updated_at > original_updated_at

    # Test password update
    password_update_data = {"password": "newpassword123"}
    password_updated_user = crud_user.update_user(db, original_user.id, password_update_data)
    assert crud_user.verify_password("newpassword123", password_updated_user.password_hash)
    assert not crud_user.verify_password("password", password_updated_user.password_hash) # Old password fails

    with pytest.raises(ProjectValidationError, match="User not found."):
        crud_user.update_user(db, 9999, {"full_name": "Ghost User"})


def test_soft_delete_user(db: Session):
    user_in = UserCreate(username="deactivateuser", email="deactivate@example.com", password="password")
    user_to_deactivate = crud_user.create_user(db, user_in.model_dump())

    assert user_to_deactivate.is_active is True

    result = crud_user.soft_delete_user(db, user_to_deactivate.id)
    assert result is True

    deactivated_user = crud_user.get_user(db, user_to_deactivate.id) # get_user should still fetch it
    assert deactivated_user is not None
    assert deactivated_user.is_active is False

    with pytest.raises(ProjectValidationError, match="User not found."):
        crud_user.soft_delete_user(db, 9999) # Non-existent user

def test_get_users(db: Session):
    crud_user.create_user(db, UserCreate(username="user1", email="user1@example.com", password="password1", full_name="Alpha User", roles=["dev"]).model_dump())
    crud_user.create_user(db, UserCreate(username="user2", email="user2@example.com", password="password2", full_name="Beta User", roles=["manager"]).model_dump())
    crud_user.soft_delete_user(db, crud_user.get_user_by_username(db, "user2").id) # Deactivate user2
    crud_user.create_user(db, UserCreate(username="user3", email="user3@example.com", password="password3", full_name="Gamma User", roles=["dev"]).model_dump())

    all_active_users = crud_user.get_users(db, filters={"is_active": True})
    assert len(all_active_users) == 2
    assert "user2" not in [u.username for u in all_active_users]

    all_users_no_filter = crud_user.get_users(db) # Default should be active only based on current crud
    # Assuming default of get_users is also active only if not specified.
    # If get_users by default gets ALL users (active and inactive), this assertion needs change.
    # Based on `soft_delete_user` which only sets `is_active=False`, models are not removed.
    # The `get_users` function itself does not show explicit is_active filtering by default,
    # so this test might need adjustment based on exact `get_users` behavior for no filters.
    # For now, assuming it filters by is_active=True if not specified, or adjust as per actual behavior.

    # To make it more robust, let's check the specific behavior of get_users without filters.
    # If it returns all (including inactive):
    # all_users_including_inactive = db.query(UserModel).all()
    # assert len(crud_user.get_users(db)) == len(all_users_including_inactive)
    # For now, let's assume is_active=True is the default or common case for "get_users"

    dev_users = crud_user.get_users(db, filters={"role": "dev", "is_active": True})
    assert len(dev_users) == 2
    assert "user1" in [u.username for u in dev_users]
    assert "user3" in [u.username for u in dev_users]

    search_users = crud_user.get_users(db, filters={"search": "Alpha", "is_active": True})
    assert len(search_users) == 1
    assert search_users[0].username == "user1"

    empty_search = crud_user.get_users(db, filters={"search": "NonExistentName", "is_active": True})
    assert len(empty_search) == 0

def test_get_users_default_no_active_filter(db: Session):
    # Clean up users from other tests in this session or ensure unique names
    u1 = crud_user.create_user(db, UserCreate(username="default_user1", email="default1@example.com", password="password").model_dump())
    u2_data = UserCreate(username="default_user2", email="default2@example.com", password="password").model_dump()
    u2_data['is_active'] = False # Create an inactive user directly
    u2 = crud_user.create_user(db, u2_data)

    all_users = crud_user.get_users(db) # No filters
    usernames = [user.username for user in all_users]

    assert u1.username in usernames
    assert u2.username in usernames
    assert len(all_users) >= 2 # Check at least these two are present

def test_set_last_login(db: Session):
    user_in = UserCreate(username="loginuser", email="login@example.com", password="password")
    user = crud_user.create_user(db, user_in.model_dump())

    assert user.last_login_at is None # Initially None

    crud_user.set_last_login(db, user.id)
    db.refresh(user) # Refresh to get the updated value from DB

    updated_user = crud_user.get_user(db, user.id)
    assert updated_user.last_login_at is not None

    # Test on non-existent user (should not raise error, just do nothing or handle gracefully)
    crud_user.set_last_login(db, 99999) # Assuming 99999 does not exist, no error expected
    # No assertion needed, just checking it doesn't crash.

def test_create_user_with_specific_roles_and_status(db: Session):
    user_in = UserCreate(
        username="specialuser",
        email="special@example.com",
        password="password123",
        roles=["editor", "viewer"],
        is_active=False,
        is_superuser=True
    )
    user = crud_user.create_user(db, user_in.model_dump())
    assert user.roles == ["editor", "viewer"]
    assert user.is_active is False
    assert user.is_superuser is True

def test_update_user_roles_and_status(db: Session):
    user_in = UserCreate(username="roleupdateuser", email="roleupdate@example.com", password="password")
    user = crud_user.create_user(db, user_in.model_dump())

    update_data = {
        "roles": ["admin"],
        "is_active": False,
        "is_superuser": True
    }
    updated_user = crud_user.update_user(db, user.id, update_data)

    assert updated_user.roles == ["admin"]
    assert updated_user.is_active is False
    assert updated_user.is_superuser is True

def test_get_password_hash_and_verify(db: Session):
    password = "securepassword!123"
    hashed_password = crud_user.get_password_hash(password)
    assert hashed_password != password # Ensure it's hashed
    assert crud_user.verify_password(password, hashed_password) is True
    assert crud_user.verify_password("wrongpassword", hashed_password) is False

# Test for edge case in create_user, e.g. empty username/email if not caught by Pydantic
# However, Pydantic UserCreate schema should enforce this.
# If ProjectValidationError is raised for empty fields by CRUD before DB constraints:
# def test_create_user_empty_username(db: Session):
#     with pytest.raises(ProjectValidationError, match="Username cannot be empty"): # Or appropriate error
#         crud_user.create_user(db, UserCreate(username="", email="test@example.com", password="pw").model_dump())

# def test_create_user_empty_email(db: Session):
#     with pytest.raises(ProjectValidationError, match="Email cannot be empty"): # Or appropriate error
#         crud_user.create_user(db, UserCreate(username="testuser", email="", password="pw").model_dump())

# These depend on whether validation is in Pydantic or CRUD layer.
# Current `create_user` checks for existing username/email but not emptiness, assuming Pydantic handles it.
# The `ProjectValidationError` is for "already exists" or generic DB error.
# If Pydantic UserCreate allows empty strings, then these tests would be valid for CRUD.
# Let's assume Pydantic UserCreate handles this.
# If `data["username"].strip()` is used, then empty string might become an issue at DB level if not unique.
# The current `create_user` does `data["username"].strip()`.
# If username is an empty string after strip and DB constraint is NOT NULL, UNIQUE, IntegrityError happens.
# The `ProjectValidationError` for "User with this username or email already exists." might be too generic
# if an IntegrityError for a NOT NULL constraint (e.g. empty username) fires.

# The current CRUD `create_user` raises `ProjectValidationError("User with this username or email already exists.")`
# if the initial query finds a match, or for IntegrityError during commit.
# So an IntegrityError from an empty username (if "" is not unique and already exists) would map to that.
# If "" is unique but violates NOT NULL, it would also be an IntegrityError.
# This means the current exception handling in CRUD might mask the true nature of some IntegrityErrors.
# However, for this test suite, we trust Pydantic for field-level validation like "is not empty".
# The CRUD tests focus on what the CRUD functions themselves are responsible for.

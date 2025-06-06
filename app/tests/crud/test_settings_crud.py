import pytest
import uuid
from sqlalchemy.orm import Session
from app.crud import settings as crud_settings
from app.models.settings import Setting as SettingModel
from app.models.user import User as UserModel
from app.core.exceptions import ProjectValidationError # Should ideally be SettingValidationError
from typing import Optional, Dict, Any

# --- Fixtures ---

@pytest.fixture
def setting_data_factory():
    def _factory(**kwargs) -> Dict[str, Any]:
        unique_key_suffix = uuid.uuid4().hex[:6]
        data: Dict[str, Any] = {
            "key": f"test_setting_{unique_key_suffix}",
            "value": {"theme": "dark", "notifications": True},
            "description": "A test setting description.",
            "user_id": None, # Default to global
            "is_active": True
        }
        data.update(kwargs)
        return data
    return _factory

# --- Tests for create_setting ---

def test_create_global_setting_success(db: Session, setting_data_factory: callable):
    setting_data = setting_data_factory(user_id=None, key="global_theme")
    created_setting = crud_settings.create_setting(db, setting_data)

    assert created_setting is not None
    assert created_setting.id is not None
    assert created_setting.key == "global_theme"
    assert created_setting.value == setting_data["value"]
    assert created_setting.user_id is None
    assert created_setting.is_active is True

def test_create_user_specific_setting_success(db: Session, test_user: UserModel, setting_data_factory: callable):
    setting_data = setting_data_factory(user_id=test_user.id, key="user_theme")
    created_setting = crud_settings.create_setting(db, setting_data)

    assert created_setting is not None
    assert created_setting.key == "user_theme"
    assert created_setting.user_id == test_user.id

def test_create_setting_duplicate_global_key_error(db: Session, setting_data_factory: callable):
    setting_data = setting_data_factory(key="duplicate_global_key", user_id=None)
    crud_settings.create_setting(db, setting_data) # Create first one

    setting_data_dup = setting_data_factory(key="duplicate_global_key", value={"mode": "light"}, user_id=None)
    with pytest.raises(ProjectValidationError, match="Setting with this key already exists for this user."):
        crud_settings.create_setting(db, setting_data_dup)

def test_create_setting_duplicate_key_for_same_user_error(db: Session, test_user: UserModel, setting_data_factory: callable):
    setting_data = setting_data_factory(key="user_specific_key", user_id=test_user.id)
    crud_settings.create_setting(db, setting_data)

    setting_data_dup = setting_data_factory(key="user_specific_key", value={"fontSize": 14}, user_id=test_user.id)
    with pytest.raises(ProjectValidationError, match="Setting with this key already exists for this user."):
        crud_settings.create_setting(db, setting_data_dup)

def test_create_setting_same_key_different_users_raises_error_due_to_global_unique_key(
    db: Session, test_user: UserModel, test_superuser: UserModel, setting_data_factory: callable
):
    # Using a more unique key for this specific test to avoid conflict if tests run out of order or DB is not perfectly clean.
    key = f"common_key_global_test_{uuid.uuid4().hex[:4]}"
    setting_data_user1 = setting_data_factory(key=key, user_id=test_user.id, value="user1_value")
    crud_settings.create_setting(db, setting_data_user1)

    setting_data_user2 = setting_data_factory(key=key, user_id=test_superuser.id, value="user2_value")
    # This should fail due to UNIQUE constraint on settings.key column in the database,
    # even though the CRUD's initial check (key + user_id) would pass.
    # The IntegrityError from DB is caught and re-raised as ProjectValidationError in CRUD.
    with pytest.raises(ProjectValidationError, match="Setting already exists."):
        crud_settings.create_setting(db, setting_data_user2)

# --- Tests for get_setting ---

def test_get_global_setting_success(db: Session, setting_data_factory: callable):
    setting_data = setting_data_factory(key="get_global_theme", user_id=None, value="light")
    crud_settings.create_setting(db, setting_data)

    fetched_setting = crud_settings.get_setting(db, key="get_global_theme", user_id=None)
    assert fetched_setting is not None
    assert fetched_setting.key == "get_global_theme"
    assert fetched_setting.value == "light"
    assert fetched_setting.user_id is None

def test_get_user_specific_setting_success(db: Session, test_user: UserModel, setting_data_factory: callable):
    setting_data = setting_data_factory(key="get_user_theme", user_id=test_user.id, value="dark_user")
    crud_settings.create_setting(db, setting_data)

    fetched_setting = crud_settings.get_setting(db, key="get_user_theme", user_id=test_user.id)
    assert fetched_setting is not None
    assert fetched_setting.key == "get_user_theme"
    assert fetched_setting.value == "dark_user"
    assert fetched_setting.user_id == test_user.id

def test_get_setting_not_found_key(db: Session):
    assert crud_settings.get_setting(db, key="non_existent_key_global") is None
    assert crud_settings.get_setting(db, key="non_existent_key_user", user_id=1) is None

def test_get_setting_not_found_for_user(db: Session, test_user: UserModel, setting_data_factory: callable):
    # Setting for another user exists with a specific key
    other_user_id = test_user.id + 100
    specific_key_for_other_user = f"key_for_user_{other_user_id}"
    setting_data_other_user = setting_data_factory(key=specific_key_for_other_user, user_id=other_user_id, value="other_user_val")
    crud_settings.create_setting(db, setting_data_other_user)

    # Attempt to get this specific key for test_user, for whom it doesn't exist
    assert crud_settings.get_setting(db, key=specific_key_for_other_user, user_id=test_user.id) is None

    # Also, a global setting with a different key
    global_key = "global_key_test_not_found_for_user"
    setting_data_global = setting_data_factory(key=global_key, user_id=None, value="global_val")
    crud_settings.create_setting(db, setting_data_global)
    # Attempt to get this global key as if it were specific to test_user (should not be found as user-specific)
    assert crud_settings.get_setting(db, key=global_key, user_id=test_user.id) is None

def test_get_user_setting_with_user_id_none_fails(db: Session, test_user: UserModel, setting_data_factory: callable):
    # User-specific setting exists
    setting_data_user = setting_data_factory(key="user_specific_for_get_none", user_id=test_user.id)
    crud_settings.create_setting(db, setting_data_user)

    # Attempt to get it by passing user_id=None (expecting global)
    assert crud_settings.get_setting(db, key="user_specific_for_get_none", user_id=None) is None

def test_get_global_setting_with_user_id_fails(db: Session, test_user: UserModel, setting_data_factory: callable):
    # Global setting exists
    setting_data_global = setting_data_factory(key="global_for_get_user", user_id=None)
    crud_settings.create_setting(db, setting_data_global)

    # Attempt to get it by passing a user_id
    assert crud_settings.get_setting(db, key="global_for_get_user", user_id=test_user.id) is None

# --- Tests for update_setting ---

def test_update_setting_success(db: Session, test_user: UserModel, setting_data_factory: callable):
    # Create a user-specific setting first
    setting_data = setting_data_factory(key="updatable_user_setting", user_id=test_user.id, value={"initial": "value"})
    created_setting = crud_settings.create_setting(db, setting_data)
    db.refresh(created_setting) # Load created_at/updated_at
    original_updated_at = created_setting.updated_at

    import time; time.sleep(0.01) # Ensure timestamp difference

    update_data = {
        "value": {"new": "updated_value", "flag": True},
        "description": "Updated description.",
        "is_active": False
    }
    updated_setting = crud_settings.update_setting(db, created_setting.id, update_data)

    assert updated_setting is not None
    assert updated_setting.id == created_setting.id
    assert updated_setting.key == "updatable_user_setting" # Key should not change
    assert updated_setting.user_id == test_user.id # User ID should not change
    assert updated_setting.value == update_data["value"]
    assert updated_setting.description == update_data["description"]
    assert updated_setting.is_active is False
    assert updated_setting.updated_at > original_updated_at

def test_update_setting_partial_value_update(db: Session, test_user: UserModel, setting_data_factory: callable):
    setting_data = setting_data_factory(key="partial_update_setting", user_id=test_user.id, value={"a": 1, "b": 2})
    created_setting = crud_settings.create_setting(db, setting_data)

    # The current update_setting replaces the whole 'value' JSON object.
    # It does not do a deep merge.
    update_data = {"value": {"a": 10}} # This will replace {"a":1, "b":2} with {"a":10}
    updated_setting = crud_settings.update_setting(db, created_setting.id, update_data)
    assert updated_setting.value == {"a": 10}

    update_data_desc = {"description": "New desc only"}
    updated_setting_desc = crud_settings.update_setting(db, created_setting.id, update_data_desc)
    assert updated_setting_desc.description == "New desc only"
    assert updated_setting_desc.value == {"a": 10} # Value from previous update should persist

def test_update_setting_not_found(db: Session):
    with pytest.raises(ProjectValidationError, match="Setting not found."):
        crud_settings.update_setting(db, 99999, {"value": "new_value"})

def test_update_global_setting_success(db: Session, setting_data_factory: callable):
    setting_data = setting_data_factory(key="updatable_global_setting", user_id=None, value="initial_global")
    created_setting = crud_settings.create_setting(db, setting_data)

    update_data = {"value": "updated_global_value", "is_active": False}
    updated_setting = crud_settings.update_setting(db, created_setting.id, update_data)
    assert updated_setting.value == "updated_global_value"
    assert updated_setting.is_active is False
    assert updated_setting.user_id is None # Should remain global

# --- Tests for delete_setting ---

def test_delete_global_setting_success(db: Session, setting_data_factory: callable):
    setting_data = setting_data_factory(key="delete_global_key", user_id=None)
    created_setting = crud_settings.create_setting(db, setting_data)

    result = crud_settings.delete_setting(db, created_setting.id)
    assert result is True

    assert crud_settings.get_setting(db, key="delete_global_key", user_id=None) is None

def test_delete_user_setting_success(db: Session, test_user: UserModel, setting_data_factory: callable):
    setting_data = setting_data_factory(key="delete_user_key", user_id=test_user.id)
    created_setting = crud_settings.create_setting(db, setting_data)

    result = crud_settings.delete_setting(db, created_setting.id)
    assert result is True

    assert crud_settings.get_setting(db, key="delete_user_key", user_id=test_user.id) is None

def test_delete_setting_not_found(db: Session):
    with pytest.raises(ProjectValidationError, match="Setting not found."):
        crud_settings.delete_setting(db, 99999)

# --- Tests for get_all_settings ---

@pytest.fixture
def settings_set(db: Session, test_user: UserModel, test_superuser: UserModel, setting_data_factory: callable):
    settings = [
        setting_data_factory(key="global_setting_1", user_id=None, value="g1"),
        setting_data_factory(key="global_setting_2", user_id=None, value="g2"),
        setting_data_factory(key="user1_setting_1", user_id=test_user.id, value="u1_1"),
        setting_data_factory(key="user1_setting_2", user_id=test_user.id, value="u1_2"),
        setting_data_factory(key="user2_setting_1", user_id=test_superuser.id, value="u2_1"),
    ]
    created_settings = [crud_settings.create_setting(db, s) for s in settings]
    return created_settings

def test_get_all_settings_for_user(db: Session, test_user: UserModel, settings_set):
    user_settings = crud_settings.get_all_settings(db, user_id=test_user.id)
    assert len(user_settings) == 2
    user_setting_keys = {s.key for s in user_settings}
    assert "user1_setting_1" in user_setting_keys
    assert "user1_setting_2" in user_setting_keys
    for s in user_settings:
        assert s.user_id == test_user.id

def test_get_all_settings_global_with_user_id_none(db: Session, settings_set):
    global_settings = crud_settings.get_all_settings(db, user_id=None)
    assert len(global_settings) == 2
    global_setting_keys = {s.key for s in global_settings}
    assert "global_setting_1" in global_setting_keys
    assert "global_setting_2" in global_setting_keys
    for s in global_settings:
        assert s.user_id is None

def test_get_all_settings_global_with_no_user_id_arg(db: Session, settings_set):
    # crud_settings.get_all_settings defaults user_id to None if not provided
    global_settings = crud_settings.get_all_settings(db)
    assert len(global_settings) == 2
    global_setting_keys = {s.key for s in global_settings}
    assert "global_setting_1" in global_setting_keys
    assert "global_setting_2" in global_setting_keys

def test_get_all_settings_no_settings_for_user(db: Session, settings_set):
    # A user_id for whom no settings were created
    non_existent_user_id = 999
    user_settings = crud_settings.get_all_settings(db, user_id=non_existent_user_id)
    assert len(user_settings) == 0

def test_get_all_settings_no_global_settings(db: Session, test_user: UserModel, setting_data_factory):
    # Create only user-specific settings
    crud_settings.create_setting(db, setting_data_factory(key="user_only_setting", user_id=test_user.id))
    global_settings = crud_settings.get_all_settings(db, user_id=None)
    assert len(global_settings) == 0

def test_get_all_settings_empty_db(db: Session): # No settings created at all
    settings = crud_settings.get_all_settings(db) # Should get global, which is none
    assert len(settings) == 0
    user_settings = crud_settings.get_all_settings(db, user_id=1) # User specific
    assert len(user_settings) == 0


def test_create_setting_default_is_active_true(db: Session, setting_data_factory: callable):
    setting_data = setting_data_factory(key="default_active_test")
    del setting_data["is_active"] # Rely on default
    created_setting = crud_settings.create_setting(db, setting_data)
    assert created_setting.is_active is True

def test_create_setting_explicit_is_active_false(db: Session, setting_data_factory: callable):
    setting_data = setting_data_factory(key="explicit_inactive_test", is_active=False)
    created_setting = crud_settings.create_setting(db, setting_data)
    assert created_setting.is_active is False

# TODO: Add tests for get_setting, update_setting, delete_setting, get_all_settings

def test_settings_placeholder(): # Placeholder
    assert True

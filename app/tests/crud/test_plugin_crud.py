import pytest
import uuid
from sqlalchemy.orm import Session
from app.crud import plugin as crud_plugin
from app.models.plugin import Plugin as PluginModel
from app.core.exceptions import PluginNotFoundError, PluginValidationError
from datetime import datetime, timezone
import time # For time.sleep

@pytest.fixture
def basic_plugin_data_factory():
    def _factory(**kwargs):
        unique_suffix = uuid.uuid4().hex[:6]
        data = {
            "name": f"Test Plugin {unique_suffix}",
            "description": "A test plugin description.",
            "config_json": {"key1": "value1", "key2": 123},
            "is_active": True,
            "version": "1.0.0",
            "author": "Test Author",
            "subscription_level": "free",
            "is_private": False,
            "ui_component": "TestComponent",
            "tags": ["test", "pytest"]
        }
        data.update(kwargs)
        return data
    return _factory

# --- Tests for create_plugin ---

def test_create_plugin_success_minimal(db: Session, basic_plugin_data_factory):
    plugin_data = basic_plugin_data_factory(name="Minimal Plugin")
    minimal_data = {"name": plugin_data["name"]}
    created_plugin = crud_plugin.create_plugin(db, minimal_data)
    assert created_plugin is not None
    assert created_plugin.id is not None
    assert created_plugin.name == minimal_data["name"]
    assert created_plugin.description == ""
    assert created_plugin.config_json == {}
    assert created_plugin.is_active is True
    assert created_plugin.tags == []

def test_create_plugin_success_all_fields(db: Session, basic_plugin_data_factory):
    plugin_data = basic_plugin_data_factory()
    created_plugin = crud_plugin.create_plugin(db, plugin_data)
    assert created_plugin.name == plugin_data["name"]
    assert created_plugin.description == plugin_data["description"]
    assert created_plugin.config_json == plugin_data["config_json"]
    assert created_plugin.is_active == plugin_data["is_active"]
    assert created_plugin.version == plugin_data["version"]
    assert created_plugin.author == plugin_data["author"]
    assert created_plugin.subscription_level == plugin_data["subscription_level"]
    assert created_plugin.is_private == plugin_data["is_private"]
    assert created_plugin.ui_component == plugin_data["ui_component"]
    assert sorted(created_plugin.tags) == sorted(plugin_data["tags"])

def test_create_plugin_config_json_as_string(db: Session, basic_plugin_data_factory):
    import json
    plugin_data = basic_plugin_data_factory(config_json=json.dumps({"test_key": "test_value"}))
    created_plugin = crud_plugin.create_plugin(db, plugin_data)
    assert created_plugin.config_json == {"test_key": "test_value"}

def test_create_plugin_error_missing_name(db: Session, basic_plugin_data_factory):
    plugin_data = basic_plugin_data_factory()
    del plugin_data["name"]
    with pytest.raises(PluginValidationError, match="Plugin name is required."):
        crud_plugin.create_plugin(db, plugin_data)

def test_create_plugin_error_empty_name(db: Session, basic_plugin_data_factory):
    plugin_data = basic_plugin_data_factory(name=" ")
    with pytest.raises(PluginValidationError, match="Plugin name is required."):
        crud_plugin.create_plugin(db, plugin_data)

def test_create_plugin_error_duplicate_name(db: Session, basic_plugin_data_factory):
    plugin_data = basic_plugin_data_factory()
    crud_plugin.create_plugin(db, plugin_data)
    with pytest.raises(PluginValidationError, match=f"Plugin with name '{plugin_data['name']}' already exists."):
        crud_plugin.create_plugin(db, plugin_data)

def test_create_plugin_error_invalid_config_json_string(db: Session, basic_plugin_data_factory):
    plugin_data = basic_plugin_data_factory(config_json="this is not json")
    with pytest.raises(PluginValidationError, match="Invalid JSON format for configuration."):
        crud_plugin.create_plugin(db, plugin_data)

def test_create_plugin_error_invalid_config_json_type(db: Session, basic_plugin_data_factory):
    plugin_data = basic_plugin_data_factory(config_json=12345)
    with pytest.raises(PluginValidationError, match="Configuration must be a valid JSON string or a dictionary."):
        crud_plugin.create_plugin(db, plugin_data)

# --- Tests for get_plugin ---

def test_get_plugin_success(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    fetched_plugin = crud_plugin.get_plugin(db, created_plugin.id)
    assert fetched_plugin is not None
    assert fetched_plugin.id == created_plugin.id
    assert fetched_plugin.name == created_plugin.name
    assert fetched_plugin.is_deleted is False

def test_get_plugin_not_found(db: Session):
    with pytest.raises(PluginNotFoundError):
        crud_plugin.get_plugin(db, 99999)

def test_get_plugin_soft_deleted_default_not_found(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    created_plugin.is_deleted = True
    created_plugin.deleted_at = datetime.now(timezone.utc)
    db.commit()
    with pytest.raises(PluginNotFoundError):
        crud_plugin.get_plugin(db, created_plugin.id)

def test_get_plugin_soft_deleted_with_include_deleted_success(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    created_plugin.is_deleted = True
    created_plugin.deleted_at = datetime.now(timezone.utc)
    db.commit()
    fetched_plugin = crud_plugin.get_plugin(db, created_plugin.id, include_deleted=True)
    assert fetched_plugin is not None
    assert fetched_plugin.is_deleted is True

# --- Tests for get_plugin_by_name ---

def test_get_plugin_by_name_success(db: Session, basic_plugin_data_factory):
    plugin_data = basic_plugin_data_factory()
    created_plugin = crud_plugin.create_plugin(db, plugin_data)
    fetched_plugin = crud_plugin.get_plugin_by_name(db, created_plugin.name)
    assert fetched_plugin is not None
    assert fetched_plugin.name == plugin_data["name"]

def test_get_plugin_by_name_not_found(db: Session):
    assert crud_plugin.get_plugin_by_name(db, "NonExistentName") is None

def test_get_plugin_by_name_soft_deleted_default_not_found(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    created_plugin.is_deleted = True
    db.commit()
    assert crud_plugin.get_plugin_by_name(db, created_plugin.name) is None

def test_get_plugin_by_name_soft_deleted_with_include_deleted_success(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    created_plugin.is_deleted = True
    db.commit()
    fetched_plugin = crud_plugin.get_plugin_by_name(db, created_plugin.name, include_deleted=True)
    assert fetched_plugin is not None
    assert fetched_plugin.is_deleted is True

# --- Fixture for a set of plugins for list tests ---
@pytest.fixture
def plugin_set(db: Session, basic_plugin_data_factory):
    plugins_data = [
        basic_plugin_data_factory(name="Active Free Plugin", is_active=True, subscription_level="free", tags=["free_tag", "active"]),
        basic_plugin_data_factory(name="Inactive Free Plugin", is_active=False, subscription_level="free", tags=["free_tag", "inactive"]),
        basic_plugin_data_factory(name="Active Pro Plugin Public", is_active=True, subscription_level="pro", is_private=False, tags=["pro_tag", "public"]),
        basic_plugin_data_factory(name="Active Pro Plugin Private", is_active=True, subscription_level="pro", is_private=True, tags=["pro_tag", "private"]),
        basic_plugin_data_factory(name="Deleted Active Plugin", is_active=True, tags=["deleted", "active"]),
        basic_plugin_data_factory(name="Deleted Inactive Plugin", is_active=False, tags=["deleted", "inactive"]),
    ]
    created_plugins_map = {}
    for data in plugins_data:
        plugin = crud_plugin.create_plugin(db, data)
        if "Deleted" in data["name"]:
            plugin.is_deleted = True
            plugin.deleted_at = datetime.now(timezone.utc)
        created_plugins_map[data["name"]] = plugin
    db.commit()
    return created_plugins_map

# --- Tests for get_all_plugins ---

def test_get_all_plugins_default(db: Session, plugin_set: dict):
    all_plugins = crud_plugin.get_all_plugins(db)
    assert len(all_plugins) == 4
    for p in all_plugins:
        assert p.is_deleted is False

def test_get_all_plugins_include_deleted(db: Session, plugin_set: dict):
    all_plugins = crud_plugin.get_all_plugins(db, include_deleted=True)
    assert len(all_plugins) == 6

def test_get_all_plugins_filter_is_active_true(db: Session, plugin_set: dict):
    active_plugins = crud_plugin.get_all_plugins(db, filters={"is_active": True})
    assert len(active_plugins) == 3
    for p in active_plugins:
        assert p.is_active is True and p.is_deleted is False

def test_get_all_plugins_filter_is_active_false(db: Session, plugin_set: dict):
    inactive_plugins = crud_plugin.get_all_plugins(db, filters={"is_active": False})
    assert len(inactive_plugins) == 1
    assert inactive_plugins[0].name == "Inactive Free Plugin"

def test_get_all_plugins_filter_is_active_false_include_deleted(db: Session, plugin_set: dict):
    inactive_plugins = crud_plugin.get_all_plugins(db, filters={"is_active": False}, include_deleted=True)
    assert len(inactive_plugins) == 2
    names = {p.name for p in inactive_plugins}
    assert "Inactive Free Plugin" in names
    assert "Deleted Inactive Plugin" in names

def test_get_all_plugins_filter_subscription_level(db: Session, plugin_set: dict):
    pro_plugins = crud_plugin.get_all_plugins(db, filters={"subscription_level": "pro"})
    assert len(pro_plugins) == 2
    for p in pro_plugins:
        assert p.subscription_level == "pro"

def test_get_all_plugins_filter_is_private_true(db: Session, plugin_set: dict):
    private_plugins = crud_plugin.get_all_plugins(db, filters={"is_private": True})
    assert len(private_plugins) == 1
    assert private_plugins[0].name == "Active Pro Plugin Private"

def test_get_all_plugins_filter_tag(db: Session, plugin_set: dict):
    pro_tag_plugins = crud_plugin.get_all_plugins(db, filters={"tag": "pro_tag"})
    assert len(pro_tag_plugins) == 2
    for p in pro_tag_plugins:
        assert "pro_tag" in p.tags

def test_get_all_plugins_filter_combined(db: Session, plugin_set: dict):
    filtered_plugins = crud_plugin.get_all_plugins(db, filters={
        "is_active": True, "subscription_level": "pro", "is_private": True
    })
    assert len(filtered_plugins) == 1
    assert filtered_plugins[0].name == "Active Pro Plugin Private"

def test_get_all_plugins_no_results(db: Session, plugin_set: dict):
    no_match_plugins = crud_plugin.get_all_plugins(db, filters={"tag": "non_existent_tag"})
    assert len(no_match_plugins) == 0

def test_get_all_plugins_empty_db(db: Session):
    all_plugins = crud_plugin.get_all_plugins(db)
    assert len(all_plugins) == 0

# --- Tests for update_plugin ---

def test_update_plugin_success_all_fields(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory(name="Original Name"))
    db.refresh(created_plugin)
    time_of_creation = created_plugin.updated_at

    unique_suffix_update = uuid.uuid4().hex[:6]
    update_data = {
        "name": f"Updated Plugin Name {unique_suffix_update}", "description": "Updated plugin description.",
        "config_json": {"new_key": "new_value"}, "is_active": False, "version": "1.1.0",
        "author": "Updated Author", "subscription_level": "pro", "is_private": True,
        "ui_component": "UpdatedComponent", "tags": ["updated_tag"]
    }
    time.sleep(0.01)
    updated_plugin = crud_plugin.update_plugin(db, created_plugin.id, update_data)

    assert updated_plugin.name == update_data["name"]
    assert updated_plugin.description == update_data["description"]
    assert updated_plugin.config_json == update_data["config_json"]
    assert updated_plugin.is_active == update_data["is_active"]
    assert updated_plugin.version == update_data["version"]
    assert updated_plugin.author == update_data["author"]
    assert updated_plugin.subscription_level == update_data["subscription_level"]
    assert updated_plugin.is_private == update_data["is_private"]
    assert updated_plugin.ui_component == update_data["ui_component"]
    assert sorted(updated_plugin.tags) == sorted(update_data["tags"])
    assert updated_plugin.updated_at >= time_of_creation

def test_update_plugin_partial_success(db: Session, basic_plugin_data_factory):
    plugin_data = basic_plugin_data_factory()
    created_plugin = crud_plugin.create_plugin(db, plugin_data)
    update_data = {"description": "A very new description"}
    updated_plugin = crud_plugin.update_plugin(db, created_plugin.id, update_data)
    assert updated_plugin.description == "A very new description"
    assert updated_plugin.name == plugin_data["name"]

def test_update_plugin_config_json_string_and_dict(db: Session, basic_plugin_data_factory):
    import json
    plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    config_str = json.dumps({"key_str": "val_str"})
    updated_plugin_str = crud_plugin.update_plugin(db, plugin.id, {"config_json": config_str})
    assert updated_plugin_str.config_json == {"key_str": "val_str"}
    config_dict = {"key_dict": "val_dict"}
    updated_plugin_dict = crud_plugin.update_plugin(db, plugin.id, {"config_json": config_dict})
    assert updated_plugin_dict.config_json == {"key_dict": "val_dict"}

def test_update_plugin_not_found(db: Session):
    with pytest.raises(PluginNotFoundError):
        crud_plugin.update_plugin(db, 99999, {"description": "test"})

def test_update_plugin_error_empty_name(db: Session, basic_plugin_data_factory):
    plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    with pytest.raises(PluginValidationError, match="Plugin name cannot be empty."):
        crud_plugin.update_plugin(db, plugin.id, {"name": " "})

def test_update_plugin_error_duplicate_name(db: Session, basic_plugin_data_factory):
    p1 = crud_plugin.create_plugin(db, basic_plugin_data_factory(name="Plugin One"))
    p2 = crud_plugin.create_plugin(db, basic_plugin_data_factory(name="Plugin Two"))
    with pytest.raises(PluginValidationError, match=f"Plugin with name '{p1.name}' already exists."):
        crud_plugin.update_plugin(db, p2.id, {"name": p1.name})

def test_update_plugin_error_invalid_config_json_string(db: Session, basic_plugin_data_factory):
    plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    with pytest.raises(PluginValidationError, match="Invalid JSON format for configuration."):
        crud_plugin.update_plugin(db, plugin.id, {"config_json": "not json"})

def test_update_plugin_error_invalid_config_json_type(db: Session, basic_plugin_data_factory):
    plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    with pytest.raises(PluginValidationError, match="Configuration must be a valid JSON string or a dictionary."):
        crud_plugin.update_plugin(db, plugin.id, {"config_json": 123})

# --- Tests for soft_delete_plugin ---

def test_soft_delete_plugin_success(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory(is_active=True))
    deleted_plugin = crud_plugin.soft_delete_plugin(db, created_plugin.id)
    assert deleted_plugin.is_deleted is True
    assert deleted_plugin.deleted_at is not None
    assert deleted_plugin.is_active is False
    plugin_in_db = crud_plugin.get_plugin(db, created_plugin.id, include_deleted=True)
    assert plugin_in_db.is_deleted is True

def test_soft_delete_plugin_not_found(db: Session):
    with pytest.raises(PluginNotFoundError):
        crud_plugin.soft_delete_plugin(db, 99999)

def test_soft_delete_plugin_already_deleted(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    crud_plugin.soft_delete_plugin(db, created_plugin.id)
    first_deleted_at = created_plugin.deleted_at # db.refresh(created_plugin) might be needed if not auto-refreshed
    db.refresh(created_plugin) # ensure first_deleted_at is loaded after commit by soft_delete
    first_deleted_at = created_plugin.deleted_at

    deleted_plugin_again = crud_plugin.soft_delete_plugin(db, created_plugin.id)
    assert deleted_plugin_again.is_deleted is True
    assert deleted_plugin_again.deleted_at == first_deleted_at

# --- Tests for restore_plugin ---

def test_restore_plugin_success(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory(is_active=True))
    crud_plugin.soft_delete_plugin(db, created_plugin.id)
    assert created_plugin.is_active is False # Due to soft_delete

    restored_plugin = crud_plugin.restore_plugin(db, created_plugin.id)
    assert restored_plugin.is_deleted is False
    assert restored_plugin.deleted_at is None
    assert restored_plugin.is_active is False # Restore doesn't auto-reactivate

def test_restore_plugin_not_found(db: Session):
    with pytest.raises(PluginNotFoundError):
        crud_plugin.restore_plugin(db, 99999)

def test_restore_plugin_not_deleted_error(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    with pytest.raises(PluginValidationError, match="is not deleted"):
        crud_plugin.restore_plugin(db, created_plugin.id)

# --- Tests for hard_delete_plugin ---

def test_hard_delete_plugin_success(db: Session, basic_plugin_data_factory):
    plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    assert crud_plugin.hard_delete_plugin(db, plugin.id) is True
    with pytest.raises(PluginNotFoundError):
        crud_plugin.get_plugin(db, plugin.id, include_deleted=True)

def test_hard_delete_soft_deleted_plugin_success(db: Session, basic_plugin_data_factory):
    plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    crud_plugin.soft_delete_plugin(db, plugin.id)
    assert crud_plugin.hard_delete_plugin(db, plugin.id) is True
    with pytest.raises(PluginNotFoundError):
        crud_plugin.get_plugin(db, plugin.id, include_deleted=True)

def test_hard_delete_plugin_not_found(db: Session):
    with pytest.raises(PluginNotFoundError):
        crud_plugin.hard_delete_plugin(db, 99999)

# --- Tests for activate_plugin ---

def test_activate_plugin_success(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory(is_active=False))
    assert created_plugin.is_active is False
    activated_plugin = crud_plugin.activate_plugin(db, created_plugin.id)
    assert activated_plugin.is_active is True

def test_activate_already_active_plugin(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory(is_active=True))
    activated_plugin = crud_plugin.activate_plugin(db, created_plugin.id)
    assert activated_plugin.is_active is True

def test_activate_plugin_not_found(db: Session):
    with pytest.raises(PluginNotFoundError):
        crud_plugin.activate_plugin(db, 99999)

def test_activate_soft_deleted_plugin_error(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    crud_plugin.soft_delete_plugin(db, created_plugin.id)
    with pytest.raises(PluginValidationError, match="Cannot activate a deleted plugin"):
        crud_plugin.activate_plugin(db, created_plugin.id)

# --- Tests for deactivate_plugin ---

def test_deactivate_plugin_success(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory(is_active=True))
    deactivated_plugin = crud_plugin.deactivate_plugin(db, created_plugin.id)
    assert deactivated_plugin.is_active is False

def test_deactivate_already_inactive_plugin(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory(is_active=False))
    deactivated_plugin = crud_plugin.deactivate_plugin(db, created_plugin.id)
    assert deactivated_plugin.is_active is False

def test_deactivate_plugin_not_found(db: Session):
    with pytest.raises(PluginNotFoundError):
        crud_plugin.deactivate_plugin(db, 99999)

def test_deactivate_soft_deleted_plugin_error(db: Session, basic_plugin_data_factory):
    created_plugin = crud_plugin.create_plugin(db, basic_plugin_data_factory())
    crud_plugin.soft_delete_plugin(db, created_plugin.id)
    # deactivate_plugin calls get_plugin (default include_deleted=False)
    with pytest.raises(PluginNotFoundError):
        crud_plugin.deactivate_plugin(db, created_plugin.id)

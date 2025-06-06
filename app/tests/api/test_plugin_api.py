#tests/api/test_plugin_api.py
import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User as UserModel # For type hints
from app.models.plugin import Plugin as PluginModel # For DB verification
from app.crud.plugin import get_plugin as crud_get_plugin # For DB verification

# --- Fixtures ---

@pytest.fixture
def plugin_api_payload_factory():
    def _factory(**kwargs):
        unique_suffix = uuid.uuid4().hex[:6]
        data = {
            "name": f"API Test Plugin {unique_suffix}",
            "description": "An API test plugin.",
            "config_json": {"api_key": "value1", "api_setting": True},
            "is_active": True,
            "version": "1.0.1",
            "author": "API Test Author",
            "subscription_level": "free",
            "is_private": False,
            "ui_component": "APITestComponent",
            "tags": ["api_test", "pytest_api"]
        }
        data.update(kwargs)
        return data
    return _factory

# --- Tests for POST /plugins/ ---

def test_create_plugin_api_success_superuser(
    client: TestClient, superuser_token_headers: dict, plugin_api_payload_factory: callable, db: Session
):
    payload = plugin_api_payload_factory()
    response = client.post("/plugins/", json=payload, headers=superuser_token_headers)

    assert response.status_code == 200 # Default for FastAPI if not specified in decorator
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["config_json"] == payload["config_json"]
    assert data["is_active"] == payload["is_active"]
    # Verify in DB
    plugin_in_db = db.query(PluginModel).filter(PluginModel.id == data["id"]).first()
    assert plugin_in_db is not None
    assert plugin_in_db.name == payload["name"]

def test_create_plugin_api_forbidden_normal_user(
    client: TestClient, normal_user_token_headers: dict, plugin_api_payload_factory: callable
):
    payload = plugin_api_payload_factory()
    response = client.post("/plugins/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]

def test_create_plugin_api_unauthenticated(
    client: TestClient, plugin_api_payload_factory: callable
):
    payload = plugin_api_payload_factory()
    response = client.post("/plugins/", json=payload) # No headers
    assert response.status_code == 401

def test_create_plugin_api_validation_error_missing_name_superuser(
    client: TestClient, superuser_token_headers: dict, plugin_api_payload_factory: callable
):
    payload = plugin_api_payload_factory()
    del payload["name"]
    # Pydantic schema PluginCreate requires name, so this will be a 422 from FastAPI
    response = client.post("/plugins/", json=payload, headers=superuser_token_headers)
    assert response.status_code == 422 # Pydantic validation error

def test_create_plugin_api_duplicate_name_superuser(
    client: TestClient, superuser_token_headers: dict, plugin_api_payload_factory: callable, db: Session
):
    payload = plugin_api_payload_factory(name="Duplicate Test Plugin API")
    # Create first plugin
    response1 = client.post("/plugins/", json=payload, headers=superuser_token_headers)
    assert response1.status_code == 200

    # Attempt to create another with the same name
    response2 = client.post("/plugins/", json=payload, headers=superuser_token_headers)
    assert response2.status_code == 400 # From CRUD: PluginValidationError
    assert "already exists" in response2.json()["detail"]

def test_create_plugin_api_invalid_config_json_string_superuser(
    client: TestClient, superuser_token_headers: dict, plugin_api_payload_factory: callable
):
    payload = plugin_api_payload_factory(config_json="this is not valid json")
    response = client.post("/plugins/", json=payload, headers=superuser_token_headers)
    assert response.status_code == 422 # FastAPI/Pydantic validation for incorrect type
    # The detail for a 422 error will be structured differently, e.g., about "value is not a valid dict"
    # For now, just check the status code. If more specific error checking is needed, inspect response.json().
    # assert "Invalid JSON format for configuration" in response.json()["detail"] # This would be for a 400 from CRUD

# --- Fixture for a set of plugins for API list tests ---
@pytest.fixture
def api_plugin_set(db: Session, plugin_api_payload_factory: callable, superuser_token_headers: dict, client: TestClient):
    # Use CRUD to create plugins for more direct setup and to avoid API dependencies for setup
    from app.crud.plugin import create_plugin as crud_create_plugin
    from app.crud.plugin import soft_delete_plugin as crud_soft_delete_plugin # To soft delete some

    plugins_data_specs = [
        {"name": "API Active Free", "is_active": True, "subscription_level": "free", "tags": ["api_free", "general"]},
        {"name": "API Inactive Free", "is_active": False, "subscription_level": "free", "tags": ["api_free", "utility"]},
        {"name": "API Active Pro Public", "is_active": True, "subscription_level": "pro", "is_private": False, "tags": ["api_pro", "public"]},
        {"name": "API Active Pro Private", "is_active": True, "subscription_level": "pro", "is_private": True, "tags": ["api_pro", "private_content"]}, # is_private doesn't affect list visibility for plugins
        {"name": "API ToBeDeleted Active", "is_active": True, "tags": ["to_delete"]},
        {"name": "API ToBeDeleted Inactive", "is_active": False, "tags": ["to_delete", "old"]},
    ]

    created_plugins_map = {}
    for spec in plugins_data_specs:
        payload = plugin_api_payload_factory(**spec)
        # Use CRUD for setup
        plugin = crud_create_plugin(db, payload) # Use the raw dict from factory
        created_plugins_map[spec["name"]] = plugin

    # Soft delete some plugins
    crud_soft_delete_plugin(db, created_plugins_map["API ToBeDeleted Active"].id)
    crud_soft_delete_plugin(db, created_plugins_map["API ToBeDeleted Inactive"].id)

    db.commit()
    # Re-fetch all to ensure test has fresh objects from the session
    all_plugins_from_db = {}
    for name, plugin in created_plugins_map.items():
        # Fetch including deleted ones to get all of them for the fixture's return value
        re_fetched_plugin = crud_get_plugin(db, plugin.id, include_deleted=True)
        all_plugins_from_db[name] = re_fetched_plugin

    return all_plugins_from_db


# --- Tests for GET /plugins/ ---

def test_list_plugins_api_normal_user_default(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    response = client.get("/plugins/", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    # Expected: 4 non-deleted plugins (Active Free, Inactive Free, Active Pro Public, Active Pro Private)
    # The default list_plugins API does not filter by is_active unless specified
    assert len(data) == 4
    for p_short in data:
        # Verify that none of the soft-deleted plugins are returned
        original_plugin = api_plugin_set[p_short["name"]] # Get original from fixture by name
        assert original_plugin.is_deleted is False


def test_list_plugins_api_superuser_default(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict
):
    response = client.get("/plugins/", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4 # Same as normal user, no include_deleted by default

def test_list_plugins_api_filter_active_true(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    response = client.get("/plugins/?is_active=true", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    # Active Free, Active Pro Public, Active Pro Private
    assert len(data) == 3
    for p_short in data:
        assert p_short["is_active"] is True

def test_list_plugins_api_filter_active_false(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    response = client.get("/plugins/?is_active=false", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    # Inactive Free
    assert len(data) == 1
    assert data[0]["name"] == "API Inactive Free"
    assert data[0]["is_active"] is False

def test_list_plugins_api_filter_subscription_level_pro(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    response = client.get("/plugins/?subscription_level=pro", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    # Active Pro Public, Active Pro Private
    assert len(data) == 2
    for p_short in data:
        original_plugin = api_plugin_set[p_short["name"]]
        assert original_plugin.subscription_level == "pro"

def test_list_plugins_api_filter_tag_general(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    response = client.get("/plugins/?tag=general", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    # Active Free Plugin
    assert len(data) == 1
    assert data[0]["name"] == "API Active Free"

def test_list_plugins_api_no_plugins_match_filter(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    response = client.get("/plugins/?tag=non_existent_tag_api", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

def test_list_plugins_api_empty_db(
    client: TestClient, normal_user_token_headers: dict, db: Session # Use db to ensure clean state
):
    # Ensure no plugins exist
    db.query(PluginModel).delete()
    db.commit()

    response = client.get("/plugins/", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

# --- Tests for GET /plugins/{plugin_id} ---

def test_get_one_plugin_api_success_normal_user(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    # Get a known active, non-deleted plugin from the fixture
    plugin_to_get = api_plugin_set["API Active Free"]
    assert plugin_to_get.is_deleted is False # Sanity check fixture

    response = client.get(f"/plugins/{plugin_to_get.id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == plugin_to_get.id
    assert data["name"] == plugin_to_get.name
    assert data["description"] == plugin_to_get.description
    assert data["config_json"] == plugin_to_get.config_json
    assert data["is_active"] == plugin_to_get.is_active
    assert data["version"] == plugin_to_get.version
    assert data["author"] == plugin_to_get.author
    assert data["subscription_level"] == plugin_to_get.subscription_level
    assert data["is_private"] == plugin_to_get.is_private # is_private for plugins does not mean normal users cannot see it
    assert data["ui_component"] == plugin_to_get.ui_component
    assert sorted(data["tags"]) == sorted(plugin_to_get.tags)

def test_get_one_plugin_api_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict
):
    plugin_to_get = api_plugin_set["API Active Pro Private"] # A private plugin
    assert plugin_to_get.is_deleted is False

    response = client.get(f"/plugins/{plugin_to_get.id}", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == plugin_to_get.id
    assert data["name"] == plugin_to_get.name
    assert data["is_private"] is True

def test_get_one_plugin_api_not_found(
    client: TestClient, normal_user_token_headers: dict
):
    non_existent_id = uuid.uuid4().int & (1<<30)-1
    response = client.get(f"/plugins/{non_existent_id}", headers=normal_user_token_headers)
    assert response.status_code == 404
    assert f"Plugin with ID {non_existent_id} not found (or is deleted)" in response.json()["detail"]

def test_get_one_plugin_api_soft_deleted_returns_404(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    soft_deleted_plugin = api_plugin_set["API ToBeDeleted Active"]
    assert soft_deleted_plugin.is_deleted is True # Sanity check fixture

    response = client.get(f"/plugins/{soft_deleted_plugin.id}", headers=normal_user_token_headers)
    assert response.status_code == 404 # Default get_one_plugin does not include deleted
    assert f"Plugin with ID {soft_deleted_plugin.id} not found (or is deleted)" in response.json()["detail"]

def test_get_one_plugin_api_unauthenticated(
    client: TestClient, api_plugin_set: dict
):
    plugin_to_get = api_plugin_set["API Active Free"]
    response = client.get(f"/plugins/{plugin_to_get.id}") # No headers
    assert response.status_code == 401


# --- Tests for PATCH /plugins/{plugin_id} ---

def test_update_plugin_api_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict, plugin_api_payload_factory: callable, db: Session
):
    plugin_to_update = api_plugin_set["API Active Free"] # Get a known plugin

    update_payload_dict = {
        "name": f"Updated - {plugin_to_update.name}",
        "description": "This plugin has been updated via API.",
        "is_active": False,
        "version": "2.0.0",
        "tags": ["updated", "api_patch"],
        "config_json": {"new_api_key": "new_secret_value"}
    }

    response = client.patch(f"/plugins/{plugin_to_update.id}", json=update_payload_dict, headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_payload_dict["name"]
    assert data["description"] == update_payload_dict["description"]
    assert data["is_active"] is False
    assert data["version"] == "2.0.0"
    assert sorted(data["tags"]) == sorted(["updated", "api_patch"])
    assert data["config_json"] == {"new_api_key": "new_secret_value"}

    # Verify in DB
    # db.refresh(plugin_to_update) # This will fail due to session issues with fixture object
    updated_plugin_in_db = crud_get_plugin(db, plugin_to_update.id) # Fetch anew
    assert updated_plugin_in_db is not None # Ensure it was found
    assert updated_plugin_in_db.name == update_payload_dict["name"]
    assert updated_plugin_in_db.is_active is False

def test_update_plugin_api_partial_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict, db: Session
):
    plugin_to_update = api_plugin_set["API Active Pro Public"]
    original_name = plugin_to_update.name
    update_payload_dict = {"is_active": False}

    response = client.patch(f"/plugins/{plugin_to_update.id}", json=update_payload_dict, headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False
    assert data["name"] == original_name # Name should not change

    updated_plugin_in_db = crud_get_plugin(db, plugin_to_update.id)
    assert updated_plugin_in_db.is_active is False
    assert updated_plugin_in_db.name == original_name

def test_update_plugin_api_forbidden_normal_user(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict, plugin_api_payload_factory: callable
):
    plugin_to_update = api_plugin_set["API Active Free"]
    update_payload_dict = plugin_api_payload_factory(description="Attempted update by normal user")

    response = client.patch(f"/plugins/{plugin_to_update.id}", json=update_payload_dict, headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]

def test_update_plugin_api_not_found_superuser(
    client: TestClient, superuser_token_headers: dict, plugin_api_payload_factory: callable
):
    non_existent_id = uuid.uuid4().int & (1<<30)-1
    update_payload_dict = plugin_api_payload_factory(name="Update Non Existent")

    response = client.patch(f"/plugins/{non_existent_id}", json=update_payload_dict, headers=superuser_token_headers)
    assert response.status_code == 404
    # Detail comes from CRUD's get_plugin via update_plugin
    assert f"Plugin with ID {non_existent_id} not found (or is deleted)" in response.json()["detail"]


def test_update_plugin_api_validation_empty_name_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict
):
    plugin_to_update = api_plugin_set["API Inactive Free"]
    update_payload_dict = {"name": " "} # Invalid empty name

    response = client.patch(f"/plugins/{plugin_to_update.id}", json=update_payload_dict, headers=superuser_token_headers)
    assert response.status_code == 400 # PluginValidationError from CRUD
    assert "Plugin name cannot be empty" in response.json()["detail"]

def test_update_plugin_api_validation_duplicate_name_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict
):
    plugin1 = api_plugin_set["API Active Free"]
    plugin2 = api_plugin_set["API Inactive Free"]
    update_payload_dict = {"name": plugin1.name} # Try to update plugin2's name to plugin1's name

    response = client.patch(f"/plugins/{plugin2.id}", json=update_payload_dict, headers=superuser_token_headers)
    assert response.status_code == 400 # PluginValidationError from CRUD
    assert f"Plugin with name '{plugin1.name}' already exists" in response.json()["detail"]

def test_update_plugin_api_invalid_config_json_string_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict
):
    plugin_to_update = api_plugin_set["API Active Free"]
    update_payload_dict = {"config_json": "this is not valid json"}

    response = client.patch(f"/plugins/{plugin_to_update.id}", json=update_payload_dict, headers=superuser_token_headers)
    # Based on PluginUpdate schema, if config_json is Optional[Dict], FastAPI will yield 422
    # If PluginUpdate allows Any for config_json, then CRUD's validation will be hit (400)
    # Assuming PluginUpdate.config_json is proper Dict (or Union that includes Dict)
    assert response.status_code == 422

def test_update_plugin_api_unauthenticated(
    client: TestClient, api_plugin_set: dict, plugin_api_payload_factory: callable
):
    plugin_to_update = api_plugin_set["API Active Free"]
    update_payload_dict = plugin_api_payload_factory(description="Unauthenticated update")

    response = client.patch(f"/plugins/{plugin_to_update.id}", json=update_payload_dict) # No headers
    assert response.status_code == 401

def test_update_soft_deleted_plugin_api_not_found_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict, plugin_api_payload_factory: callable
):
    plugin_to_update = api_plugin_set["API ToBeDeleted Active"] # This plugin is soft-deleted in fixture
    assert plugin_to_update.is_deleted is True

    update_payload_dict = plugin_api_payload_factory(description="Attempt to update soft-deleted")
    response = client.patch(f"/plugins/{plugin_to_update.id}", json=update_payload_dict, headers=superuser_token_headers)
    assert response.status_code == 404 # update_plugin calls get_plugin (default no include_deleted)
    assert f"Plugin with ID {plugin_to_update.id} not found (or is deleted)" in response.json()["detail"]


# --- Tests for DELETE /plugins/{plugin_id} ---

def test_delete_plugin_api_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict, db: Session
):
    plugin_to_delete = api_plugin_set["API Active Free"] # Get an active plugin
    assert plugin_to_delete.is_deleted is False # Pre-condition

    response = client.delete(f"/plugins/{plugin_to_delete.id}", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == plugin_to_delete.id
    assert "Plugin archived (soft-deleted)" in data["detail"]

    # Verify in DB
    deleted_plugin_in_db = crud_get_plugin(db, plugin_to_delete.id, include_deleted=True)
    assert deleted_plugin_in_db is not None
    assert deleted_plugin_in_db.is_deleted is True
    assert deleted_plugin_in_db.is_active is False # Soft delete also deactivates

def test_delete_plugin_api_forbidden_normal_user(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    plugin_to_delete = api_plugin_set["API Active Pro Public"]
    response = client.delete(f"/plugins/{plugin_to_delete.id}", headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]

def test_delete_plugin_api_not_found_superuser(
    client: TestClient, superuser_token_headers: dict
):
    non_existent_id = uuid.uuid4().int & (1<<30)-1
    response = client.delete(f"/plugins/{non_existent_id}", headers=superuser_token_headers)
    assert response.status_code == 404
    # This detail comes from the PluginNotFoundError in crud's get_plugin (via soft_delete_plugin)
    assert f"Plugin with ID {non_existent_id} not found" in response.json()["detail"]


def test_delete_already_soft_deleted_plugin_api_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict, db: Session
):
    # API's delete_one_plugin calls crud's soft_delete_plugin.
    # crud's soft_delete_plugin calls get_plugin(include_deleted=True).
    # If already deleted, crud's soft_delete_plugin logs and returns the plugin.
    # The API then returns SuccessResponse.
    plugin_already_deleted = api_plugin_set["API ToBeDeleted Active"]
    assert plugin_already_deleted.is_deleted is True # Pre-condition

    response = client.delete(f"/plugins/{plugin_already_deleted.id}", headers=superuser_token_headers)
    assert response.status_code == 200 # Should succeed and indicate it's archived
    data = response.json()
    assert data["result"] == plugin_already_deleted.id
    assert "Plugin archived (soft-deleted)" in data["detail"]

    # Verify it's still soft-deleted
    plugin_in_db = crud_get_plugin(db, plugin_already_deleted.id, include_deleted=True)
    assert plugin_in_db.is_deleted is True

def test_delete_plugin_api_unauthenticated(
    client: TestClient, api_plugin_set: dict
):
    plugin_to_delete = api_plugin_set["API Active Free"]
    response = client.delete(f"/plugins/{plugin_to_delete.id}") # No headers
    assert response.status_code == 401


# --- Tests for POST /plugins/{plugin_id}/restore ---

def test_restore_plugin_api_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict, db: Session
):
    plugin_to_restore = api_plugin_set["API ToBeDeleted Active"] # This was soft-deleted
    assert plugin_to_restore.is_deleted is True # Pre-condition
    # Note: soft_delete_plugin in CRUD also sets is_active=False
    original_active_status_when_deleted = plugin_to_restore.is_active

    response = client.post(f"/plugins/{plugin_to_restore.id}/restore", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == plugin_to_restore.id
    assert data["is_deleted"] is False
    assert data["deleted_at"] is None
    assert data["is_active"] == original_active_status_when_deleted # Restore doesn't auto-activate

    # Verify in DB
    restored_plugin_in_db = crud_get_plugin(db, plugin_to_restore.id)
    assert restored_plugin_in_db is not None
    assert restored_plugin_in_db.is_deleted is False
    assert restored_plugin_in_db.is_active == original_active_status_when_deleted

def test_restore_plugin_api_forbidden_normal_user(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    plugin_to_restore = api_plugin_set["API ToBeDeleted Inactive"]
    assert plugin_to_restore.is_deleted is True

    response = client.post(f"/plugins/{plugin_to_restore.id}/restore", headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]

def test_restore_plugin_api_not_found_superuser(
    client: TestClient, superuser_token_headers: dict
):
    non_existent_id = uuid.uuid4().int & (1<<30)-1
    response = client.post(f"/plugins/{non_existent_id}/restore", headers=superuser_token_headers)
    assert response.status_code == 404
    # Detail comes from CRUD's get_plugin(include_deleted=True) which is called by restore_plugin
    assert f"Plugin with ID {non_existent_id} not found" in response.json()["detail"]

def test_restore_plugin_api_not_deleted_error_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict
):
    active_plugin = api_plugin_set["API Active Free"] # This plugin is not deleted
    assert active_plugin.is_deleted is False

    response = client.post(f"/plugins/{active_plugin.id}/restore", headers=superuser_token_headers)
    assert response.status_code == 400 # PluginValidationError from CRUD
    assert f"Plugin '{active_plugin.name}' (ID: {active_plugin.id}) is not deleted" in response.json()["detail"]

def test_restore_plugin_api_unauthenticated(
    client: TestClient, api_plugin_set: dict
):
    plugin_to_restore = api_plugin_set["API ToBeDeleted Active"]
    response = client.post(f"/plugins/{plugin_to_restore.id}/restore") # No headers
    assert response.status_code == 401


# --- Tests for POST /plugins/{plugin_id}/activate ---

def test_activate_plugin_api_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict, db: Session
):
    inactive_plugin = api_plugin_set["API Inactive Free"]
    assert inactive_plugin.is_active is False # Pre-condition

    response = client.post(f"/plugins/{inactive_plugin.id}/activate", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == inactive_plugin.id
    assert data["is_active"] is True

    db_plugin = crud_get_plugin(db, inactive_plugin.id)
    assert db_plugin.is_active is True

def test_activate_already_active_plugin_api_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict, db: Session
):
    active_plugin = api_plugin_set["API Active Free"]
    assert active_plugin.is_active is True # Pre-condition

    response = client.post(f"/plugins/{active_plugin.id}/activate", headers=superuser_token_headers)
    assert response.status_code == 200 # Idempotent
    assert response.json()["is_active"] is True

def test_activate_plugin_api_forbidden_normal_user(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    inactive_plugin = api_plugin_set["API Inactive Free"]
    response = client.post(f"/plugins/{inactive_plugin.id}/activate", headers=normal_user_token_headers)
    assert response.status_code == 403

def test_activate_plugin_api_not_found_superuser(
    client: TestClient, superuser_token_headers: dict
):
    non_existent_id = uuid.uuid4().int & (1<<30)-1
    response = client.post(f"/plugins/{non_existent_id}/activate", headers=superuser_token_headers)
    assert response.status_code == 404 # From get_plugin(include_deleted=True) in CRUD activate

def test_activate_soft_deleted_plugin_api_error_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict
):
    soft_deleted_plugin = api_plugin_set["API ToBeDeleted Inactive"]
    assert soft_deleted_plugin.is_deleted is True

    response = client.post(f"/plugins/{soft_deleted_plugin.id}/activate", headers=superuser_token_headers)
    assert response.status_code == 400 # PluginValidationError from CRUD
    assert "Cannot activate a deleted plugin" in response.json()["detail"]

def test_activate_plugin_api_unauthenticated(client: TestClient, api_plugin_set: dict):
    inactive_plugin = api_plugin_set["API Inactive Free"]
    response = client.post(f"/plugins/{inactive_plugin.id}/activate")
    assert response.status_code == 401

# --- Tests for POST /plugins/{plugin_id}/deactivate ---

def test_deactivate_plugin_api_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict, db: Session
):
    active_plugin = api_plugin_set["API Active Free"]
    assert active_plugin.is_active is True # Pre-condition

    response = client.post(f"/plugins/{active_plugin.id}/deactivate", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == active_plugin.id
    assert data["is_active"] is False

    db_plugin = crud_get_plugin(db, active_plugin.id)
    assert db_plugin.is_active is False

def test_deactivate_already_inactive_plugin_api_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict, db: Session
):
    inactive_plugin = api_plugin_set["API Inactive Free"]
    assert inactive_plugin.is_active is False # Pre-condition

    response = client.post(f"/plugins/{inactive_plugin.id}/deactivate", headers=superuser_token_headers)
    assert response.status_code == 200 # Idempotent
    assert response.json()["is_active"] is False

def test_deactivate_plugin_api_forbidden_normal_user(
    client: TestClient, normal_user_token_headers: dict, api_plugin_set: dict
):
    active_plugin = api_plugin_set["API Active Free"]
    response = client.post(f"/plugins/{active_plugin.id}/deactivate", headers=normal_user_token_headers)
    assert response.status_code == 403

def test_deactivate_plugin_api_not_found_superuser(
    client: TestClient, superuser_token_headers: dict
):
    non_existent_id = uuid.uuid4().int & (1<<30)-1
    response = client.post(f"/plugins/{non_existent_id}/deactivate", headers=superuser_token_headers)
    assert response.status_code == 404 # From get_plugin in CRUD deactivate

def test_deactivate_soft_deleted_plugin_api_error_superuser(
    client: TestClient, superuser_token_headers: dict, api_plugin_set: dict
):
    # CRUD deactivate_plugin calls get_plugin (default no include_deleted)
    # So this will result in a 404 from the API's perspective
    soft_deleted_plugin = api_plugin_set["API ToBeDeleted Active"]
    assert soft_deleted_plugin.is_deleted is True

    response = client.post(f"/plugins/{soft_deleted_plugin.id}/deactivate", headers=superuser_token_headers)
    assert response.status_code == 404
    assert f"Plugin with ID {soft_deleted_plugin.id} not found (or is deleted)" in response.json()["detail"]

def test_deactivate_plugin_api_unauthenticated(client: TestClient, api_plugin_set: dict):
    active_plugin = api_plugin_set["API Active Free"]
    response = client.post(f"/plugins/{active_plugin.id}/deactivate")
    assert response.status_code == 401

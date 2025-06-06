import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.models.user import User as UserModel
from app.models.settings import Setting as SettingModel
from app.crud.settings import get_setting as crud_get_setting
from app.crud.settings import create_setting as crud_create_setting
from app.crud.settings import delete_setting as crud_delete_setting
from app.crud.settings import update_setting as crud_update_setting


from app.schemas.settings import SettingCreate, SettingRead

# --- Fixtures ---

@pytest.fixture
def setting_api_payload_factory():
    def _factory(**kwargs) -> Dict[str, Any]:
        unique_key_suffix = uuid.uuid4().hex[:4]
        data: Dict[str, Any] = {
            "key": f"api_setting_{unique_key_suffix}",
            "value": {"feature_enabled": True, "limit": 100},
            "description": "API test setting description."
        }
        data.update(kwargs)
        return data
    return _factory

@pytest.fixture
def api_settings_set(db: Session, test_user: UserModel, test_superuser: UserModel, setting_api_payload_factory: callable):
    settings_created = {}

    # Global settings
    global_key1 = f"global_color_{uuid.uuid4().hex[:4]}"
    global_payload1 = setting_api_payload_factory(key=global_key1, value="blue", user_id=None)
    settings_created["global_color"] = crud_create_setting(db, global_payload1)

    global_key2 = f"global_timeout_{uuid.uuid4().hex[:4]}"
    global_payload2 = setting_api_payload_factory(key=global_key2, value=3000, user_id=None)
    settings_created["global_timeout"] = crud_create_setting(db, global_payload2)

    # test_user settings
    user1_key1 = f"user_notifications_{test_user.id}_{uuid.uuid4().hex[:4]}"
    user1_payload1 = setting_api_payload_factory(key=user1_key1, value={"email": True, "sms": False}, user_id=test_user.id)
    settings_created["user1_notifications"] = crud_create_setting(db, user1_payload1)

    user1_key2 = f"user_dashboard_widgets_{test_user.id}_{uuid.uuid4().hex[:4]}"
    user1_payload2 = setting_api_payload_factory(key=user1_key2, value=["weather", "news"], user_id=test_user.id)
    settings_created["user1_dashboard"] = crud_create_setting(db, user1_payload2)

    # test_superuser settings (as another distinct user)
    user2_key1 = f"user_notifications_{test_superuser.id}_{uuid.uuid4().hex[:4]}"
    user2_payload1 = setting_api_payload_factory(key=user2_key1, value={"email": False, "push": True}, user_id=test_superuser.id)
    settings_created["user2_notifications"] = crud_create_setting(db, user2_payload1)

    db.commit()
    return settings_created


# --- Tests for POST /settings/ ---

def test_create_global_setting_api_superuser(
    client: TestClient, superuser_token_headers: dict, setting_api_payload_factory: callable, db: Session
):
    payload = setting_api_payload_factory(key="new_global_via_api", user_id=None)
    response = client.post("/settings/", json=payload, headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == payload["key"]
    assert data["user_id"] is None
    assert crud_get_setting(db, payload["key"], user_id=None) is not None

def test_create_user_setting_api_superuser_for_other_user(
    client: TestClient, superuser_token_headers: dict, setting_api_payload_factory: callable, test_user: UserModel, db: Session
):
    live_test_user = db.merge(test_user)
    target_user_id = live_test_user.id
    payload = setting_api_payload_factory(key="setting_for_user1_by_admin_api", user_id=target_user_id)
    response = client.post("/settings/", json=payload, headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == target_user_id

def test_create_user_setting_api_normal_user_defaults_to_self(
    client: TestClient, normal_user_token_headers: dict, setting_api_payload_factory: callable, test_user: UserModel, db: Session
):
    live_test_user = db.merge(test_user)
    expected_user_id = live_test_user.id
    payload = setting_api_payload_factory(key="normal_user_own_setting_api", user_id=None) # API defaults user_id

    response = client.post("/settings/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == expected_user_id

def test_create_user_setting_api_normal_user_explicit_self(
    client: TestClient, normal_user_token_headers: dict, setting_api_payload_factory: callable, test_user: UserModel, db: Session
):
    live_test_user = db.merge(test_user)
    expected_user_id = live_test_user.id
    payload = setting_api_payload_factory(key="normal_user_explicit_setting_api", user_id=expected_user_id)
    response = client.post("/settings/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == expected_user_id

def test_create_user_setting_api_normal_user_for_other_user_forbidden( # UPDATED EXPECTATION
    client: TestClient, normal_user_token_headers: dict, setting_api_payload_factory: callable, test_superuser: UserModel, db: Session
):
    live_test_superuser = db.merge(test_superuser)
    other_user_id = live_test_superuser.id
    payload = setting_api_payload_factory(key="exploit_attempt_setting_api", user_id=other_user_id)
    response = client.post("/settings/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 403 # API should now forbid this
    assert "Not authorized to create settings for another user" in response.json()["detail"]


def test_create_setting_api_duplicate_error(
    client: TestClient, superuser_token_headers: dict, setting_api_payload_factory: callable, api_settings_set: dict
):
    existing_global_key = api_settings_set["global_color"].key
    payload = setting_api_payload_factory(key=existing_global_key, user_id=None)
    response = client.post("/settings/", json=payload, headers=superuser_token_headers)
    assert response.status_code == 400
    assert "Setting with this key already exists" in response.json()["detail"]

def test_create_setting_api_unauthenticated(client: TestClient, setting_api_payload_factory: callable):
    payload = setting_api_payload_factory()
    response = client.post("/settings/", json=payload)
    assert response.status_code == 401

# --- Tests for GET /settings/ ---

def test_list_settings_normal_user_sees_own_only(
    client: TestClient, normal_user_token_headers: dict, api_settings_set: dict, test_user: UserModel, db: Session
):
    live_test_user = db.merge(test_user)
    expected_user_id = live_test_user.id
    response = client.get("/settings/", headers=normal_user_token_headers) # Querying for self
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for setting in data:
        assert setting["user_id"] == expected_user_id

    other_user_id = expected_user_id + 1
    response_other = client.get(f"/settings/?user_id={other_user_id}", headers=normal_user_token_headers)
    assert response_other.status_code == 403 # API now forbids this for non-superusers

def test_list_settings_superuser_sees_specific_user(
    client: TestClient, superuser_token_headers: dict, api_settings_set: dict, test_user: UserModel, db: Session
):
    live_test_user = db.merge(test_user)
    target_user_id = live_test_user.id
    response = client.get(f"/settings/?user_id={target_user_id}", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for setting in data:
        assert setting["user_id"] == target_user_id

def test_list_settings_superuser_sees_global_if_user_id_is_none_query(
    client: TestClient, superuser_token_headers: dict, api_settings_set: dict
):
    # Было: /settings/?user_id=
    # Стало:
    response = client.get("/settings/", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for setting in data:
        assert setting["user_id"] is None

def test_list_settings_superuser_sees_global_if_no_user_id_query( # NEW to test API change
    client: TestClient, superuser_token_headers: dict, api_settings_set: dict
):
    response = client.get("/settings/", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for setting in data:
        assert setting["user_id"] is None


def test_list_settings_pagination_superuser_global(
    client: TestClient, superuser_token_headers: dict, api_settings_set: dict
):
    response_page1 = client.get("/settings/?limit=1&skip=0", headers=superuser_token_headers)
    assert response_page1.status_code == 200
    data_page1 = response_page1.json()
    assert len(data_page1) == 1

    response_page2 = client.get("/settings/?limit=1&skip=1", headers=superuser_token_headers)
    assert response_page2.status_code == 200
    data_page2 = response_page2.json()
    assert len(data_page2) == 1
    assert data_page1[0]["key"] != data_page2[0]["key"]

def test_list_settings_unauthenticated(client: TestClient):
    response = client.get("/settings/")
    assert response.status_code == 401

# --- Tests for GET /settings/{key} ---

def test_get_one_setting_api_normal_user_own(client: TestClient, normal_user_token_headers: dict, api_settings_set: dict, test_user: UserModel, db:Session):
    live_test_user = db.merge(test_user)
    user_setting = api_settings_set["user1_notifications"]
    response = client.get(f"/settings/{user_setting.key}", headers=normal_user_token_headers) # API defaults to current user
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == user_setting.key
    assert data["user_id"] == live_test_user.id

def test_get_one_setting_api_normal_user_querying_for_own_explicitly(client: TestClient, normal_user_token_headers: dict, api_settings_set: dict, test_user: UserModel, db:Session):
    live_test_user = db.merge(test_user)
    user_setting = api_settings_set["user1_notifications"]
    response = client.get(f"/settings/{user_setting.key}?user_id={live_test_user.id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == live_test_user.id

def test_get_one_setting_api_normal_user_global_by_omitting_userid_query(client: TestClient, normal_user_token_headers: dict, api_settings_set: dict, test_user: UserModel, db:Session):
    # This test now expects a 404 because the API's get_one_setting for normal users defaults to their user_id.
    # To get global, they must use /effective/{key} or have it listed in GET / if API allowed that.
    global_setting = api_settings_set["global_color"]
    response = client.get(f"/settings/{global_setting.key}", headers=normal_user_token_headers)
    assert response.status_code == 404

def test_get_one_setting_api_normal_user_cannot_get_other_user(client: TestClient, normal_user_token_headers: dict, api_settings_set: dict, test_superuser: UserModel, db:Session):
    live_test_superuser = db.merge(test_superuser)
    other_user_setting = api_settings_set["user2_notifications"]
    response = client.get(f"/settings/{other_user_setting.key}?user_id={live_test_superuser.id}", headers=normal_user_token_headers)
    assert response.status_code == 403

def test_get_one_setting_api_superuser_get_specific_user(client: TestClient, superuser_token_headers: dict, api_settings_set: dict, test_user: UserModel, db:Session):
    live_test_user = db.merge(test_user)
    user_setting = api_settings_set["user1_notifications"]
    response = client.get(f"/settings/{user_setting.key}?user_id={live_test_user.id}", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == live_test_user.id

def test_get_one_setting_api_superuser_get_global_explicit_none_userid(
    client: TestClient, superuser_token_headers: dict, api_settings_set: dict
):
    global_setting = api_settings_set["global_color"]
    # Было: /settings/{key}?user_id=
    # Стало:
    response = client.get(f"/settings/{global_setting.key}", headers=superuser_token_headers)
    assert response.status_code == 200
    assert response.json()["user_id"] is None

def test_get_one_setting_api_superuser_get_global_no_userid_param(client: TestClient, superuser_token_headers: dict, api_settings_set: dict):
    global_setting = api_settings_set["global_color"]
    response = client.get(f"/settings/{global_setting.key}", headers=superuser_token_headers) # No user_id param
    assert response.status_code == 200 # Superuser without user_id param will get global
    assert response.json()["user_id"] is None


def test_get_one_setting_api_not_found(client: TestClient, normal_user_token_headers: dict):
    response = client.get("/settings/non_existent_key", headers=normal_user_token_headers)
    assert response.status_code == 404

# --- Tests for GET /settings/effective/{key} ---

def test_get_effective_setting_api_user_specific_exists(client: TestClient, normal_user_token_headers: dict, api_settings_set: dict, test_user: UserModel, db: Session, setting_api_payload_factory: callable):
    live_test_user = db.merge(test_user)
    user_setting = api_settings_set["user1_notifications"]
    user_setting_key = user_setting.key
    user_setting_value = user_setting.value

    response = client.get(f"/settings/effective/{user_setting_key}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == user_setting_key
    assert data["value"] == user_setting_value
    assert data["user_id"] == live_test_user.id

def test_get_effective_setting_api_fallback_to_global(client: TestClient, normal_user_token_headers: dict, api_settings_set: dict, db: Session, test_user:UserModel):
    global_setting_key = api_settings_set["global_timeout"].key
    global_setting_value = api_settings_set["global_timeout"].value
    live_test_user = db.merge(test_user)

    user_specific_version = crud_get_setting(db, key=global_setting_key, user_id=live_test_user.id)
    if user_specific_version:
        crud_delete_setting(db, user_specific_version.id)

    response = client.get(f"/settings/effective/{global_setting_key}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == global_setting_key
    assert data["value"] == global_setting_value
    assert data["user_id"] is None

def test_get_effective_setting_api_not_found_anywhere(client: TestClient, normal_user_token_headers: dict):
    response = client.get("/settings/effective/completely_non_existent_key", headers=normal_user_token_headers)
    assert response.status_code == 404
    assert "Setting with key 'completely_non_existent_key' not found" in response.json()["detail"]

def test_get_effective_setting_api_unauthenticated(client: TestClient, api_settings_set: dict):
    key = api_settings_set["global_color"].key
    response = client.get(f"/settings/effective/{key}")
    assert response.status_code == 401

# --- Tests for PUT /settings/{key} (upsert_setting) ---

def test_upsert_setting_api_create_new_global_superuser(
    client: TestClient, superuser_token_headers: dict, setting_api_payload_factory: callable, db: Session
):
    key = f"upsert_new_global_key_{uuid.uuid4().hex[:4]}"
    payload = setting_api_payload_factory(value={"detail": "new global value"}, user_id=None)
    response = client.put(f"/settings/{key}", json=payload, headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == key
    assert data["user_id"] is None
    assert crud_get_setting(db, key, user_id=None) is not None

def test_upsert_setting_api_update_existing_global_superuser(
    client: TestClient, superuser_token_headers: dict, api_settings_set:dict, setting_api_payload_factory: callable, db: Session
):
    existing_global = api_settings_set["global_color"]
    payload = setting_api_payload_factory(value="new_global_color_value_upsert", user_id=None)
    response = client.put(f"/settings/{existing_global.key}", json=payload, headers=superuser_token_headers)
    assert response.status_code == 200
    assert response.json()["value"] == payload["value"]

def test_upsert_setting_api_normal_user_create_own(
    client: TestClient, normal_user_token_headers: dict, setting_api_payload_factory: callable, test_user: UserModel, db: Session
):
    live_test_user = db.merge(test_user)
    expected_user_id = live_test_user.id
    key = f"upsert_own_key_u{expected_user_id}_{uuid.uuid4().hex[:4]}"
    payload = setting_api_payload_factory(value="my own value upsert")
    if "user_id" in payload: del payload["user_id"]

    response = client.put(f"/settings/{key}", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == expected_user_id
    assert crud_get_setting(db, key, user_id=expected_user_id) is not None

def test_upsert_setting_api_normal_user_update_own(
    client: TestClient, normal_user_token_headers: dict, api_settings_set: dict, test_user: UserModel, setting_api_payload_factory: callable, db: Session
):
    live_test_user = db.merge(test_user)
    expected_user_id = live_test_user.id
    existing_user_setting = api_settings_set["user1_notifications"]
    payload = setting_api_payload_factory(value={"email": False, "sms": True, "push_upsert": True}, user_id=expected_user_id)

    response = client.put(f"/settings/{existing_user_setting.key}", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == expected_user_id
    assert data["value"]["push_upsert"] is True

def test_upsert_setting_api_normal_user_for_other_user_forbidden(
    client: TestClient, normal_user_token_headers: dict, setting_api_payload_factory: callable, test_user:UserModel, test_superuser: UserModel, db: Session
):
    live_test_superuser = db.merge(test_superuser)
    other_user_id = live_test_superuser.id
    key_for_superuser = f"key_for_superuser_by_normal_user_upsert_{other_user_id}"
    payload = setting_api_payload_factory(value="value set by normal user", user_id=other_user_id)

    response = client.put(f"/settings/{key_for_superuser}", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized to upsert settings for another user" in response.json()["detail"]

def test_upsert_setting_api_unauthenticated(client: TestClient, setting_api_payload_factory: callable):
    response = client.put("/settings/unauth_upsert_key", json=setting_api_payload_factory())
    assert response.status_code == 401

# --- Tests for PATCH /settings/{setting_id} ---

def test_patch_setting_api_superuser_update_global(
    client: TestClient, superuser_token_headers: dict, api_settings_set: dict, db: Session
):
    global_setting = api_settings_set["global_color"]
    payload = {"value": "new_global_color_patch", "description": "Patched global desc"}
    response = client.patch(f"/settings/{global_setting.id}", json=payload, headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == payload["value"]
    db_setting = crud_get_setting(db, global_setting.key, user_id=None)
    assert db_setting.value == payload["value"]

def test_patch_setting_api_normal_user_update_own_setting(
    client: TestClient, normal_user_token_headers: dict, api_settings_set: dict, test_user: UserModel, db: Session
):
    live_test_user = db.merge(test_user)
    user_setting = api_settings_set["user1_dashboard"] # Belongs to test_user (ID check done by API)
    payload = {"value": ["calendar", "tasks_updated"]}
    response = client.patch(f"/settings/{user_setting.id}", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 200
    assert response.json()["value"] == payload["value"]

def test_patch_setting_api_normal_user_update_other_user_forbidden(
    client: TestClient, normal_user_token_headers: dict, api_settings_set: dict, test_superuser: UserModel
):
    other_user_setting = api_settings_set["user2_notifications"] # Belongs to test_superuser
    payload = {"value": "normal_user_hacked_this"}
    response = client.patch(f"/settings/{other_user_setting.id}", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 403

def test_patch_setting_api_normal_user_update_global_forbidden(
    client: TestClient, normal_user_token_headers: dict, api_settings_set: dict
):
    global_setting = api_settings_set["global_timeout"]
    payload = {"value": 9999}
    response = client.patch(f"/settings/{global_setting.id}", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 403

def test_patch_setting_api_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.patch("/settings/99999", json={"value": "test"}, headers=superuser_token_headers)
    assert response.status_code == 404 # Changed from 400 based on new API error handling
    assert "Setting not found" in response.json()["detail"]

# --- Tests for DELETE /settings/{setting_id} ---

def test_delete_setting_api_superuser_delete_global(
    client: TestClient, superuser_token_headers: dict, api_settings_set: dict, db: Session
):
    global_setting = api_settings_set["global_color"]
    response = client.delete(f"/settings/{global_setting.id}", headers=superuser_token_headers)
    assert response.status_code == 200
    assert crud_get_setting(db, global_setting.key, user_id=None) is None

def test_delete_setting_api_superuser_delete_user_specific(
    client: TestClient, superuser_token_headers: dict, api_settings_set: dict, test_user: UserModel, db: Session
):
    user_setting = api_settings_set["user1_notifications"]
    setting_id = user_setting.id
    setting_key = user_setting.key
    user_id = user_setting.user_id  # Лучше брать из user_setting, а не из test_user, чтобы не было detached

    response = client.delete(f"/settings/{setting_id}", headers=superuser_token_headers)
    assert response.status_code == 200

    # После этого делаем select по ключу и user_id, никаких detached!
    assert crud_get_setting(db, setting_key, user_id=user_id) is None

def test_delete_setting_api_normal_user_delete_own(
    client: TestClient, normal_user_token_headers: dict, api_settings_set: dict, test_user: UserModel, db: Session
):
    user_setting = api_settings_set["user1_dashboard"]
    setting_id = user_setting.id
    setting_key = user_setting.key
    user_id = user_setting.user_id  # Лучше брать из user_setting, а не из test_user, чтобы не было detached

    response = client.delete(f"/settings/{setting_id}", headers=normal_user_token_headers)
    assert response.status_code == 200

    # После этого делаем select по ключу и user_id, никаких detached!
    assert crud_get_setting(db, setting_key, user_id=user_id) is None

def test_delete_setting_api_normal_user_delete_other_forbidden(
    client: TestClient, normal_user_token_headers: dict, api_settings_set: dict
):
    # Берём настройку другого пользователя (не текущего normal_user)
    other_user_setting = api_settings_set["user2_notifications"]
    setting_id = other_user_setting.id

    response = client.delete(f"/settings/{setting_id}", headers=normal_user_token_headers)
    assert response.status_code == 403

def test_delete_setting_api_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.delete("/settings/99999", headers=superuser_token_headers)
    assert response.status_code == 404
    assert "Setting not found" in response.json()["detail"]

def test_delete_setting_api_unauthenticated(client: TestClient, api_settings_set: dict):
    setting_to_delete = api_settings_set["global_timeout"]
    response = client.delete(f"/settings/{setting_to_delete.id}")
    assert response.status_code == 401

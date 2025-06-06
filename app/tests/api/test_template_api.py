import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.settings import settings as app_settings
from app.models.user import User as UserModel
from app.models.template import Template as TemplateModel
from app.schemas.template import TemplateCreate, TemplateRead, TemplateShort # For type hints and validation
from app.crud.template import get_template as crud_get_template # For verifying after operations
# For clone test project verification
from app.models.project import Project as ProjectModel
from app.models.task import Task as TaskModel
from app.schemas.project import ProjectCreate as ProjectCreateSchema # For clone endpoint payload
from unittest.mock import patch # Required for patch
from app.tests.crud.test_project_crud import MOCKED_CUSTOM_FIELDS_SCHEMA # Required for patch
from datetime import date, timedelta, datetime, timezone # Ensure full datetime import

# --- Fixtures ---
@pytest.fixture
def template_api_payload_factory():
    def _template_payload(name_suffix: str = ""):
        name = f"API Template {uuid.uuid4().hex[:4]}{name_suffix}"
        return {
            "name": name,
            "description": "A template created via API tests.",
            "version": "1.0.0", # Use a simple, known-good version
            "structure": {"type": "project", "details": "some structured content"},
            "tags": ["api_test", "sample"],
            "is_private": False,
            "is_active": True
        }
    return _template_payload

# --- Tests for POST /templates/ ---
def test_create_template_api_success(
    client: TestClient, normal_user_token_headers: dict, template_api_payload_factory: callable, db: Session, test_user: UserModel
):
    payload = template_api_payload_factory()
    response = client.post("/templates/", json=payload, headers=normal_user_token_headers)

    if response.status_code != 201:
        print("Create template failed:", response.json())
    assert response.status_code == 201 # Created
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["author_id"] == test_user.id # Set by current_user
    assert data["structure"] == payload["structure"]
    assert data["version"] == payload["version"]
    assert data["is_active"] == payload["is_active"]
    assert data["is_private"] == payload["is_private"]
    assert "api_test" in data["tags"]

    # Verify in DB
    template_in_db = db.query(TemplateModel).filter(TemplateModel.id == data["id"]).first()
    assert template_in_db is not None
    assert template_in_db.name == payload["name"]
    assert template_in_db.author_id == test_user.id

def test_create_template_api_missing_name(
    client: TestClient, normal_user_token_headers: dict, template_api_payload_factory: callable
):
    payload = template_api_payload_factory()
    payload["name"] = ""
    response = client.post("/templates/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 400 # ProjectValidationError from CRUD, mapped to 400
    assert "Template name is required" in response.json()["detail"]

def test_create_template_api_missing_structure(
    client: TestClient, normal_user_token_headers: dict, template_api_payload_factory: callable
):
    payload = template_api_payload_factory()
    del payload["structure"] # Pydantic validation error
    response = client.post("/templates/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 422 # Pydantic validation for missing required field

def test_create_template_api_duplicate_name(
    client: TestClient, normal_user_token_headers: dict, template_api_payload_factory: callable, db: Session
):
    payload = template_api_payload_factory(name_suffix="_dup")
    # Create first template
    client.post("/templates/", json=payload, headers=normal_user_token_headers).raise_for_status()

    # Attempt to create again
    response = client.post("/templates/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 400 # DuplicateTemplateName from CRUD, mapped to 400
    assert f"Template with name '{payload['name']}' already exists" in response.json()["detail"]

def test_create_template_api_unauthenticated(client: TestClient, template_api_payload_factory: callable):
    payload = template_api_payload_factory()
    response = client.post("/templates/", json=payload) # No headers
    assert response.status_code == 401

# --- Fixture for a set of templates for API list tests ---
@pytest.fixture
def api_template_set(db: Session, test_user: UserModel, test_superuser: UserModel, template_api_payload_factory: callable):
    from app.crud.template import create_template as crud_create_template
    from app.core.exceptions import DuplicateProjectName # Actually DuplicateTemplateName
    # datetime, timezone, uuid are now imported at module level

    templates_data = [
        # test_user's templates
        template_api_payload_factory(name_suffix="_user_priv_active") | {"is_private": True, "is_active": True, "tags": ["user", "report"], "subscription_level": "free"},
        template_api_payload_factory(name_suffix="_user_pub_active")  | {"is_private": False, "is_active": True, "tags": ["user", "public"], "subscription_level": "pro"},
        template_api_payload_factory(name_suffix="_user_priv_inactive")| {"is_private": True, "is_active": False, "tags": ["user", "old"]},
        template_api_payload_factory(name_suffix="_user_pub_deleted") | {"is_private": False, "is_active": True, "is_deleted": True}, # Will be soft-deleted
        # test_superuser's templates
        template_api_payload_factory(name_suffix="_admin_priv_active")| {"is_private": True, "is_active": True, "tags": ["admin", "config"], "subscription_level": "pro"},
        template_api_payload_factory(name_suffix="_admin_pub_active") | {"is_private": False, "is_active": True, "tags": ["admin", "global"]},
        template_api_payload_factory(name_suffix="_admin_pub_inact_del")| {"is_private": False, "is_active": False, "is_deleted": True}, # Soft-deleted and inactive
    ]

    created_templates = []
    author_map = { test_user.id: test_user, test_superuser.id: test_superuser }

    for i, data in enumerate(templates_data):
        author = test_user if i < 4 else test_superuser # Crude author assignment for variety
        is_del = data.pop("is_deleted", False)

        # Ensure unique name if factory doesn't guarantee it fully with suffix alone
        data["name"] = f"{data['name']}_{uuid.uuid4().hex[:3]}"

        try:
            tmpl = crud_create_template(db, data, author_id=author.id)
            if is_del:
                tmpl.is_deleted = True
                tmpl.deleted_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(tmpl)
            created_templates.append(tmpl)
        except DuplicateProjectName: # Should be DuplicateTemplateName
            existing = db.query(TemplateModel).filter(TemplateModel.name == data['name']).first()
            if existing: created_templates.append(existing)
            else: raise
    return created_templates

# --- Tests for GET /templates/ (list_templates) ---
def test_list_templates_normal_user_default(client: TestClient, normal_user_token_headers: dict, api_template_set, test_user: UserModel):
    response = client.get("/templates/", headers=normal_user_token_headers)
    assert response.status_code == 200
    templates = response.json()
    # Expected: UserTemplate PrivateActive, UserTemplate PublicActive, AdminTemplate PublicActive (active, non-deleted, visible)
    assert len(templates) == 3
    for t in templates:
        assert t["is_active"] is True
        # is_deleted is not in TemplateShort by default, but crud get_all_templates filters it
        if t["is_private"]:
            assert t["author_id"] == test_user.id

def test_list_templates_superuser_default(client: TestClient, superuser_token_headers: dict, api_template_set):
    response = client.get("/templates/", headers=superuser_token_headers)
    assert response.status_code == 200
    templates = response.json()
    # Expected: All active, non-deleted templates (User PrivAct, User PubAct, Admin PrivAct, Admin PubAct) = 4
    assert len(templates) == 4

def test_list_templates_superuser_show_archived_no_active_filter(client: TestClient, superuser_token_headers: dict, api_template_set):
    response = client.get("/templates/?show_archived=true", headers=superuser_token_headers) # Changed to show_archived
    assert response.status_code == 200
    templates = response.json()
    # Superuser, include_deleted=True, is_active not specified => should get all 7 (active/inactive, deleted/non-deleted)
    # because CRUD's get_all_templates, when is_active is not in filters AND (superuser AND include_deleted), does not filter by active status.
    assert len(templates) == 7

def test_list_templates_superuser_show_archived_and_filter_inactive(client: TestClient, superuser_token_headers: dict, api_template_set):
    response = client.get("/templates/?show_archived=true&is_active=false", headers=superuser_token_headers) # Changed to show_archived
    assert response.status_code == 200
    templates = response.json()
    # UserTemplate PrivateInactive, AdminTemplate PublicInactiveDeleted
    assert len(templates) == 2
    for t in templates:
        assert t["is_active"] is False

def test_list_templates_filter_tag_normal_user(client: TestClient, normal_user_token_headers: dict, api_template_set, test_user: UserModel):
    response = client.get("/templates/?tag=user", headers=normal_user_token_headers)
    assert response.status_code == 200
    templates = response.json()
    # UserTemplate PrivateActive, UserTemplate PublicActive (both have 'user' tag and are active/visible)
    assert len(templates) == 2

# --- Tests for GET /templates/{template_id} ---
def test_api_get_one_template_author_success(client: TestClient, normal_user_token_headers: dict, api_template_set, test_user: UserModel):
    # Find a public active template by test_user
    template_id = None
    expected_name = ""
    for t in api_template_set:
        # Ensure author_id matches and it's a public, active, non-deleted template created by test_user
        if t.author_id == test_user.id and not t.is_private and t.is_active and not t.is_deleted:
            template_id = t.id
            expected_name = t.name
            break
    assert template_id is not None, "No suitable public active template found for test_user"

    response = client.get(f"/templates/{template_id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == template_id
    assert data["name"] == expected_name
    assert data["author_id"] == test_user.id

def test_api_get_one_private_template_author_success(client: TestClient, normal_user_token_headers: dict, api_template_set, test_user: UserModel):
    template_id = None
    for t in api_template_set:
        if t.author_id == test_user.id and t.is_private and t.is_active and not t.is_deleted:
            template_id = t.id
            break
    assert template_id is not None, "No suitable private active template found for test_user"

    response = client.get(f"/templates/{template_id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    assert response.json()["id"] == template_id

def test_api_get_one_private_template_other_user_forbidden(client: TestClient, normal_user_token_headers: dict, api_template_set, test_superuser: UserModel):
    template_id = None # Find a private template by test_superuser
    for t in api_template_set:
        if t.author_id == test_superuser.id and t.is_private and t.is_active and not t.is_deleted:
            template_id = t.id
            break
    assert template_id is not None, "No suitable private active template found for test_superuser"

    response = client.get(f"/templates/{template_id}", headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized to access this private template" in response.json()["detail"]

def test_api_get_one_template_superuser_can_access_private(client: TestClient, superuser_token_headers: dict, api_template_set, test_user: UserModel):
    template_id = None # Find a private template by test_user
    for t in api_template_set:
        if t.author_id == test_user.id and t.is_private and t.is_active and not t.is_deleted:
            template_id = t.id
            break
    assert template_id is not None, "No suitable private template found for test_user for superuser access test"

    response = client.get(f"/templates/{template_id}", headers=superuser_token_headers)
    assert response.status_code == 200
    assert response.json()["id"] == template_id

def test_api_get_one_template_not_found(client: TestClient, normal_user_token_headers: dict):
    response = client.get("/templates/99999", headers=normal_user_token_headers)
    assert response.status_code == 404

def test_api_get_one_template_soft_deleted_returns_404(client: TestClient, normal_user_token_headers: dict, api_template_set, test_user: UserModel):
    # Find a soft-deleted template by test_user
    template_id = None
    for t in api_template_set:
        if t.author_id == test_user.id and t.is_deleted and t.is_private is False: # Public but deleted
            template_id = t.id
            break
    assert template_id is not None, "No suitable soft-deleted public template found for test_user"

    response = client.get(f"/templates/{template_id}", headers=normal_user_token_headers)
    assert response.status_code == 404 # get_template in API raises 404 if not found (which includes deleted ones by default)
    assert "Template not found" in response.json()["detail"]


# --- Tests for PATCH /templates/{template_id} (update) ---

def test_api_update_template_success_author(
    client: TestClient, normal_user_token_headers: dict, api_template_set: list[TemplateModel], test_user: UserModel, db: Session
):
    template_to_update = None
    for t in api_template_set:
        if t.author_id == test_user.id and not t.is_deleted: # Find a non-deleted template by test_user
            template_to_update = db.query(TemplateModel).get(t.id) # Re-fetch to ensure it's attach to session
            break
    assert template_to_update is not None, "No suitable template found for test_user to update"

    update_payload = {
        "name": f"Updated Name {uuid.uuid4().hex[:4]}",
        "description": "Updated description via API.",
        "tags": ["updated", "api_patch"],
        "is_active": not template_to_update.is_active,
        "is_private": not template_to_update.is_private,
        "structure": {"type": "project", "details": "updated structure content"},
        "version": "1.1.0",
        # "custom_fields": {"new_key": "new_value"} # Add if custom fields are applicable
    }

    response = client.patch(f"/templates/{template_to_update.id}", json=update_payload, headers=normal_user_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_payload["name"]
    assert data["description"] == update_payload["description"]
    assert sorted(data["tags"]) == sorted(update_payload["tags"])
    assert data["is_active"] == update_payload["is_active"]
    assert data["is_private"] == update_payload["is_private"]
    assert data["structure"] == update_payload["structure"]
    assert data["version"] == update_payload["version"]
    assert data["author_id"] == test_user.id # Author should not change

    # Verify in DB
    template_in_db = db.query(TemplateModel).get(template_to_update.id)
    assert template_in_db is not None
    assert template_in_db.name == update_payload["name"]
    assert template_in_db.description == update_payload["description"]
    assert sorted(template_in_db.tags) == sorted(update_payload["tags"])
    assert template_in_db.is_active == update_payload["is_active"]
    assert template_in_db.is_private == update_payload["is_private"]
    assert template_in_db.structure == update_payload["structure"]
    assert template_in_db.version == update_payload["version"]


def test_api_update_template_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_template_set: list[TemplateModel], test_user: UserModel, db: Session
):
    template_to_update = None
    for t in api_template_set:
        if t.author_id == test_user.id and not t.is_deleted: # Find a template by normal_user
            template_to_update = db.query(TemplateModel).get(t.id)
            break
    assert template_to_update is not None, "No suitable template by test_user found for superuser to update"

    update_payload = {"description": "Superuser updated this template."}
    response = client.patch(f"/templates/{template_to_update.id}", json=update_payload, headers=superuser_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == update_payload["description"]
    assert data["author_id"] == test_user.id # Author should not change

    # Verify in DB
    template_in_db = db.query(TemplateModel).get(template_to_update.id)
    assert template_in_db is not None
    assert template_in_db.description == update_payload["description"]


def test_api_update_template_partial_success(
    client: TestClient, normal_user_token_headers: dict, api_template_set: list[TemplateModel], test_user: UserModel, db: Session
):
    template_to_update = None
    original_name = ""
    for t in api_template_set:
        if t.author_id == test_user.id and not t.is_deleted:
            template_to_update = db.query(TemplateModel).get(t.id)
            original_name = template_to_update.name
            break
    assert template_to_update is not None, "No suitable template found for partial update test"

    update_payload = {"is_active": not template_to_update.is_active}
    response = client.patch(f"/templates/{template_to_update.id}", json=update_payload, headers=normal_user_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] == update_payload["is_active"]
    assert data["name"] == original_name # Name should not have changed

    # Verify in DB
    template_in_db = db.query(TemplateModel).get(template_to_update.id)
    assert template_in_db is not None
    assert template_in_db.is_active == update_payload["is_active"]
    assert template_in_db.name == original_name


def test_api_update_template_forbidden_other_user(
    client: TestClient, normal_user_token_headers: dict, api_template_set: list[TemplateModel], test_superuser: UserModel, db: Session
):
    template_to_update = None
    for t in api_template_set:
        if t.author_id == test_superuser.id and not t.is_deleted: # Find a template by superuser
            template_to_update = db.query(TemplateModel).get(t.id)
            break
    assert template_to_update is not None, "No suitable template by superuser found for forbidden test"

    update_payload = {"description": "Attempted update by another user."}
    response = client.patch(f"/templates/{template_to_update.id}", json=update_payload, headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized to update this template" in response.json()["detail"]


def test_api_update_template_not_found(client: TestClient, superuser_token_headers: dict):
    non_existent_id = uuid.uuid4().int & (1<<30)-1 # A large random int ID
    update_payload = {"description": "Doesn't matter"}
    response = client.patch(f"/templates/{non_existent_id}", json=update_payload, headers=superuser_token_headers)
    assert response.status_code == 404
    assert "Template not found" in response.json()["detail"]


def test_api_update_template_validation_error_empty_name(
    client: TestClient, superuser_token_headers: dict, api_template_set: list[TemplateModel], test_superuser: UserModel, db: Session
):
    template_to_update = None
    for t in api_template_set:
        if t.author_id == test_superuser.id and not t.is_deleted: # Superuser updating their own template
            template_to_update = db.query(TemplateModel).get(t.id)
            break
    assert template_to_update is not None, "No suitable template found for validation error test"

    update_payload = {"name": ""}
    response = client.patch(f"/templates/{template_to_update.id}", json=update_payload, headers=superuser_token_headers)
    assert response.status_code == 400 # TemplateValidationError from CRUD
    assert "Template name cannot be empty." in response.json()["detail"]


def test_api_update_template_unauthenticated(client: TestClient, api_template_set: list[TemplateModel]):
    template_to_update = None
    for t in api_template_set: # Find any template
        if not t.is_deleted:
            template_to_update = t # No need to fetch from db, just need ID
            break
    assert template_to_update is not None, "No template found for unauthenticated test"

    update_payload = {"description": "Unauthenticated update attempt"}
    response = client.patch(f"/templates/{template_to_update.id}", json=update_payload) # No headers
    assert response.status_code == 401


# --- Tests for DELETE /templates/{template_id} (soft delete) ---

def test_api_delete_template_success_author(
    client: TestClient, normal_user_token_headers: dict, api_template_set: list[TemplateModel], test_user: UserModel, db: Session
):
    template_to_delete = None
    for t in api_template_set:
        if t.author_id == test_user.id and not t.is_deleted:
            template_to_delete = db.query(TemplateModel).get(t.id) # Re-fetch for session
            break
    assert template_to_delete is not None, "No suitable active template found for test_user to delete"

    response = client.delete(f"/templates/{template_to_delete.id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == template_to_delete.id
    assert "Template archived (soft-deleted)" in data["detail"]

    # Verify in DB
    deleted_template_in_db = db.query(TemplateModel).get(template_to_delete.id)
    assert deleted_template_in_db is not None
    assert deleted_template_in_db.is_deleted is True
    assert deleted_template_in_db.deleted_at is not None
    assert deleted_template_in_db.is_active is False # Soft delete also deactivates

def test_api_delete_template_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_template_set: list[TemplateModel], test_user: UserModel, db: Session
):
    template_to_delete = None
    for t in api_template_set:
        if t.author_id == test_user.id and not t.is_deleted: # Template owned by normal_user
            template_to_delete = db.query(TemplateModel).get(t.id)
            break
    assert template_to_delete is not None, "No suitable active template by test_user found for superuser to delete"

    response = client.delete(f"/templates/{template_to_delete.id}", headers=superuser_token_headers)
    assert response.status_code == 200

    deleted_template_in_db = db.query(TemplateModel).get(template_to_delete.id)
    assert deleted_template_in_db.is_deleted is True

def test_api_delete_template_forbidden_other_user(
    client: TestClient, normal_user_token_headers: dict, api_template_set: list[TemplateModel], test_superuser: UserModel, db: Session
):
    template_to_delete = None
    for t in api_template_set:
        if t.author_id == test_superuser.id and not t.is_deleted: # Template owned by superuser
            template_to_delete = db.query(TemplateModel).get(t.id)
            break
    assert template_to_delete is not None, "No suitable active template by superuser found for forbidden delete test"

    response = client.delete(f"/templates/{template_to_delete.id}", headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized to delete this template" in response.json()["detail"]

def test_api_delete_template_not_found(client: TestClient, superuser_token_headers: dict):
    non_existent_id = uuid.uuid4().int & (1<<30)-1
    response = client.delete(f"/templates/{non_existent_id}", headers=superuser_token_headers)
    assert response.status_code == 404
    assert "Template not found" in response.json()["detail"]

def test_api_delete_template_already_deleted(
    client: TestClient, superuser_token_headers: dict, api_template_set: list[TemplateModel], test_superuser: UserModel, db: Session
):
    template_to_delete = None
    # Find an already deleted template by superuser from the fixture setup
    for t_fixture_data in api_template_set:
        if t_fixture_data.author_id == test_superuser.id and t_fixture_data.is_deleted:
            template_to_delete = db.query(TemplateModel).get(t_fixture_data.id)
            break
    assert template_to_delete is not None, "No already deleted template found for superuser for this test"
    assert template_to_delete.is_deleted is True # Pre-condition

    response = client.delete(f"/templates/{template_to_delete.id}", headers=superuser_token_headers)
    # The API calls crud_template.get_template first (without include_deleted=True by default).
    # If it's already soft-deleted, get_template will raise SpecificTemplateNotFoundError.
    # So the API should return 404.
    assert response.status_code == 404
    assert "Template not found" in response.json()["detail"]
    # If the behavior was to return 200 and a message "already deleted", this test would change.
    # Current API's delete_one_template first calls get_template (default include_deleted=False)
    # then checks permissions, then calls crud_template.soft_delete_template.
    # crud_template.soft_delete_template itself fetches with include_deleted=True and if already deleted,
    # it logs and returns the template. But the API would have failed at get_template first.

def test_api_delete_template_unauthenticated(client: TestClient, api_template_set: list[TemplateModel]):
    template_to_delete = None
    for t in api_template_set:
        if not t.is_deleted:
            template_to_delete = t
            break
    assert template_to_delete is not None
    response = client.delete(f"/templates/{template_to_delete.id}") # No headers
    assert response.status_code == 401


# --- Tests for POST /templates/{template_id}/restore ---

def test_api_restore_template_success_author(
    client: TestClient, normal_user_token_headers: dict, api_template_set: list[TemplateModel], test_user: UserModel, db: Session
):
    # Find a soft-deleted template by test_user
    template_to_restore = None
    for t_fixture in api_template_set:
        if t_fixture.author_id == test_user.id and t_fixture.is_deleted:
            # Re-fetch to ensure it's a fresh object for this session and to confirm current state
            template_to_restore = db.query(TemplateModel).filter(TemplateModel.id == t_fixture.id, TemplateModel.is_deleted == True).first()
            if template_to_restore:
                 # Ensure it was made inactive upon soft deletion by the fixture or previous tests
                template_to_restore.is_active = False
                db.commit()
                db.refresh(template_to_restore)
                break
    assert template_to_restore is not None, "No suitable soft-deleted template found for test_user to restore"
    original_is_active_state = template_to_restore.is_active # Should be False

    response = client.post(f"/templates/{template_to_restore.id}/restore", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == template_to_restore.id
    assert data["is_deleted"] is False
    assert data["deleted_at"] is None
    assert data["is_active"] == original_is_active_state # Restore doesn't auto-reactivate

    # Verify in DB
    restored_template_in_db = db.query(TemplateModel).get(template_to_restore.id)
    assert restored_template_in_db is not None
    assert restored_template_in_db.is_deleted is False
    assert restored_template_in_db.deleted_at is None
    assert restored_template_in_db.is_active == original_is_active_state

def test_api_restore_template_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_template_set: list[TemplateModel], test_user: UserModel, db: Session
):
    template_to_restore = None
    for t_fixture in api_template_set:
        if t_fixture.author_id == test_user.id and t_fixture.is_deleted: # Owned by normal_user
            template_to_restore = db.query(TemplateModel).filter(TemplateModel.id == t_fixture.id, TemplateModel.is_deleted == True).first()
            if template_to_restore:
                template_to_restore.is_active = False # Ensure inactive
                db.commit()
                db.refresh(template_to_restore)
                break
    assert template_to_restore is not None, "No suitable soft-deleted template by test_user found for superuser to restore"

    response = client.post(f"/templates/{template_to_restore.id}/restore", headers=superuser_token_headers)
    assert response.status_code == 200

    restored_template_in_db = db.query(TemplateModel).get(template_to_restore.id)
    assert restored_template_in_db.is_deleted is False

def test_api_restore_template_forbidden_other_user(
    client: TestClient, normal_user_token_headers: dict, api_template_set: list[TemplateModel], test_superuser: UserModel, db: Session
):
    template_to_restore = None
    for t_fixture in api_template_set:
        if t_fixture.author_id == test_superuser.id and t_fixture.is_deleted: # Owned by superuser
            template_to_restore = db.query(TemplateModel).filter(TemplateModel.id == t_fixture.id, TemplateModel.is_deleted == True).first()
            if template_to_restore: break
    assert template_to_restore is not None, "No suitable soft-deleted template by superuser found for forbidden restore test"

    response = client.post(f"/templates/{template_to_restore.id}/restore", headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized to restore this template" in response.json()["detail"]

def test_api_restore_template_not_found(client: TestClient, superuser_token_headers: dict):
    non_existent_id = uuid.uuid4().int & (1<<30)-1
    response = client.post(f"/templates/{non_existent_id}/restore", headers=superuser_token_headers)
    assert response.status_code == 404
    # Detail message comes from crud_template.get_template(include_deleted=True)
    assert f"Template with id={non_existent_id} not found" in response.json()["detail"]


def test_api_restore_template_not_deleted(
    client: TestClient, superuser_token_headers: dict, api_template_set: list[TemplateModel], test_superuser: UserModel, db: Session
):
    template_to_restore = None
    for t_fixture in api_template_set: # Find an active template by superuser
        if t_fixture.author_id == test_superuser.id and not t_fixture.is_deleted:
            template_to_restore = db.query(TemplateModel).get(t_fixture.id)
            break
    assert template_to_restore is not None, "No active template found for superuser for this test"
    assert template_to_restore.is_deleted is False # Pre-condition

    response = client.post(f"/templates/{template_to_restore.id}/restore", headers=superuser_token_headers)
    assert response.status_code == 400 # TemplateValidationError from CRUD
    assert f"Template '{template_to_restore.name}' (ID: {template_to_restore.id}) is not deleted. No action taken." in response.json()["detail"]

def test_api_restore_template_unauthenticated(client: TestClient, api_template_set: list[TemplateModel], db:Session):
    template_to_restore = None
    for t in api_template_set:
        if t.is_deleted: # Find any deleted template
            template_to_restore = db.query(TemplateModel).get(t.id)
            if template_to_restore: break
    assert template_to_restore is not None, "No deleted template found for unauthenticated restore test"

    response = client.post(f"/templates/{template_to_restore.id}/restore") # No headers
    assert response.status_code == 401


# --- Tests for POST /templates/{template_id}/clone ---

@pytest.fixture
def template_for_cloning_api(db: Session, test_user: UserModel, template_api_payload_factory) -> TemplateModel:
    """Creates a simple template with a defined structure including tasks, owned by test_user."""
    from app.crud.template import create_template as crud_create_template
    payload = template_api_payload_factory(name_suffix="_clonable_api")
    payload["structure"] = {
        "description": "Project description from template.",
        "tasks": [
            {"title": "Cloned Task 1", "description": "Detail for task 1", "status": "todo", "priority": 1},
            {"title": "Cloned Task 2", "description": "Detail for task 2", "deadline": "2025-12-31"}
        ]
    }
    template = crud_create_template(db, payload, author_id=test_user.id)
    return template

def test_api_clone_template_success_normal_user_public_template(
    client: TestClient, normal_user_token_headers: dict, db: Session, test_user: UserModel,
    api_template_set: list[TemplateModel], template_api_payload_factory # To get a public template not owned by test_user
):
    # Try to get IDs from fixtures immediately. If this fails, the fixture itself is providing a detached object.
    cloning_user_id = test_user.id

    # Find a public, active, non-deleted template NOT authored by test_user (e.g. by superuser)
    source_template = None
    for t_fixture_item in api_template_set: # Use a different variable name to avoid confusion
        # Accessing t_fixture_item.author_id should be fine as it's from a list of ORM objects.
        # The problem is test_user.id if test_user is detached.
        if t_fixture_item.author_id != cloning_user_id and not t_fixture_item.is_private and t_fixture_item.is_active and not t_fixture_item.is_deleted:
            source_template = db.query(TemplateModel).get(t_fixture_item.id) # Fetch for session
            # Add some tasks to its structure for comprehensive testing if not already present
            if not source_template.structure.get("tasks"):
                source_template.structure = {
                    **source_template.structure,
                    "tasks": [{"title": "Task from public template", "description": "A task"}]
                }
                db.commit()
                db.refresh(source_template)
            break
    assert source_template is not None, "No suitable public template found for cloning test"

    project_payload = {
        "name": f"Cloned Project {uuid.uuid4().hex[:4]} from public template",
        "description": "Optional new project description."
    }
    response = client.post(f"/templates/{source_template.id}/clone", json=project_payload, headers=normal_user_token_headers)

    assert response.status_code == 200 # API uses ProjectRead which is 200 OK by default for POST if no status_code specified
    cloned_project_data = response.json()
    assert cloned_project_data["name"] == project_payload["name"]
    assert cloned_project_data["author_id"] == cloning_user_id # Cloned project owned by current user
    assert cloned_project_data["description"] == project_payload["description"] # Overridden

    # Verify project and tasks in DB
    project_in_db = db.query(ProjectModel).filter(ProjectModel.id == cloned_project_data["id"]).first()
    assert project_in_db is not None
    # Query tasks separately as there's no direct 'tasks' relationship attribute on ProjectModel for selectinload
    tasks_in_db = db.query(TaskModel).filter(TaskModel.project_id == project_in_db.id).all()
    assert len(tasks_in_db) > 0 # Tasks should have been cloned from source_template's updated structure
    assert tasks_in_db[0].title == "Task from public template"


def test_api_clone_template_success_author_private_template(
    client: TestClient, normal_user_token_headers: dict, db: Session, test_user: UserModel, template_for_cloning_api: TemplateModel
):
    cloning_user_id = test_user.id
    # Merge template_for_cloning_api as it might be modified (is_private)
    # and then used in an API call that involves a different session.
    source_template = db.merge(template_for_cloning_api)
    # This template is private by default if not specified, owned by test_user
    # Make it explicitly private for clarity if default changes
    if not source_template.is_private:
        source_template.is_private = True
        db.commit()
        db.refresh(source_template)

    project_payload = {"name": f"Cloned Project {uuid.uuid4().hex[:4]} from own private template"}
    # Description will come from template structure if not provided here

    response = client.post(f"/templates/{source_template.id}/clone", json=project_payload, headers=normal_user_token_headers)
    assert response.status_code == 200
    cloned_project_data = response.json()
    assert cloned_project_data["name"] == project_payload["name"]
    assert cloned_project_data["author_id"] == cloning_user_id
    assert cloned_project_data["description"] == source_template.structure["description"] # From template

    project_in_db = db.query(ProjectModel).filter(ProjectModel.id == cloned_project_data["id"]).first()
    assert project_in_db is not None
    # Query tasks separately
    tasks_in_db = db.query(TaskModel).filter(TaskModel.project_id == project_in_db.id).all()
    assert len(tasks_in_db) == 2
    assert tasks_in_db[0].title == "Cloned Task 1"
    assert tasks_in_db[1].title == "Cloned Task 2"

def test_api_clone_template_success_superuser_other_private_template(
    client: TestClient, superuser_token_headers: dict, db: Session, test_user: UserModel, test_superuser: UserModel, template_for_cloning_api: TemplateModel
):
    cloning_superuser_id = test_superuser.id
    # template_for_cloning_api is owned by test_user. Superuser (identified by token) will clone it.
    # Merge template_for_cloning_api as it might be modified (is_private)
    source_template = db.merge(template_for_cloning_api)

    if not source_template.is_private: # Ensure it's private
        source_template.is_private = True
        db.commit()
        db.refresh(source_template)

    project_payload = {"name": f"Superuser Cloned Project {uuid.uuid4().hex[:4]}"}
    response = client.post(f"/templates/{source_template.id}/clone", json=project_payload, headers=superuser_token_headers)
    assert response.status_code == 200
    cloned_project_data = response.json()
    assert cloned_project_data["author_id"] == cloning_superuser_id # Project owned by superuser

def test_api_clone_template_forbidden_other_user_private_template(
    client: TestClient, normal_user_token_headers: dict, db: Session, test_user: UserModel, test_superuser: UserModel,
    template_api_payload_factory: callable
):
    # Create a private template owned by test_superuser
    from app.crud.template import create_template as crud_create_template
    private_payload = template_api_payload_factory("_priv_by_super")
    private_payload["is_private"] = True
    private_template_by_superuser = crud_create_template(db, private_payload, author_id=test_superuser.id)

    project_payload = {"name": "Attempted Clone Project"}
    response = client.post(f"/templates/{private_template_by_superuser.id}/clone", json=project_payload, headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized to clone this private template" in response.json()["detail"]

def test_api_clone_template_source_not_found(client: TestClient, normal_user_token_headers: dict):
    non_existent_id = uuid.uuid4().int & (1<<30)-1
    project_payload = {"name": "Cloning non-existent template"}
    response = client.post(f"/templates/{non_existent_id}/clone", json=project_payload, headers=normal_user_token_headers)
    assert response.status_code == 404
    assert "Template not found" in response.json()["detail"] # From get_template in API

def test_api_clone_template_project_validation_error(
    client: TestClient, normal_user_token_headers: dict, template_for_cloning_api: TemplateModel
):
    project_payload = {"name": ""} # Invalid project name
    response = client.post(f"/templates/{template_for_cloning_api.id}/clone", json=project_payload, headers=normal_user_token_headers)
    assert response.status_code == 400 # Should be DuplicateTemplateName or ProjectValidationError from project creation
    # The specific error can vary, let's check for a common part of project validation
    assert "Project name is required" in response.json()["detail"] # Or similar from project CRUD

import pytest
import pytest
import uuid # For unique names in fixture
from unittest.mock import patch, MagicMock # Added MagicMock for more versatile mocking if needed
from http import HTTPStatus # Added HTTPStatus
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.settings import settings as app_settings # For API prefix if used, though not currently
from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.schemas.project import ProjectCreate, ProjectRead # Assuming ProjectRead for responses
from datetime import date, timedelta, datetime
from app.tests.crud.test_project_crud import MOCKED_CUSTOM_FIELDS_SCHEMA # Import for tests

# Basic Project API tests

@pytest.fixture
def project_api_data(test_user: UserModel):
    return {
        "name": f"API Test Project {uuid.uuid4().hex[:6]}",
        "description": "Project created via API test.",
        "author_id": test_user.id, # Will be overridden by current_user in endpoint
        "project_status": "active",
        "deadline": (date.today() + timedelta(days=30)).isoformat(),
        "priority": 1,
        "tags": ["api", "test"],
        "custom_fields": {}
    }

def test_create_project_api_success_as_superuser(client: TestClient, superuser_token_headers: dict, project_api_data: dict, db: Session):
    # Remove author_id as it's set by current_user in the endpoint
    project_api_data.pop("author_id", None)

    response = client.post("/projects/", json=project_api_data, headers=superuser_token_headers)

    assert response.status_code == 200 # Assuming 200 for successful creation
    data = response.json()
    assert data["name"] == project_api_data["name"]
    assert data["description"] == project_api_data["description"]
    assert data["project_status"] == project_api_data["project_status"]
    assert data["deadline"] == project_api_data["deadline"]
    assert data["priority"] == project_api_data["priority"]
    assert "id" in data

    # Verify in DB
    project_in_db = db.query(ProjectModel).filter(ProjectModel.id == data["id"]).first()
    assert project_in_db is not None
    assert project_in_db.name == project_api_data["name"]
    # Note: author_id will be set to the user from superuser_token_headers

def test_create_project_api_forbidden_for_normal_user(client: TestClient, normal_user_token_headers: dict, project_api_data: dict):
    project_api_data.pop("author_id", None)
    response = client.post("/projects/", json=project_api_data, headers=normal_user_token_headers)
    assert response.status_code == 403 # Forbidden for normal user

def test_create_project_api_missing_name_as_superuser(client: TestClient, superuser_token_headers: dict, project_api_data: dict):
    data = project_api_data.copy()
    data.pop("author_id", None)
    data["name"] = ""
    response = client.post("/projects/", json=data, headers=superuser_token_headers)
    # Based on CRUD, create_project raises ProjectValidationError which is mapped to 400 by API
    # However, Pydantic UserCreate might catch empty name first if min_length=1 for name.
    # Assuming ProjectValidationError from CRUD is the primary check here for empty string after strip.
    # The API maps ProjectValidationError to 400.
    assert response.status_code == 400
    assert "Project name is required" in response.json()["detail"]


def test_create_project_api_past_deadline_as_superuser(client: TestClient, superuser_token_headers: dict, project_api_data: dict):
    data = project_api_data.copy()
    data.pop("author_id", None)
    data["name"] = f"API Past Deadline {uuid.uuid4().hex[:4]}" # Ensure unique name
    data["deadline"] = (date.today() - timedelta(days=1)).isoformat()
    response = client.post("/projects/", json=data, headers=superuser_token_headers)
    assert response.status_code == 400 # Based on ProjectValidationError from CRUD
    assert "Deadline cannot be in the past" in response.json()["detail"]

def test_create_project_api_unauthenticated(client: TestClient, project_api_data: dict):
    data = project_api_data.copy()
    data.pop("author_id", None)
    response = client.post("/projects/", json=data) # No headers
    assert response.status_code == 401 # Unauthorized

# --- Fixture for a set of projects for API list tests ---
@pytest.fixture
def api_project_set(db: Session, test_user: UserModel, test_superuser: UserModel):
    # Use app.crud.project.create_project to create projects
    # Need to import it or use client calls if API requires superuser for creation
    from app.crud.project import create_project as crud_create_project
    from app.core.exceptions import DuplicateProjectName # To handle potential name clashes if run multiple times
    from datetime import datetime, timezone # Ensure datetime and timezone are imported for the fixture
    import uuid # Ensure uuid is imported for the fixture

    projects_data = [
        {"name": f"API User1 Proj Alpha {uuid.uuid4().hex[:4]}", "author_id": test_user.id, "project_status": "active", "tags": ["frontend"], "is_favorite": True},
        {"name": f"API User1 Proj Beta {uuid.uuid4().hex[:4]}", "author_id": test_user.id, "project_status": "planning", "tags": ["backend"]},
        {"name": f"API User1 Proj Gamma (Archived) {uuid.uuid4().hex[:4]}", "author_id": test_user.id, "project_status": "archived", "is_deleted": True},
        {"name": f"API Superuser Proj Omega {uuid.uuid4().hex[:4]}", "author_id": test_superuser.id, "project_status": "active", "tags": ["infra"], "is_favorite": True},
        {"name": f"API Superuser Proj Zeta (Archived) {uuid.uuid4().hex[:4]}", "author_id": test_superuser.id, "project_status": "archived", "is_deleted": True},
    ]
    created_projects = []
    for data in projects_data:
        is_del = data.pop("is_deleted", False)
        # CRUD create_project doesn't take is_deleted directly, handle after creation
        try:
            proj = crud_create_project(db, data)
            if is_del:
                proj.is_deleted = True
                proj.deleted_at = datetime.now(timezone.utc) # Use timezone aware
                proj.project_status = data.get("project_status", "archived")
                db.commit()
                db.refresh(proj)
            created_projects.append(proj)
        except DuplicateProjectName: # Handle if a previous identical run created this
            existing_proj = db.query(ProjectModel).filter(ProjectModel.name == data['name']).first()
            if existing_proj:
                created_projects.append(existing_proj)
            else: # Should not happen if name is truly unique
                raise
    return created_projects

# --- Tests for GET /projects/ (list_projects) ---
def test_list_projects_as_normal_user(client: TestClient, normal_user_token_headers: dict, api_project_set, test_user: UserModel):
    response = client.get("/projects/", headers=normal_user_token_headers)
    assert response.status_code == 200
    projects = response.json()
    # Expects 2 non-archived projects for test_user: Alpha, Beta
    assert len(projects) == 2
    for p in projects:
        assert p["author_id"] == test_user.id
        assert not p.get("is_deleted", False) # ProjectShort might not have is_deleted

def test_list_projects_as_superuser_default(client: TestClient, superuser_token_headers: dict, api_project_set):
    response = client.get("/projects/", headers=superuser_token_headers)
    assert response.status_code == 200
    projects = response.json()
    # Expects 3 non-archived projects: User1 Alpha, User1 Beta, Superuser Omega
    assert len(projects) == 3

def test_list_projects_as_superuser_show_archived(client: TestClient, superuser_token_headers: dict, api_project_set):
    response = client.get("/projects/?show_archived=true", headers=superuser_token_headers)
    assert response.status_code == 200
    projects = response.json()
    # Expects all 5 projects
    assert len(projects) == 5

def test_list_projects_filter_tag_normal_user(client: TestClient, normal_user_token_headers: dict, api_project_set, test_user: UserModel):
    response = client.get("/projects/?tag=frontend", headers=normal_user_token_headers)
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) == 1
    assert "API User1 Proj Alpha" in projects[0]["name"]

def test_list_projects_filter_is_favorite_superuser(client: TestClient, superuser_token_headers: dict, api_project_set):
    response = client.get("/projects/?is_favorite=true", headers=superuser_token_headers)
    assert response.status_code == 200
    projects = response.json()
    # User1 Alpha, Superuser Omega
    assert len(projects) == 2

# --- Tests for GET /projects/{project_id} ---
def test_get_project_by_id_author_success(client: TestClient, normal_user_token_headers: dict, api_project_set, test_user: UserModel):
    # Find a project authored by test_user from the set
    project_id = None
    expected_name = ""
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted:
            project_id = p.id
            expected_name = p.name
            break
    assert project_id is not None, "No suitable project found in fixture for test_user"

    response = client.get(f"/projects/{project_id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == expected_name
    assert data["author_id"] == test_user.id

def test_get_project_by_id_superuser_can_access_others(client: TestClient, superuser_token_headers: dict, api_project_set, test_user: UserModel):
    # Superuser accesses a project owned by test_user
    project_id = None
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted:
            project_id = p.id
            break
    assert project_id is not None, "No suitable project found in fixture for test_user"

    response = client.get(f"/projects/{project_id}", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["author_id"] == test_user.id # Still shows original author

def test_get_project_by_id_normal_user_forbidden(client: TestClient, normal_user_token_headers: dict, api_project_set, test_superuser: UserModel):
    # Normal user tries to access a project owned by test_superuser
    project_id = None
    for p in api_project_set:
        if p.author_id == test_superuser.id and not p.is_deleted:
            project_id = p.id
            break
    assert project_id is not None, "No suitable project found in fixture for test_superuser"

    response = client.get(f"/projects/{project_id}", headers=normal_user_token_headers)
    assert response.status_code == 403 # Or 404 depending on get_project_for_user_or_404_403 logic

def test_get_project_by_id_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.get("/projects/99999", headers=superuser_token_headers)
    assert response.status_code == 404

def test_get_project_by_id_soft_deleted_not_found_default(client: TestClient, superuser_token_headers: dict, api_project_set, test_superuser: UserModel):
    # Find a soft-deleted project by test_superuser
    project_id = None
    for p in api_project_set:
        if p.author_id == test_superuser.id and p.is_deleted:
            project_id = p.id
            break
    assert project_id is not None, "No soft-deleted project found for superuser in fixture"

    response = client.get(f"/projects/{project_id}", headers=superuser_token_headers)
    # get_project_for_user_or_404_403 by default does not return deleted items
    assert response.status_code == 404

# --- Tests for PATCH /projects/{project_id} (update_one_project) ---
def test_update_project_api_by_author_success(client: TestClient, normal_user_token_headers: dict, api_project_set, test_user: UserModel, db: Session):
    # Find a project authored by test_user
    project_to_update = None
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted:
            project_to_update = p
            break
    assert project_to_update is not None, "No suitable project found for test_user to update"

    update_data = {
        "name": "Updated API Project Name",
        "description": "Updated via API.",
        "project_status": "done",
        "priority": 5,
        "tags": ["api_updated"],
        "custom_fields": {"valid_text_field": "api_custom_val"}
    }

    # Patch the CUSTOM_FIELDS_SCHEMA for the scope of this test if update_project uses it for validation
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        response = client.patch(f"/projects/{project_to_update.id}", json=update_data, headers=normal_user_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated API Project Name"
    assert data["description"] == "Updated via API."
    assert data["project_status"] == "done"
    assert data["priority"] == 5
    assert "api_updated" in data["tags"]
    # Custom fields might not be in ProjectRead, check DB or adjust ProjectRead schema if needed
    updated_project_from_db = db.query(ProjectModel).get(project_to_update.id)
    assert updated_project_from_db.custom_fields["valid_text_field"] == "api_custom_val"

def test_update_project_api_partial_by_author(client: TestClient, normal_user_token_headers: dict, api_project_set, test_user: UserModel):
    project_to_update = None
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted:
            project_to_update = p
            break
    assert project_to_update is not None

    update_data = {"project_status": "archived"}
    response = client.patch(f"/projects/{project_to_update.id}", json=update_data, headers=normal_user_token_headers)
    assert response.status_code == 200
    assert response.json()["project_status"] == "archived"

def test_update_project_api_by_superuser_on_others_project(client: TestClient, superuser_token_headers: dict, api_project_set, test_user: UserModel):
    project_to_update = None
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted: # Find test_user's project
            project_to_update = p
            break
    assert project_to_update is not None

    update_data = {"name": "Superuser Updated Name"}
    response = client.patch(f"/projects/{project_to_update.id}", json=update_data, headers=superuser_token_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Superuser Updated Name"

def test_update_project_api_forbidden_for_normal_user_on_others_project(client: TestClient, normal_user_token_headers: dict, api_project_set, test_superuser: UserModel):
    project_to_update = None
    for p in api_project_set:
        if p.author_id == test_superuser.id and not p.is_deleted: # Find test_superuser's project
            project_to_update = p
            break
    assert project_to_update is not None

    update_data = {"name": "Normal User Attempt Update"}
    response = client.patch(f"/projects/{project_to_update.id}", json=update_data, headers=normal_user_token_headers)
    assert response.status_code == 403 # Or 404

def test_update_project_api_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.patch("/projects/99999", json={"name": "Does not exist"}, headers=superuser_token_headers)
    assert response.status_code == 404

def test_update_project_api_validation_error_empty_name(client: TestClient, superuser_token_headers: dict, api_project_set, test_superuser: UserModel):
    project_to_update = None
    for p in api_project_set:
        if p.author_id == test_superuser.id and not p.is_deleted:
            project_to_update = p
            break
    assert project_to_update is not None

    update_data = {"name": ""} # Empty name
    response = client.patch(f"/projects/{project_to_update.id}", json=update_data, headers=superuser_token_headers)
    assert response.status_code == 400 # ProjectValidationError from CRUD
    assert "Project name is required" in response.json()["detail"]

# --- Tests for DELETE /projects/{project_id} (archive_project_api) ---
def test_delete_project_api_by_author_success(client: TestClient, normal_user_token_headers: dict, api_project_set, test_user: UserModel, db: Session):
    project_to_delete = None
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted:
            project_to_delete = p
            break
    assert project_to_delete is not None, "No active project found for test_user to delete"

    response = client.delete(f"/projects/{project_to_delete.id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    assert response.json()["detail"] == "Project archived"

    deleted_project_from_db = db.query(ProjectModel).filter(ProjectModel.id == project_to_delete.id).first()
    assert deleted_project_from_db.is_deleted is True
    assert deleted_project_from_db.project_status == "archived"

def test_delete_project_api_by_superuser_on_others(client: TestClient, superuser_token_headers: dict, api_project_set, test_user: UserModel, db: Session):
    project_to_delete = None
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted: # Find test_user's project
            project_to_delete = p
            break
    assert project_to_delete is not None

    response = client.delete(f"/projects/{project_to_delete.id}", headers=superuser_token_headers)
    assert response.status_code == 200
    deleted_project_from_db = db.query(ProjectModel).filter(ProjectModel.id == project_to_delete.id).first()
    assert deleted_project_from_db.is_deleted is True

def test_delete_project_api_forbidden_for_normal_user_on_others(client: TestClient, normal_user_token_headers: dict, api_project_set, test_superuser: UserModel):
    project_to_delete = None
    for p in api_project_set:
        if p.author_id == test_superuser.id and not p.is_deleted: # Find superuser's project
            project_to_delete = p
            break
    assert project_to_delete is not None

    response = client.delete(f"/projects/{project_to_delete.id}", headers=normal_user_token_headers)
    assert response.status_code == 403 # or 404

def test_delete_project_api_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.delete("/projects/99999", headers=superuser_token_headers)
    assert response.status_code == 404

def test_delete_project_api_already_deleted(client: TestClient, superuser_token_headers: dict, api_project_set, test_superuser: UserModel, db: Session):
    project_to_delete = None # Find an already deleted project by superuser
    for p in api_project_set:
        if p.author_id == test_superuser.id and p.is_deleted:
            project_to_delete = p
            break
    assert project_to_delete is not None, "No archived project found for superuser in fixture"

    response = client.delete(f"/projects/{project_to_delete.id}", headers=superuser_token_headers)
    assert response.status_code == 400 # ProjectValidationError: "Project already archived."
    assert "Project already archived" in response.json()["detail"]

# --- Tests for POST /projects/{project_id}/restore (restore_deleted_project) ---
def test_restore_project_api_by_author_success(client: TestClient, normal_user_token_headers: dict, api_project_set, test_user: UserModel, db: Session):
    project_to_restore = None # Find an archived project by test_user
    for p in api_project_set:
        if p.author_id == test_user.id and p.is_deleted:
            project_to_restore = p
            break
    assert project_to_restore is not None, "No archived project found for test_user to restore"

    response = client.post(f"/projects/{project_to_restore.id}/restore", headers=normal_user_token_headers)
    assert response.status_code == 200
    assert response.json()["detail"] == "Project restored"

    restored_project_from_db = db.query(ProjectModel).get(project_to_restore.id)
    assert restored_project_from_db.is_deleted is False
    assert restored_project_from_db.project_status == "active"

def test_restore_project_api_not_deleted(client: TestClient, normal_user_token_headers: dict, api_project_set, test_user: UserModel):
    project_not_deleted = None # Find an active project by test_user
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted:
            project_not_deleted = p
            break
    assert project_not_deleted is not None

    response = client.post(f"/projects/{project_not_deleted.id}/restore", headers=normal_user_token_headers)
    assert response.status_code == 400 # ProjectValidationError from CRUD
    assert "is not archived/deleted" in response.json()["detail"]

def test_restore_project_api_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.post("/projects/99999/restore", headers=superuser_token_headers)
    assert response.status_code == HTTPStatus.NOT_FOUND # Dependency get_deleted_project_for_user_or_404_403 will 404


# --- Tests for GET /projects/{project_id}/ai_context ---

def test_get_project_ai_context_success(
    client: TestClient,
    normal_user_token_headers: dict,
    api_project_set: list, # api_project_set is a list of ProjectModel
    test_user: UserModel,
    db: Session
):
    project_to_use = None
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted:
            project_to_use = p
            break
    assert project_to_use is not None, "No suitable project found for test_user in api_project_set"

    mock_ai_context_data = {"project_name": project_to_use.name, "description": project_to_use.description, "tasks_count": 5, "custom_field": "value"}

    # Patch the function where it's looked up by the endpoint code
    with patch("app.api.project.crud_get_ai_context_for_project") as mock_crud_get_ai_context:
        mock_crud_get_ai_context.return_value = mock_ai_context_data

        response = client.get(f"{app_settings.API_V1_STR}/projects/{project_to_use.id}/ai_context", headers=normal_user_token_headers)

        assert response.status_code == HTTPStatus.OK, response.text
        assert response.json() == mock_ai_context_data
        # The API endpoint calls crud_get_ai_context_for_project(db, project_id)
        mock_crud_get_ai_context.assert_called_once_with(db, project_id=project_to_use.id)

def test_get_project_ai_context_project_not_found(client: TestClient, normal_user_token_headers: dict):
    non_existent_project_id = uuid.uuid4()
    response = client.get(f"{app_settings.API_V1_STR}/projects/{non_existent_project_id}/ai_context", headers=normal_user_token_headers)
    assert response.status_code == HTTPStatus.NOT_FOUND, response.text

def test_get_project_ai_context_forbidden_other_user(
    client: TestClient,
    other_user_token_headers: dict, # Assumed fixture from conftest.py
    api_project_set: list,
    test_user: UserModel
):
    project_to_use = None
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted: # Project owned by test_user
            project_to_use = p
            break
    assert project_to_use is not None, "No suitable project found for test_user in api_project_set"

    # other_user tries to access test_user's project context
    response = client.get(f"{app_settings.API_V1_STR}/projects/{project_to_use.id}/ai_context", headers=other_user_token_headers)
    # get_project_for_user_or_404_403 dependency handles this
    assert response.status_code == HTTPStatus.FORBIDDEN, response.text # Or 404 depending on exact behavior of dependency


# --- Tests for GET /projects/{project_id}/summary ---

def test_get_project_summary_success(
    client: TestClient,
    normal_user_token_headers: dict,
    api_project_set: list,
    test_user: UserModel,
    db: Session
):
    project_to_use = None
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted:
            project_to_use = p
            break
    assert project_to_use is not None, "No suitable project found for test_user in api_project_set"

    mock_summary_text = f"This is a detailed summary of project {project_to_use.name}."

    # Patch the function where it's looked up by the endpoint code
    with patch("app.api.project.crud_summarize_project") as mock_crud_summarize_project:
        mock_crud_summarize_project.return_value = mock_summary_text

        response = client.get(f"{app_settings.API_V1_STR}/projects/{project_to_use.id}/summary", headers=normal_user_token_headers)

        assert response.status_code == HTTPStatus.OK, response.text
        # The endpoint uses response_model=str, FastAPI returns this as a JSON-encoded string
        assert response.json() == mock_summary_text
        mock_crud_summarize_project.assert_called_once_with(db, project_id=project_to_use.id)

def test_get_project_summary_project_not_found(client: TestClient, normal_user_token_headers: dict):
    non_existent_project_id = uuid.uuid4()
    response = client.get(f"{app_settings.API_V1_STR}/projects/{non_existent_project_id}/summary", headers=normal_user_token_headers)
    assert response.status_code == HTTPStatus.NOT_FOUND, response.text

def test_get_project_summary_forbidden_other_user(
    client: TestClient,
    other_user_token_headers: dict,
    api_project_set: list,
    test_user: UserModel
):
    project_to_use = None
    for p in api_project_set:
        if p.author_id == test_user.id and not p.is_deleted: # Project owned by test_user
            project_to_use = p
            break
    assert project_to_use is not None, "No suitable project found for test_user in api_project_set"

    # other_user tries to access test_user's project summary
    response = client.get(f"{app_settings.API_V1_STR}/projects/{project_to_use.id}/summary", headers=other_user_token_headers)
    assert response.status_code == HTTPStatus.FORBIDDEN, response.text # Or 404


# --- Fixture for a single project by test_user for focused tests ---
@pytest.fixture
def test_project_by_user(db: Session, test_user: UserModel) -> ProjectModel:
    from app.crud.project import create_project as crud_create_project
    from app.core.exceptions import DuplicateProjectName

    project_data = {
        "name": f"Dedicated Test Project {uuid.uuid4().hex[:6]}",
        "description": "A project for specific update tests.",
        "author_id": test_user.id, # This will be set by CRUD or API based on current_user
        "project_status": "active",
        "deadline": (datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat(),
        "priority": 1,
        "tags": ["fixture_tag"],
        "custom_fields": {"initial_field": "initial_value"}
    }
    # crud_create_project in this app typically takes dict and sets author_id from calling user or context
    # For fixture, we might need to pass author_id if not implicit by some other means
    # The existing create_project in crud takes a dict, let's ensure author_id is part of it.
    try:
        return crud_create_project(db, project_data)
    except DuplicateProjectName: # Should not happen with UUID in name
        return db.query(ProjectModel).filter(ProjectModel.name == project_data["name"]).first()


# --- Tests for Custom Field Validation (PATCH /projects/{project_id}) ---

MOCKED_TEST_CUSTOM_FIELDS_SCHEMA = {
    "valid_text_field": {"type": "string", "required": False},
    "required_number_field": {"type": "number", "required": True},
    "bool_field": {"type": "boolean", "required": False}
}

def test_update_project_custom_fields_success(
    client: TestClient, normal_user_token_headers: dict, test_project_by_user: ProjectModel, db: Session
):
    update_payload = {
        "custom_fields": {
            "valid_text_field": "new text value",
            "required_number_field": 42,
            "bool_field": True
        }
    }
    with patch("app.crud.project.CUSTOM_FIELDS_SCHEMA", MOCKED_TEST_CUSTOM_FIELDS_SCHEMA):
        response = client.patch(f"{app_settings.API_V1_STR}/projects/{test_project_by_user.id}", headers=normal_user_token_headers, json=update_payload)

    assert response.status_code == HTTPStatus.OK, response.text
    db.refresh(test_project_by_user)
    assert test_project_by_user.custom_fields["valid_text_field"] == "new text value"
    assert test_project_by_user.custom_fields["required_number_field"] == 42
    assert test_project_by_user.custom_fields["bool_field"] is True

def test_update_project_custom_fields_validation_error_invalid_type(
    client: TestClient, normal_user_token_headers: dict, test_project_by_user: ProjectModel, db: Session
):
    update_payload = {
        "custom_fields": {
            "required_number_field": "this is not a number" # Invalid type
        }
    }
    with patch("app.crud.project.CUSTOM_FIELDS_SCHEMA", MOCKED_TEST_CUSTOM_FIELDS_SCHEMA):
        response = client.patch(f"{app_settings.API_V1_STR}/projects/{test_project_by_user.id}", headers=normal_user_token_headers, json=update_payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.text # CRUD validation raises ProjectValidationError -> 400
    assert "Invalid type for field 'required_number_field'" in response.json()["detail"]

def test_update_project_custom_fields_validation_error_missing_required(
    client: TestClient, normal_user_token_headers: dict, test_project_by_user: ProjectModel, db: Session
):
    update_payload = {
        "custom_fields": {
            "valid_text_field": "only this field" # Missing required_number_field
        }
    }
    # Ensure the project initially doesn't have the required field, or this test might pass if it's already set.
    test_project_by_user.custom_fields = {"valid_text_field": "pre-existing"}
    db.commit()
    db.refresh(test_project_by_user)

    with patch("app.crud.project.CUSTOM_FIELDS_SCHEMA", MOCKED_TEST_CUSTOM_FIELDS_SCHEMA):
        response = client.patch(f"{app_settings.API_V1_STR}/projects/{test_project_by_user.id}", headers=normal_user_token_headers, json=update_payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.text
    assert "Missing required custom field 'required_number_field'" in response.json()["detail"]

def test_update_project_custom_fields_clear_fields(
    client: TestClient, normal_user_token_headers: dict, test_project_by_user: ProjectModel, db: Session
):
    # First, ensure some custom fields are set
    initial_custom_fields = {
        "custom_fields": {
            "valid_text_field": "text to be cleared",
            "required_number_field": 123 # Must be valid to set initially
        }
    }
    with patch("app.crud.project.CUSTOM_FIELDS_SCHEMA", MOCKED_TEST_CUSTOM_FIELDS_SCHEMA):
        client.patch(f"{app_settings.API_V1_STR}/projects/{test_project_by_user.id}", headers=normal_user_token_headers, json=initial_custom_fields)

    db.refresh(test_project_by_user)
    assert test_project_by_user.custom_fields.get("valid_text_field") == "text to be cleared"

    # Then, update with empty custom_fields dict
    update_payload_clear = {"custom_fields": {}}
    with patch("app.crud.project.CUSTOM_FIELDS_SCHEMA", MOCKED_TEST_CUSTOM_FIELDS_SCHEMA): # Schema still applies for update
        response = client.patch(f"{app_settings.API_V1_STR}/projects/{test_project_by_user.id}", headers=normal_user_token_headers, json=update_payload_clear)

    assert response.status_code == HTTPStatus.OK, response.text
    db.refresh(test_project_by_user)
    # Depending on CRUD logic: {} means "clear all non-required" or "clear all".
    # Assuming it means "clear all fields that are not required and not provided".
    # If required_number_field was set, and then an empty {} is sent, it should ideally complain about missing required if it clears all.
    # Or, if {} means "no changes to custom_fields", then this test needs rethink.
    # The prompt implies {} should clear. Let's assume it clears fields not in the schema or not required.
    # A more robust test would be to check if valid_text_field is gone, and required_number_field is still there or also gone (if allowed).
    # If CUSTOM_FIELDS_SCHEMA is strictly enforced on update (i.e. all required fields must be present in payload if custom_fields key is present):
    # Then sending {"custom_fields": {}} would fail if required_number_field is missing.
    # This test path needs to be very specific to the implementation of custom field updates.
    # For now, let's assume {} means clear optional fields, but required ones must persist or be re-provided.
    # The current CRUD logic for custom fields (validate_custom_fields) might need to be checked.
    # If we assume {} means "clear all", then required field validation should kick in if schema requires it.
    # Let's adjust the test: clearing should make optional fields null/gone.
    # The required field should remain or the update should fail if it's not re-provided.
    # A simpler "clear" is to set to null if schema allows, or omit.
    # Let's test clearing an optional field by setting it to None (if schema supports null) or sending empty dict.
    # For this test, let's assume custom_fields: {} means "remove all existing custom fields".
    # If required fields are truly "required" they cannot be removed.
    # This test is tricky. Re-simplifying: set optional field, then clear it.

    # Re-simplifying the clear test:
    # 1. Set an optional field and a required field.
    project_with_fields = {
        "custom_fields": {"valid_text_field": "abc", "required_number_field": 789}
    }
    with patch("app.crud.project.CUSTOM_FIELDS_SCHEMA", MOCKED_TEST_CUSTOM_FIELDS_SCHEMA):
        res = client.patch(f"{app_settings.API_V1_STR}/projects/{test_project_by_user.id}", headers=normal_user_token_headers, json=project_with_fields)
        assert res.status_code == HTTPStatus.OK

    # 2. Update to remove the optional field by not including it (partial update)
    #    or by setting custom_fields to only contain the required one.
    update_to_clear_optional = {
         "custom_fields": {"required_number_field": 789} # valid_text_field is omitted
    }
    with patch("app.crud.project.CUSTOM_FIELDS_SCHEMA", MOCKED_TEST_CUSTOM_FIELDS_SCHEMA):
        response_clear = client.patch(f"{app_settings.API_V1_STR}/projects/{test_project_by_user.id}", headers=normal_user_token_headers, json=update_to_clear_optional)
    assert response_clear.status_code == HTTPStatus.OK
    db.refresh(test_project_by_user)
    assert "valid_text_field" not in test_project_by_user.custom_fields # Or is None, depending on update logic
    assert test_project_by_user.custom_fields["required_number_field"] == 789


# --- Tests for Duplicate Project Name (PATCH /projects/{project_id}) ---

def test_update_project_duplicate_name_error(
    client: TestClient, normal_user_token_headers: dict, test_user: UserModel, db: Session
):
    from app.crud.project import create_project as crud_create_project # For test setup

    # Create two projects for the same user
    project1_data = {"name": f"Original Name {uuid.uuid4().hex[:6]}", "author_id": test_user.id, "description":"First project"}
    project1 = crud_create_project(db, project1_data)

    project2_data = {"name": f"Second Name {uuid.uuid4().hex[:6]}", "author_id": test_user.id, "description":"Second project"}
    project2 = crud_create_project(db, project2_data)

    update_payload = {"name": project1.name} # Attempt to update project2's name to project1's name

    response = client.patch(f"{app_settings.API_V1_STR}/projects/{project2.id}", headers=normal_user_token_headers, json=update_payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.text # DuplicateProjectName from CRUD -> 400
    assert "Project name already exists" in response.json()["detail"]

def test_update_project_same_name_no_change_ok(
    client: TestClient, normal_user_token_headers: dict, test_project_by_user: ProjectModel, db: Session
):
    update_payload = {"name": test_project_by_user.name} # Update with its own current name

    response = client.patch(f"{app_settings.API_V1_STR}/projects/{test_project_by_user.id}", headers=normal_user_token_headers, json=update_payload)

    assert response.status_code == HTTPStatus.OK, response.text
    # Ensure no unintended changes, e.g. description is still the same
    db.refresh(test_project_by_user)
    assert response.json()["name"] == test_project_by_user.name


# TODO: Test pagination and more complex filtering for list_projects if not fully covered.
# TODO: Test behavior of endpoints when underlying CRUD functions raise unexpected errors (e.g., DB errors if not caught).

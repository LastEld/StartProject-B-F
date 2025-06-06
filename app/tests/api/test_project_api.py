import pytest
import pytest
import uuid # For unique names in fixture
from unittest.mock import patch
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
    assert response.status_code == 404 # Dependency get_deleted_project_for_user_or_404_403 will 404

# TODO: Add tests for GET /projects/{project_id}/ai_context
# TODO: Add tests for GET /projects/{project_id}/summarize
# TODO: Add more tests for custom field validation via API update
# TODO: Add tests for duplicate project name via API update (if name updates are allowed and constrained)

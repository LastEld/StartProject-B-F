#test/test_devlog_api.py
import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta # Added

from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.models.task import Task as TaskModel
from app.models.devlog import DevLogEntry as DevLogModel

from app.crud.project import create_project as crud_create_project
from app.crud.task import create_task as crud_create_task
from app.crud.devlog import create_entry as crud_create_devlog_entry
from app.crud.devlog import get_entry as crud_get_devlog_entry
from app.crud.devlog import soft_delete_entry as crud_soft_delete_devlog_entry # Added import

from app.core.config import settings # If needed for something specific
from app.core.exceptions import DevLogValidationError, ProjectNotFound, TaskNotFound # For expected errors

# --- Fixtures ---

@pytest.fixture
def project_by_user1(db: Session, test_user: UserModel) -> ProjectModel:
    return crud_create_project(db, {"name": f"User1 Project {uuid.uuid4().hex[:4]}", "author_id": test_user.id})

@pytest.fixture
def project_by_user2(db: Session, test_superuser: UserModel) -> ProjectModel: # Using superuser as a distinct "other user"
    return crud_create_project(db, {"name": f"User2 Project {uuid.uuid4().hex[:4]}", "author_id": test_superuser.id})

@pytest.fixture
def project_by_user1_another(db: Session, test_user: UserModel) -> ProjectModel: # Second project for test_user
    return crud_create_project(db, {"name": f"User1 Another Project {uuid.uuid4().hex[:4]}", "author_id": test_user.id})

@pytest.fixture
def task_in_project_by_user1(db: Session, project_by_user1: ProjectModel) -> TaskModel:
    return crud_create_task(db, {"title": f"Task in User1 Project {uuid.uuid4().hex[:4]}", "project_id": project_by_user1.id})

@pytest.fixture
def devlog_api_payload_factory(project_by_user1: ProjectModel, task_in_project_by_user1: TaskModel):
    def _factory(**kwargs):
        unique_suffix = uuid.uuid4().hex[:6]
        data = {
            "content": f"API DevLog content {unique_suffix}",
            "entry_type": "note",
            "project_id": project_by_user1.id, # Default to user1's project
            "task_id": task_in_project_by_user1.id, # Default to user1's task
            "tags": ["api_test"],
            # Custom fields can be added here if needed for specific tests
        }
        data.update(kwargs)
        # Remove keys if their passed value is None explicitly, to test default creations
        return {k: v for k, v in data.items() if v is not None}
    return _factory

# --- Tests for POST /devlog/ ---

def test_create_devlog_api_success_user_own_project(
    client: TestClient, normal_user_token_headers: dict, db: Session,
    test_user: UserModel, project_by_user1: ProjectModel, devlog_api_payload_factory: callable
):
    payload = devlog_api_payload_factory(project_id=project_by_user1.id, task_id=None)
    response = client.post("/devlog/", json=payload, headers=normal_user_token_headers)

    assert response.status_code == 200 # Default for FastAPI if not specified
    data = response.json()
    assert data["content"] == payload["content"]
    assert data["author_id"] == test_user.id
    live_project = db.merge(project_by_user1) # Ensure project is in session
    expected_project_id = live_project.id
    assert data["project_id"] == expected_project_id

    entry_in_db = crud_get_devlog_entry(db, data["id"])
    assert entry_in_db is not None
    assert entry_in_db.author_id == test_user.id

def test_create_devlog_api_success_no_project_or_task(
    client: TestClient, normal_user_token_headers: dict, db: Session, test_user: UserModel, devlog_api_payload_factory: callable
):
    payload = devlog_api_payload_factory(project_id=None, task_id=None)
    response = client.post("/devlog/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["author_id"] == test_user.id
    assert data["project_id"] is None
    assert data["task_id"] is None

def test_create_devlog_api_success_superuser_any_project(
    client: TestClient, superuser_token_headers: dict, db: Session,
    test_superuser: UserModel, project_by_user1: ProjectModel, # project_by_user1 is owned by test_user
    devlog_api_payload_factory: callable
):
    payload = devlog_api_payload_factory(project_id=project_by_user1.id, task_id=None)
    response = client.post("/devlog/", json=payload, headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    live_project = db.merge(project_by_user1) # Ensure project is in session
    expected_project_id = live_project.id
    assert data["author_id"] == test_superuser.id # Logged by superuser
    assert data["project_id"] == expected_project_id # Associated with test_user's project

def test_create_devlog_api_forbidden_for_other_user_project(
    client: TestClient, normal_user_token_headers: dict,
    project_by_user2: ProjectModel, # project_by_user2 is owned by test_superuser/another user
    devlog_api_payload_factory: callable
):
    payload = devlog_api_payload_factory(project_id=project_by_user2.id, task_id=None)
    response = client.post("/devlog/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 403 # Forbidden based on check_project_access
    assert "Not authorized to access this project" in response.json()["detail"]

def test_create_devlog_api_project_not_found(
    client: TestClient, normal_user_token_headers: dict, devlog_api_payload_factory: callable
):
    payload = devlog_api_payload_factory(project_id=99999, task_id=None)
    response = client.post("/devlog/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 404 # From check_project_access or CRUD create_entry
    assert "Project with id 99999 not found" in response.json()["detail"]

def test_create_devlog_api_task_not_found_but_no_project_given(
    client: TestClient, normal_user_token_headers: dict, devlog_api_payload_factory: callable
):
    # If task_id is given, and project_id is NOT, API tries to find task to get project_id
    payload = devlog_api_payload_factory(project_id=None, task_id=88888)
    response = client.post("/devlog/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 404
    assert "Task with id 88888 not found" in response.json()["detail"]


def test_create_devlog_api_empty_content(
    client: TestClient, normal_user_token_headers: dict, devlog_api_payload_factory: callable
):
    payload = devlog_api_payload_factory(content=" ")
    response = client.post("/devlog/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 400 # DevLogValidationError from CRUD
    assert "DevLog entry content cannot be empty" in response.json()["detail"]

def test_create_devlog_api_unauthenticated(
    client: TestClient, devlog_api_payload_factory: callable
):
    payload = devlog_api_payload_factory()
    response = client.post("/devlog/", json=payload) # No headers
    assert response.status_code == 401

# --- Fixture for DevLog API list tests ---
@pytest.fixture
def api_devlog_entry_set(
    db: Session, test_user: UserModel, test_superuser: UserModel,
    project_by_user1: ProjectModel, project_by_user2: ProjectModel, # project_by_user2 is by test_superuser
    task_in_project_by_user1: TaskModel,
    devlog_api_payload_factory: callable # Using this to generate base data
):
    entries = []
    now = datetime.now(timezone.utc)

    # User1 entries
    entry1_user1_data = devlog_api_payload_factory(
        content="User1 Log for Project1 Task1 (Recent)", project_id=project_by_user1.id, task_id=task_in_project_by_user1.id,
        entry_type="note", tags=["bugfix", "urgent"], created_at_override=now - timedelta(hours=1)
    )
    entries.append(crud_create_devlog_entry(db, {k:v for k,v in entry1_user1_data.items() if k != 'created_at_override'}, author_id=test_user.id))

    entry2_user1_data = devlog_api_payload_factory(
        content="User1 Log for Project2 (Older)", project_id=project_by_user2.id, # User1 logging on another's project (allowed if user has project access - API create checks this)
        entry_type="action", tags=["planning"], created_at_override=now - timedelta(days=2)
    )
    # For this fixture, we assume test_user has access to project_by_user2 for creation, or this entry won't be created by API.
    # For CRUD setup, this direct creation is fine.
    entries.append(crud_create_devlog_entry(db, {k:v for k,v in entry2_user1_data.items() if k != 'created_at_override'}, author_id=test_user.id))

    entry3_user1_deleted_data = devlog_api_payload_factory(
        content="User1 Deleted Log (Oldest)", project_id=project_by_user1.id, task_id=None,
        entry_type="note", tags=["archived"], created_at_override=now - timedelta(days=5)
    )
    deleted_entry_user1 = crud_create_devlog_entry(db, {k:v for k,v in entry3_user1_deleted_data.items() if k != 'created_at_override'}, author_id=test_user.id)
    crud_soft_delete_devlog_entry(db, deleted_entry_user1.id) # Use imported function
    entries.append(crud_get_devlog_entry(db, deleted_entry_user1.id)) # Get it after soft delete

    # Superuser entries
    entry4_superuser_data = devlog_api_payload_factory(
        content="Superuser Log for Project1 (Urgent)", project_id=project_by_user1.id, task_id=None,
        entry_type="decision", tags=["project1", "urgent"], created_at_override=now - timedelta(minutes=30)
    )
    entries.append(crud_create_devlog_entry(db, {k:v for k,v in entry4_superuser_data.items() if k != 'created_at_override'}, author_id=test_superuser.id))

    entry5_superuser_data = devlog_api_payload_factory(
        content="Superuser Log, no project (General)", project_id=None, task_id=None,
        entry_type="note", tags=["general"], created_at_override=now - timedelta(days=1, hours=2)
    )
    entries.append(crud_create_devlog_entry(db, {k:v for k,v in entry5_superuser_data.items() if k != 'created_at_override'}, author_id=test_superuser.id))

    # Manually set created_at for testing date filters, as CRUD doesn't allow overriding it
    for i, entry_spec in enumerate([entry1_user1_data, entry2_user1_data, entry3_user1_deleted_data, entry4_superuser_data, entry5_superuser_data]):
        if 'created_at_override' in entry_spec:
            entry_to_update = entries[i]
            entry_to_update.created_at = entry_spec['created_at_override']
            db.add(entry_to_update)
    db.commit()

    # Re-fetch all to have consistent session state for tests and ensure all data is loaded
    return {entry.content: db.query(DevLogModel).get(entry.id) for entry in entries}


# --- Tests for GET /devlog/ (list entries) ---

def test_list_devlog_api_normal_user_default(client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict, test_user: UserModel):
    response = client.get("/devlog/", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json() # List of DevLogShort
    # Normal user sees only their own non-deleted entries by default
    # User1 Log for Project1 Task1 (Recent), User1 Log for Project2 (Older)
    assert len(data) == 2
    for entry_short in data:
        assert entry_short["author_id"] == test_user.id
        db_entry = api_devlog_entry_set[entry_short["content"]] # Find by content
        assert db_entry.is_deleted is False

def test_list_devlog_api_superuser_default(client: TestClient, superuser_token_headers: dict, api_devlog_entry_set: dict):
    response = client.get("/devlog/", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    # Superuser sees all non-deleted entries
    # User1 Log1, User1 Log2, Superuser Log1, Superuser Log2
    assert len(data) == 4
    for entry_short in data:
        db_entry = api_devlog_entry_set[entry_short["content"]]
        assert db_entry.is_deleted is False

def test_list_devlog_api_normal_user_show_archived(client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict, test_user: UserModel):
    response = client.get("/devlog/?show_archived=true", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    # Normal user sees own entries, including archived
    # User1 Log1, User1 Log2, User1 Deleted Log
    assert len(data) == 3
    has_deleted = False
    for entry_short in data:
        assert entry_short["author_id"] == test_user.id
        if api_devlog_entry_set[entry_short["content"]].is_deleted:
            has_deleted = True
    assert has_deleted is True

def test_list_devlog_api_superuser_show_archived(client: TestClient, superuser_token_headers: dict, api_devlog_entry_set: dict):
    response = client.get("/devlog/?show_archived=true", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    # Superuser sees ALL entries
    assert len(data) == 5

def test_list_devlog_api_filter_by_project_id_user_has_access(
    client: TestClient, normal_user_token_headers: dict, project_by_user1: ProjectModel, api_devlog_entry_set: dict, test_user: UserModel, db: Session
):
    # Normal user filters for a project they created/own
    response = client.get(f"/devlog/?project_id={project_by_user1.id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    # User1 Log for Project1 Task1 (Recent) - authored by test_user
    # Superuser Log for Project1 (Urgent) - NOT authored by test_user, but in project_by_user1
    # API endpoint's check_project_access allows this. CRUD further filters by author for non-superuser.
    assert len(data) == 1
    for entry_short in data:
        # DevLogShort does not contain project_id, so fetch full entry to verify
        db_entry = crud_get_devlog_entry(db, entry_short["id"])
        assert db_entry.project_id == project_by_user1.id
        assert entry_short["author_id"] == test_user.id # CRUD get_entries ensures this for non-superusers

def test_list_devlog_api_filter_by_project_id_superuser(
    client: TestClient, superuser_token_headers: dict, project_by_user1: ProjectModel, api_devlog_entry_set: dict, db: Session
):
    response = client.get(f"/devlog/?project_id={project_by_user1.id}", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    # User1 Log for Project1 Task1, Superuser Log for Project1
    assert len(data) == 2
    for entry_short in data:
        # DevLogShort does not contain project_id, so fetch full entry to verify
        db_entry = crud_get_devlog_entry(db, entry_short["id"])
        assert db_entry.project_id == project_by_user1.id

def test_list_devlog_api_filter_by_tag(client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict, test_user: UserModel):
    response = client.get("/devlog/?tag=urgent", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    # User1 Log for Project1 Task1 (Recent) has "urgent" tag and is by test_user
    assert len(data) == 1
    assert data[0]["content"] == "User1 Log for Project1 Task1 (Recent)"

def test_list_devlog_api_pagination(client: TestClient, superuser_token_headers: dict, api_devlog_entry_set: dict):
    # Superuser sees 4 non-deleted by default
    response_page1 = client.get("/devlog/?per_page=3&page=1", headers=superuser_token_headers)
    assert response_page1.status_code == 200
    data_page1 = response_page1.json()
    assert len(data_page1) == 3

    response_page2 = client.get("/devlog/?per_page=3&page=2", headers=superuser_token_headers)
    assert response_page2.status_code == 200
    data_page2 = response_page2.json()
    assert len(data_page2) == 1


# --- Tests for GET /devlog/{entry_id} ---

def test_get_devlog_entry_api_success_author(
    client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict, test_user: UserModel
):
    # Find an entry authored by test_user
    entry_to_get = api_devlog_entry_set["User1 Log for Project1 Task1 (Recent)"]
    assert entry_to_get.author_id == test_user.id

    response = client.get(f"/devlog/{entry_to_get.id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == entry_to_get.id
    assert data["content"] == entry_to_get.content
    assert data["author_id"] == test_user.id

def test_get_devlog_entry_api_success_project_access_not_author(
    client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict,
    project_by_user1: ProjectModel, test_user: UserModel, test_superuser: UserModel
):
    # Entry by superuser on project_by_user1 (which test_user is author of)
    entry_to_get = api_devlog_entry_set["Superuser Log for Project1 (Urgent)"]
    assert entry_to_get.author_id == test_superuser.id
    assert entry_to_get.project_id == project_by_user1.id
    # test_user is author of project_by_user1, so should have access via check_project_access

    response = client.get(f"/devlog/{entry_to_get.id}", headers=normal_user_token_headers)
    assert response.status_code == 200 # Permitted due to project access
    data = response.json()
    assert data["id"] == entry_to_get.id
    assert data["content"] == entry_to_get.content

def test_get_devlog_entry_api_success_superuser_any_entry(
    client: TestClient, superuser_token_headers: dict, api_devlog_entry_set: dict, test_user: UserModel
):
    entry_by_normal_user = api_devlog_entry_set["User1 Log for Project1 Task1 (Recent)"]
    assert entry_by_normal_user.author_id == test_user.id

    response = client.get(f"/devlog/{entry_by_normal_user.id}", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == entry_by_normal_user.id

def test_get_devlog_entry_api_forbidden_no_access(
    client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict,
    project_by_user2: ProjectModel, test_superuser: UserModel # project_by_user2 is by test_superuser
):
    # Find an entry by test_superuser on a project test_user does not own (project_by_user2)
    # For this, we need to ensure such an entry exists or create one.
    # The fixture `api_devlog_entry_set` has "User1 Log for Project2 (Older)" which is by test_user on project_by_user2.
    # Let's use "Superuser Log, no project (General)" which is by superuser and has no project link.

    entry_by_superuser_no_project = api_devlog_entry_set["Superuser Log, no project (General)"]
    assert entry_by_superuser_no_project.author_id == test_superuser.id
    assert entry_by_superuser_no_project.project_id is None

    response = client.get(f"/devlog/{entry_by_superuser_no_project.id}", headers=normal_user_token_headers)
    assert response.status_code == 403 # Forbidden
    assert "Not authorized to read this DevLog entry" in response.json()["detail"]


def test_get_devlog_entry_api_not_found(client: TestClient, normal_user_token_headers: dict):
    response = client.get("/devlog/999999", headers=normal_user_token_headers)
    assert response.status_code == 404
    assert "DevLog entry not found" in response.json()["detail"]

def test_get_devlog_entry_api_normal_user_soft_deleted_is_404(
    client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict, test_user: UserModel
):
    deleted_entry = api_devlog_entry_set["User1 Deleted Log (Oldest)"]
    assert deleted_entry.author_id == test_user.id
    assert deleted_entry.is_deleted is True

    response = client.get(f"/devlog/{deleted_entry.id}", headers=normal_user_token_headers)
    assert response.status_code == 404 # Non-superuser cannot see deleted by direct ID
    assert "not found or has been archived" in response.json()["detail"]

def test_get_devlog_entry_api_superuser_can_see_soft_deleted(
    client: TestClient, superuser_token_headers: dict, api_devlog_entry_set: dict, test_user: UserModel
):
    deleted_entry = api_devlog_entry_set["User1 Deleted Log (Oldest)"]
    assert deleted_entry.author_id == test_user.id
    assert deleted_entry.is_deleted is True

    response = client.get(f"/devlog/{deleted_entry.id}", headers=superuser_token_headers)
    assert response.status_code == 200 # Superuser can see
    data = response.json()
    assert data["id"] == deleted_entry.id
    assert data["is_deleted"] is True # DevLogRead schema includes is_deleted

def test_get_devlog_entry_api_unauthenticated(client: TestClient, api_devlog_entry_set: dict):
    entry_to_get = api_devlog_entry_set["User1 Log for Project1 Task1 (Recent)"]
    response = client.get(f"/devlog/{entry_to_get.id}")
    assert response.status_code == 401


# --- Tests for PATCH /devlog/{entry_id} ---

def test_update_devlog_api_success_author(
    client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict,
    test_user: UserModel, db: Session, project_by_user1_another: ProjectModel # Use the new fixture
):
    # Ensure project_by_user1_another is session-managed for this test
    live_project_another = db.merge(project_by_user1_another)
    target_project_id = live_project_another.id

    entry_to_update = api_devlog_entry_set["User1 Log for Project1 Task1 (Recent)"]
    assert entry_to_update.author_id == test_user.id # Pre-condition

    update_payload = {
        "content": "Updated content by author.",
        "entry_type": "decision",
        "tags": ["updated_by_author"],
        "project_id": target_project_id # Moving to another of user1's projects
    }

    db_entry_before_update = crud_get_devlog_entry(db, entry_to_update.id)
    original_updated_at = db_entry_before_update.updated_at

    import time; time.sleep(0.01) # Ensure timestamp can change

    response = client.patch(f"/devlog/{entry_to_update.id}", json=update_payload, headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == update_payload["content"]
    assert data["entry_type"] == update_payload["entry_type"]
    assert sorted(data["tags"]) == sorted(update_payload["tags"])
    assert data["project_id"] == target_project_id
    assert data["updated_at"] > original_updated_at.isoformat()

    updated_db_entry = crud_get_devlog_entry(db, entry_to_update.id)
    assert updated_db_entry.content == update_payload["content"]
    assert updated_db_entry.updated_at > original_updated_at

def test_update_devlog_api_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_devlog_entry_set: dict,
    test_user: UserModel, db: Session # test_user is author of the entry
):
    entry_to_update = api_devlog_entry_set["User1 Log for Project1 Task1 (Recent)"]
    assert entry_to_update.author_id == test_user.id # Superuser updating another's entry

    update_payload = {"content": "Updated by superuser."}
    response = client.patch(f"/devlog/{entry_to_update.id}", json=update_payload, headers=superuser_token_headers)
    assert response.status_code == 200
    assert response.json()["content"] == "Updated by superuser."

def test_update_devlog_api_forbidden_non_author(
    client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict,
    test_superuser: UserModel, db: Session # test_superuser is author of entry to update
):
    # normal_user trying to update superuser's entry
    entry_by_superuser = api_devlog_entry_set["Superuser Log, no project (General)"]
    assert entry_by_superuser.author_id == test_superuser.id

    update_payload = {"content": "Attempted update by non-author."}
    response = client.patch(f"/devlog/{entry_by_superuser.id}", json=update_payload, headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized to update this DevLog entry" in response.json()["detail"]

def test_update_devlog_api_forbidden_change_project_no_access(
    client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict,
    project_by_user2: ProjectModel, test_user: UserModel # project_by_user2 owned by superuser/other
):
    entry_to_update = api_devlog_entry_set["User1 Log for Project1 Task1 (Recent)"]
    assert entry_to_update.author_id == test_user.id

    update_payload = {"project_id": project_by_user2.id} # Try to move to project_by_user2
    response = client.patch(f"/devlog/{entry_to_update.id}", json=update_payload, headers=normal_user_token_headers)
    assert response.status_code == 403 # User1 cannot access project_by_user2
    assert "Not authorized to access this project" in response.json()["detail"]


def test_update_devlog_api_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.patch("/devlog/99999", json={"content": "test"}, headers=superuser_token_headers)
    assert response.status_code == 404
    assert "DevLog entry not found" in response.json()["detail"]

def test_update_devlog_api_archived_entry_error(
    client: TestClient, superuser_token_headers: dict, api_devlog_entry_set: dict
):
    archived_entry = api_devlog_entry_set["User1 Deleted Log (Oldest)"]
    assert archived_entry.is_deleted is True

    response = client.patch(f"/devlog/{archived_entry.id}", json={"content": "update archived"}, headers=superuser_token_headers)
    assert response.status_code == 400
    assert "Cannot update an archived DevLog entry" in response.json()["detail"]

def test_update_devlog_api_invalid_project_id(
    client: TestClient, superuser_token_headers: dict, api_devlog_entry_set: dict
):
    entry_to_update = api_devlog_entry_set["Superuser Log, no project (General)"]
    response = client.patch(f"/devlog/{entry_to_update.id}", json={"project_id": 99999}, headers=superuser_token_headers)
    assert response.status_code == 404 # From check_project_access
    assert "Project with id 99999 not found" in response.json()["detail"]

def test_update_devlog_api_unauthenticated(client: TestClient, api_devlog_entry_set: dict):
    entry_to_update = api_devlog_entry_set["User1 Log for Project1 Task1 (Recent)"]
    response = client.patch(f"/devlog/{entry_to_update.id}", json={"content": "unauth update"})
    assert response.status_code == 401


# --- Tests for DELETE /devlog/{entry_id} ---

def test_delete_devlog_api_success_author(
    client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict, test_user: UserModel, db: Session
):
    entry_to_delete = api_devlog_entry_set["User1 Log for Project1 Task1 (Recent)"]
    assert entry_to_delete.author_id == test_user.id
    assert entry_to_delete.is_deleted is False
    entry_id_to_delete = entry_to_delete.id # Capture ID before API call

    response = client.delete(f"/devlog/{entry_id_to_delete}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == entry_id_to_delete
    assert "DevLog entry archived" in data["detail"]

    deleted_db_entry = crud_get_devlog_entry(db, entry_id_to_delete)
    assert deleted_db_entry.is_deleted is True

def test_delete_devlog_api_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_devlog_entry_set: dict, test_user: UserModel, db: Session
):
    entry_to_delete = api_devlog_entry_set["User1 Log for Project2 (Older)"] # Authored by test_user
    assert entry_to_delete.author_id == test_user.id
    assert entry_to_delete.is_deleted is False
    entry_id_to_delete = entry_to_delete.id # Capture ID

    response = client.delete(f"/devlog/{entry_id_to_delete}", headers=superuser_token_headers)
    assert response.status_code == 200

    deleted_db_entry = crud_get_devlog_entry(db, entry_id_to_delete)
    assert deleted_db_entry.is_deleted is True

def test_delete_devlog_api_forbidden_non_author(
    client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict, test_superuser: UserModel
):
    entry_by_superuser = api_devlog_entry_set["Superuser Log, no project (General)"]
    assert entry_by_superuser.author_id == test_superuser.id

    response = client.delete(f"/devlog/{entry_by_superuser.id}", headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized to delete this DevLog entry" in response.json()["detail"]

def test_delete_devlog_api_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.delete("/devlog/99999", headers=superuser_token_headers)
    assert response.status_code == 404
    assert "DevLog entry not found" in response.json()["detail"]

def test_delete_devlog_api_already_archived(client: TestClient, superuser_token_headers: dict, api_devlog_entry_set:dict):
    archived_entry = api_devlog_entry_set["User1 Deleted Log (Oldest)"]
    assert archived_entry.is_deleted is True

    response = client.delete(f"/devlog/{archived_entry.id}", headers=superuser_token_headers)
    assert response.status_code == 400
    assert "DevLog entry already archived" in response.json()["detail"]

def test_delete_devlog_api_unauthenticated(client: TestClient, api_devlog_entry_set: dict):
    entry_to_delete = api_devlog_entry_set["User1 Log for Project1 Task1 (Recent)"]
    response = client.delete(f"/devlog/{entry_to_delete.id}")
    assert response.status_code == 401

# --- Tests for POST /devlog/{entry_id}/restore ---

def test_restore_devlog_api_success_author(
    client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict, test_user: UserModel, db: Session
):
    entry_to_restore = api_devlog_entry_set["User1 Deleted Log (Oldest)"]
    assert entry_to_restore.author_id == test_user.id
    assert entry_to_restore.is_deleted is True
    entry_id_to_restore = entry_to_restore.id # Capture ID

    response = client.post(f"/devlog/{entry_id_to_restore}/restore", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == entry_id_to_restore
    assert "DevLog entry restored" in data["detail"]

    restored_db_entry = crud_get_devlog_entry(db, entry_id_to_restore)
    assert restored_db_entry.is_deleted is False

def test_restore_devlog_api_success_superuser(
    client: TestClient, superuser_token_headers: dict, api_devlog_entry_set: dict, test_user: UserModel, db: Session
):
    entry_to_restore = api_devlog_entry_set["User1 Deleted Log (Oldest)"]
    assert entry_to_restore.author_id == test_user.id
    assert entry_to_restore.is_deleted is True
    entry_id_to_restore = entry_to_restore.id # Capture ID

    response = client.post(f"/devlog/{entry_id_to_restore}/restore", headers=superuser_token_headers)
    assert response.status_code == 200

    restored_db_entry = crud_get_devlog_entry(db, entry_id_to_restore)
    assert restored_db_entry.is_deleted is False

def test_restore_devlog_api_forbidden_non_author(
    client: TestClient, normal_user_token_headers: dict, api_devlog_entry_set: dict, test_superuser: UserModel, db: Session, devlog_api_payload_factory: callable
):
    # Ensure there's a deleted entry by another user (superuser in this case)
    # The existing fixture might not guarantee this if test_user also has deleted items.
    # So, create one explicitly for this test scenario.
    other_user_entry_data = devlog_api_payload_factory(content="Superuser deleted log for restore test", project_id=None, task_id=None)
    other_user_entry = crud_create_devlog_entry(db, other_user_entry_data, author_id=test_superuser.id)
    crud_soft_delete_devlog_entry(db, other_user_entry.id)
    db.refresh(other_user_entry) # Load soft_delete changes
    assert other_user_entry.is_deleted is True

    response = client.post(f"/devlog/{other_user_entry.id}/restore", headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not authorized to restore this DevLog entry" in response.json()["detail"]

def test_restore_devlog_api_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.post("/devlog/99999/restore", headers=superuser_token_headers)
    assert response.status_code == 404
    assert "DevLog entry not found" in response.json()["detail"]

def test_restore_devlog_api_not_archived_error(
    client: TestClient, superuser_token_headers: dict, api_devlog_entry_set: dict
):
    active_entry = api_devlog_entry_set["User1 Log for Project1 Task1 (Recent)"]
    assert active_entry.is_deleted is False

    response = client.post(f"/devlog/{active_entry.id}/restore", headers=superuser_token_headers)
    assert response.status_code == 400
    assert "DevLog entry is not archived" in response.json()["detail"]

def test_restore_devlog_api_unauthenticated(client: TestClient, api_devlog_entry_set: dict):
    entry_to_restore = api_devlog_entry_set["User1 Deleted Log (Oldest)"]
    response = client.post(f"/devlog/{entry_to_restore.id}/restore")
    assert response.status_code == 401

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.settings import settings as app_settings
from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.models.task import Task as TaskModel
from app.schemas.task import TaskCreate, TaskRead
from app.crud.project import create_project as crud_create_project # To create parent projects
from app.crud.task import create_task as crud_create_task, get_task # For test setup and verification
from app.tests.crud.test_project_crud import MOCKED_CUSTOM_FIELDS_SCHEMA # For patching
from unittest.mock import patch
from datetime import date, timedelta, datetime, timezone # Added datetime, timezone


@pytest.fixture
def project_for_normal_user(db: Session, test_user: UserModel) -> ProjectModel:
    project_data = {"name": f"UserProject-{uuid.uuid4().hex[:4]}", "author_id": test_user.id}
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', {}):
        return crud_create_project(db, project_data)

@pytest.fixture
def project_for_superuser(db: Session, test_superuser: UserModel) -> ProjectModel:
    project_data = {"name": f"SuperuserProject-{uuid.uuid4().hex[:4]}", "author_id": test_superuser.id}
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', {}):
        return crud_create_project(db, project_data)

@pytest.fixture
def task_api_data_factory(): # Renamed to indicate it's a factory
    def _task_api_data(project_id: int, task_status: str = "todo"):
        return {
            "title": f"API Task {uuid.uuid4().hex[:6]}",
            "description": "Task created via API test.",
            "project_id": project_id,
            "deadline": (date.today() + timedelta(days=10)).isoformat(),
            "priority": 3,
            "tags": ["api_task"],
            "task_status": task_status
        }
    return _task_api_data

# --- Tests for POST /tasks/ ---

def test_create_task_api_success_normal_user(
    client: TestClient, normal_user_token_headers: dict,
    project_for_normal_user: ProjectModel, task_api_data_factory: callable, db: Session
):
    project_id_val = project_for_normal_user.id # Capture ID early
    payload = task_api_data_factory(project_id_val)

    response = client.post("/tasks/", json=payload, headers=normal_user_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["project_id"] == project_id_val

    task_in_db = db.query(TaskModel).filter(TaskModel.id == data["id"]).first()
    assert task_in_db is not None
    assert task_in_db.title == payload["title"]

def test_create_task_api_success_superuser_for_any_project(
    client: TestClient, superuser_token_headers: dict,
    project_for_normal_user: ProjectModel, task_api_data_factory: callable, db: Session
):
    project_id_val = project_for_normal_user.id # Capture ID early
    # Superuser creates task in normal_user's project
    payload = task_api_data_factory(project_id_val)
    payload["title"] = f"Superuser Task in UserProj {uuid.uuid4().hex[:4]}"

    response = client.post("/tasks/", json=payload, headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["project_id"] == project_id_val

def test_create_task_api_forbidden_for_normal_user_in_others_project(
    client: TestClient, normal_user_token_headers: dict,
    project_for_superuser: ProjectModel, task_api_data_factory: callable
):
    project_id_val = project_for_superuser.id # Capture ID early
    # Normal user tries to create task in superuser's project
    payload = task_api_data_factory(project_id_val)
    payload["title"] = f"User Task in SuperProj Attempt {uuid.uuid4().hex[:4]}"

    response = client.post("/tasks/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Not enough permissions for the parent project" in response.json()["detail"]

def test_create_task_api_project_not_found(
    client: TestClient, normal_user_token_headers: dict, task_api_data_factory: callable
):
    # Use factory, but project_id will be overridden
    payload = task_api_data_factory(0) # Dummy project_id, will be replaced
    payload["project_id"] = 99999 # Non-existent project

    response = client.post("/tasks/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 404
    assert "Project with id 99999 not found" in response.json()["detail"]

def test_create_task_api_missing_title(
    client: TestClient, normal_user_token_headers: dict,
    project_for_normal_user: ProjectModel, task_api_data_factory: callable
):
    project_id_val = project_for_normal_user.id # Capture ID
    payload = task_api_data_factory(project_id_val)
    payload["title"] = ""

    response = client.post("/tasks/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 400 # CRUD validation
    assert "Title is required" in response.json()["detail"]

def test_create_task_api_past_deadline(
    client: TestClient, normal_user_token_headers: dict,
    project_for_normal_user: ProjectModel, task_api_data_factory: callable
):
    project_id_val = project_for_normal_user.id # Capture ID
    payload = task_api_data_factory(project_id_val)
    payload["deadline"] = (date.today() - timedelta(days=1)).isoformat()

    response = client.post("/tasks/", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 400 # CRUD validation
    assert "Deadline cannot be in the past" in response.json()["detail"]

# --- Fixture for a set of tasks for API list tests ---
@pytest.fixture
def api_task_set(db: Session, project_for_normal_user: ProjectModel, project_for_superuser: ProjectModel, test_user: UserModel, test_superuser: UserModel):
    from app.crud.task import create_task as crud_create_task # Renamed to avoid conflict

    # Patch schema for task creation within this fixture
    with patch('app.crud.task.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        tasks_data = [
            # Tasks for project_for_normal_user (owned by test_user)
            {"title": f"UserTask Alpha {uuid.uuid4().hex[:4]}", "project_id": project_for_normal_user.id, "task_status": "todo", "tags": ["frontend"], "priority": 1, "assignees": [{"user_id": test_user.id, "name": test_user.full_name or "Test User", "role": "developer"}]},
            {"title": f"UserTask Beta {uuid.uuid4().hex[:4]}", "project_id": project_for_normal_user.id, "task_status": "inprogress", "tags": ["backend"]}, # No assignees here
            {"title": f"UserTask Gamma (Archived) {uuid.uuid4().hex[:4]}", "project_id": project_for_normal_user.id, "task_status": "done", "is_deleted": True},
            # Tasks for project_for_superuser (owned by test_superuser)
            {"title": f"SuperTask Omega {uuid.uuid4().hex[:4]}", "project_id": project_for_superuser.id, "task_status": "todo", "tags": ["infra"], "is_favorite": True},
            {"title": f"SuperTask Zeta (Archived) {uuid.uuid4().hex[:4]}", "project_id": project_for_superuser.id, "task_status": "archived", "is_deleted": True},
        ]
        created_tasks = []
        for data in tasks_data:
            is_del = data.pop("is_deleted", False)
            task = crud_create_task(db, data)
            if is_del:
                task.is_deleted = True
                task.deleted_at = datetime.now(timezone.utc) # Ensure datetime, timezone imported
                task.task_status = data.get("task_status", "archived")
                db.commit()
                db.refresh(task)
            created_tasks.append(task)
    return created_tasks

# --- Tests for GET /tasks/ (list_tasks) ---
def test_list_tasks_normal_user_for_own_project(client: TestClient, normal_user_token_headers: dict, project_for_normal_user: ProjectModel, api_task_set):
    response = client.get(f"/tasks/?project_id={project_for_normal_user.id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    tasks = response.json()
    # UserTask Alpha, UserTask Beta (Gamma is archived)
    assert len(tasks) == 2
    for task_json in tasks:
        assert task_json["project_id"] == project_for_normal_user.id

def test_list_tasks_normal_user_no_project_id_forbidden(client: TestClient, normal_user_token_headers: dict):
    response = client.get("/tasks/", headers=normal_user_token_headers)
    assert response.status_code == 403
    assert "Access to all tasks is restricted" in response.json()["detail"]

def test_list_tasks_normal_user_for_others_project_forbidden(client: TestClient, normal_user_token_headers: dict, project_for_superuser: ProjectModel):
    response = client.get(f"/tasks/?project_id={project_for_superuser.id}", headers=normal_user_token_headers)
    assert response.status_code == 403 # From _check_project_permission_and_get_project
    assert "Not enough permissions for the parent project" in response.json()["detail"]

def test_list_tasks_superuser_for_specific_project(client: TestClient, superuser_token_headers: dict, project_for_normal_user: ProjectModel, api_task_set):
    response = client.get(f"/tasks/?project_id={project_for_normal_user.id}", headers=superuser_token_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2 # UserTask Alpha, UserTask Beta

def test_list_tasks_superuser_all_projects_default(client: TestClient, superuser_token_headers: dict, api_task_set):
    response = client.get("/tasks/", headers=superuser_token_headers) # No project_id
    assert response.status_code == 200
    tasks = response.json()
    # UserTask Alpha, UserTask Beta, SuperTask Omega (3 non-archived)
    assert len(tasks) == 3

def test_list_tasks_superuser_show_archived_all_projects(client: TestClient, superuser_token_headers: dict, api_task_set):
    response = client.get("/tasks/?show_archived=true", headers=superuser_token_headers)
    assert response.status_code == 200
    assert len(response.json()) == 5 # All tasks from fixture

def test_list_tasks_superuser_show_archived_for_project(client: TestClient, superuser_token_headers: dict, project_for_normal_user: ProjectModel, api_task_set):
    response = client.get(f"/tasks/?project_id={project_for_normal_user.id}&show_archived=true", headers=superuser_token_headers)
    assert response.status_code == 200
    tasks = response.json()
    # UserTask Alpha, Beta, Gamma (archived)
    assert len(tasks) == 3

def test_list_tasks_filter_status(client: TestClient, superuser_token_headers: dict, project_for_normal_user: ProjectModel, api_task_set):
    response = client.get(f"/tasks/?project_id={project_for_normal_user.id}&task_status=inprogress", headers=superuser_token_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert "UserTask Beta" in tasks[0]["title"]

def test_list_tasks_filter_tag(client: TestClient, superuser_token_headers: dict, project_for_normal_user: ProjectModel, api_task_set):
    response = client.get(f"/tasks/?project_id={project_for_normal_user.id}&tag=frontend", headers=superuser_token_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert "UserTask Alpha" in tasks[0]["title"]

# --- Tests for GET /tasks/{task_id} ---
def test_get_one_task_success_normal_user(client: TestClient, normal_user_token_headers: dict, api_task_set, test_user: UserModel, project_for_normal_user: ProjectModel):
    # Find a task belonging to project_for_normal_user
    task_to_get = None
    for t in api_task_set:
        if t.project_id == project_for_normal_user.id and not t.is_deleted:
            task_to_get = t
            break
    assert task_to_get is not None, "No suitable task found for project_for_normal_user"

    response = client.get(f"/tasks/{task_to_get.id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_to_get.id
    assert data["title"] == task_to_get.title
    assert data["project_id"] == project_for_normal_user.id

def test_get_one_task_superuser_for_any_project(client: TestClient, superuser_token_headers: dict, api_task_set, project_for_normal_user: ProjectModel):
    task_to_get = None
    for t in api_task_set:
        if t.project_id == project_for_normal_user.id and not t.is_deleted: # Get task from normal user's project
            task_to_get = t
            break
    assert task_to_get is not None

    response = client.get(f"/tasks/{task_to_get.id}", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_to_get.id

def test_get_one_task_forbidden_for_normal_user_on_others_project(client: TestClient, normal_user_token_headers: dict, api_task_set, project_for_superuser: ProjectModel):
    task_on_superuser_project = None
    for t in api_task_set:
        if t.project_id == project_for_superuser.id and not t.is_deleted:
            task_on_superuser_project = t
            break
    assert task_on_superuser_project is not None, "No task found for project_for_superuser"

    response = client.get(f"/tasks/{task_on_superuser_project.id}", headers=normal_user_token_headers)
    assert response.status_code == 403 # Due to _check_project_permission_and_get_project
    assert "Not enough permissions for the parent project" in response.json()["detail"]

def test_get_one_task_not_found(client: TestClient, normal_user_token_headers: dict):
    response = client.get("/tasks/99999", headers=normal_user_token_headers)
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]

def test_get_one_task_soft_deleted_not_found_default(client: TestClient, normal_user_token_headers: dict, api_task_set, project_for_normal_user: ProjectModel, db: Session):
    # Find an archived task for project_for_normal_user
    archived_task = None
    for t in api_task_set:
        if t.project_id == project_for_normal_user.id and t.is_deleted:
            archived_task = t
            break
    assert archived_task is not None, "No archived task found for project_for_normal_user in fixture"

    response = client.get(f"/tasks/{archived_task.id}", headers=normal_user_token_headers)
    assert response.status_code == 404 # get_task by default doesn't find deleted tasks
    assert "Task not found" in response.json()["detail"]

# --- Tests for PATCH /tasks/{task_id} (update_one_task) ---
@pytest.fixture
def task_for_api_update(db: Session, project_for_normal_user: ProjectModel, task_api_data_factory: callable) -> TaskModel:
    # Create a task owned by test_user (via project_for_normal_user)
    task_data = task_api_data_factory(project_for_normal_user.id)
    task_data["title"] = f"TaskToUpdate-{uuid.uuid4().hex[:4]}"
    with patch('app.crud.task.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        task = crud_create_task(db, task_data)
    return task

def test_update_task_api_by_author_success(client: TestClient, normal_user_token_headers: dict, task_for_api_update: TaskModel, db: Session):
    update_data = {
        "title": "Updated Task API Title",
        "description": "Updated via API patch.",
        "task_status": "done",
        "priority": 1,
        "tags": ["api_patched"]
    }
    response = client.patch(f"/tasks/{task_for_api_update.id}", json=update_data, headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task API Title"
    assert data["description"] == "Updated via API patch."
    assert data["task_status"] == "done"
    assert data["priority"] == 1
    assert "api_patched" in data["tags"]

def test_update_task_api_partial_by_author(client: TestClient, normal_user_token_headers: dict, task_for_api_update: TaskModel):
    update_data = {"task_status": "blocked"}
    response = client.patch(f"/tasks/{task_for_api_update.id}", json=update_data, headers=normal_user_token_headers)
    assert response.status_code == 200
    assert response.json()["task_status"] == "blocked"

def test_update_task_api_by_superuser_on_others_task(
    client: TestClient, superuser_token_headers: dict, task_for_api_update: TaskModel, # task_for_api_update is on normal_user's project
):
    update_data = {"title": "Superuser Updated This Task"}
    response = client.patch(f"/tasks/{task_for_api_update.id}", json=update_data, headers=superuser_token_headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Superuser Updated This Task"

def test_update_task_api_forbidden_for_normal_user_on_others_task(
    client: TestClient, normal_user_token_headers: dict,
    project_for_superuser: ProjectModel, # A project belonging to superuser
    task_api_data_factory: callable, db: Session
):
    # Create a task in superuser's project
    task_in_superuser_project_data = task_api_data_factory(project_for_superuser.id)
    task_in_superuser_project_data["title"] = f"TaskInSuperuserProj-{uuid.uuid4().hex[:4]}"
    with patch('app.crud.task.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        task_to_try_update = crud_create_task(db, task_in_superuser_project_data)

    update_data = {"title": "Attempted Update by Normal User"}
    response = client.patch(f"/tasks/{task_to_try_update.id}", json=update_data, headers=normal_user_token_headers)
    assert response.status_code == 403 # Permission denied on parent project

def test_update_task_api_not_found(client: TestClient, normal_user_token_headers: dict):
    response = client.patch("/tasks/99999", json={"title": "Not Found Task"}, headers=normal_user_token_headers)
    assert response.status_code == 404

def test_update_task_api_validation_error_empty_title(client: TestClient, normal_user_token_headers: dict, task_for_api_update: TaskModel):
    update_data = {"title": ""}
    response = client.patch(f"/tasks/{task_for_api_update.id}", json=update_data, headers=normal_user_token_headers)
    assert response.status_code == 400 # From CRUD TaskValidationError
    assert "Task title is required" in response.json()["detail"] # Corrected message

# --- Tests for DELETE /tasks/{task_id} (delete_task) ---
def test_delete_task_api_by_author_success(client: TestClient, normal_user_token_headers: dict, task_for_api_update: TaskModel, db: Session):
    task_id_to_delete = task_for_api_update.id # task_for_api_update is owned by normal_user (test_user)

    response = client.delete(f"/tasks/{task_id_to_delete}", headers=normal_user_token_headers)
    assert response.status_code == 200
    assert response.json()["detail"] == "Task archived"

    deleted_task_from_db = get_task(db, task_id_to_delete, include_deleted=True) # Use CRUD get_task
    assert deleted_task_from_db.is_deleted is True
    assert deleted_task_from_db.task_status == "archived"

def test_delete_task_api_forbidden_for_normal_user_on_others_project(
    client: TestClient, normal_user_token_headers: dict, project_for_superuser: ProjectModel,
    task_api_data_factory: callable, db: Session
):
    # Create a task in superuser's project
    task_data = task_api_data_factory(project_for_superuser.id)
    with patch('app.crud.task.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        task_on_superuser_project = crud_create_task(db, task_data)

    response = client.delete(f"/tasks/{task_on_superuser_project.id}", headers=normal_user_token_headers)
    assert response.status_code == 403 # Permission denied on parent project

def test_delete_task_api_not_found(client: TestClient, normal_user_token_headers: dict):
    response = client.delete("/tasks/99999", headers=normal_user_token_headers)
    assert response.status_code == 404

def test_delete_task_api_already_deleted(client: TestClient, normal_user_token_headers: dict, task_for_api_update: TaskModel, db: Session):
    task_id = task_for_api_update.id
    # First delete
    client.delete(f"/tasks/{task_id}", headers=normal_user_token_headers)

    # Attempt second delete
    response = client.delete(f"/tasks/{task_id}", headers=normal_user_token_headers)
    assert response.status_code == 400 # TaskValidationError: "Task already archived."
    assert "Task already archived" in response.json()["detail"]

# --- Tests for POST /tasks/{task_id}/restore ---
def test_restore_task_api_by_author_success(client: TestClient, normal_user_token_headers: dict, task_for_api_update: TaskModel, db: Session):
    task_id = task_for_api_update.id
    # Ensure it's deleted first via API
    delete_response = client.delete(f"/tasks/{task_id}", headers=normal_user_token_headers)
    assert delete_response.status_code == 200

    response = client.post(f"/tasks/{task_id}/restore", headers=normal_user_token_headers)
    assert response.status_code == 200
    assert response.json()["detail"] == "Task restored"

    restored_task_from_db = get_task(db, task_id) # Should be active now
    assert restored_task_from_db.is_deleted is False
    assert restored_task_from_db.task_status == "todo"

def test_restore_task_api_not_deleted(client: TestClient, normal_user_token_headers: dict, task_for_api_update: TaskModel):
    task_id = task_for_api_update.id
    # The task_for_api_update fixture provides an active task.
    # No need to explicitly check its status here before calling the API.

    response = client.post(f"/tasks/{task_id}/restore", headers=normal_user_token_headers)
    assert response.status_code == 400 # TaskValidationError
    assert "is not archived/deleted" in response.json()["detail"]

def test_restore_task_api_not_found(client: TestClient, normal_user_token_headers: dict):
    response = client.post("/tasks/99999/restore", headers=normal_user_token_headers)
    assert response.status_code == 404


# TODO: Add more filter tests for get_all_tasks (search, deadline ranges, custom_fields, etc.)
# Also test custom fields for tasks via API
# Test unauthenticated access
# Test validation from TaskCreate schema (e.g. priority range)

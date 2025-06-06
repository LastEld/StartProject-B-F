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
from app.tests.crud.test_project_crud import MOCKED_CUSTOM_FIELDS_SCHEMA as MOCKED_PROJECT_CUSTOM_FIELDS_SCHEMA # Keep for project if needed, rename
from unittest.mock import patch
from datetime import date, timedelta, datetime, timezone
from http import HTTPStatus # Added HTTPStatus


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
    # For task_for_api_update, we'll use a task-specific mocked schema if needed in its tests
    # For now, fixture creates it with project's mocked schema, which is fine if no custom fields are set by default
    with patch('app.crud.task.CUSTOM_FIELDS_SCHEMA', {}): # Default to empty schema for this fixture if not testing CFs here
        task = crud_create_task(db, task_data)
    return task

# Define a Task-specific MOCKED_CUSTOM_FIELDS_SCHEMA
MOCKED_TASK_CUSTOM_FIELDS_SCHEMA = {
    "task_checkbox_field": {"type": "boolean", "required": False},
    "required_task_notes": {"type": "string", "required": True}
}

# --- Tests for Custom Fields in Tasks (Create and Update) ---

def test_create_task_with_custom_fields_success(
    client: TestClient, normal_user_token_headers: dict, project_for_normal_user: ProjectModel, db: Session, task_api_data_factory: callable
):
    payload = task_api_data_factory(project_for_normal_user.id)
    payload["custom_fields"] = {
        "task_checkbox_field": True,
        "required_task_notes": "This is a required note for the task."
    }

    with patch("app.crud.task.CUSTOM_FIELDS_SCHEMA", MOCKED_TASK_CUSTOM_FIELDS_SCHEMA):
        response = client.post("/tasks/", headers=normal_user_token_headers, json=payload)

    assert response.status_code == HTTPStatus.OK, response.text # API returns 200 OK for create
    data = response.json()
    new_task_id = data["id"]

    db_task = get_task(db, new_task_id)
    assert db_task is not None
    assert db_task.custom_fields["task_checkbox_field"] is True
    assert db_task.custom_fields["required_task_notes"] == "This is a required note for the task."

def test_create_task_custom_fields_validation_error_missing_required(
    client: TestClient, normal_user_token_headers: dict, project_for_normal_user: ProjectModel, task_api_data_factory: callable
):
    payload = task_api_data_factory(project_for_normal_user.id)
    payload["custom_fields"] = {"task_checkbox_field": False} # Missing "required_task_notes"

    with patch("app.crud.task.CUSTOM_FIELDS_SCHEMA", MOCKED_TASK_CUSTOM_FIELDS_SCHEMA):
        response = client.post("/tasks/", headers=normal_user_token_headers, json=payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.text # CRUD validation error
    assert "Missing required custom field 'required_task_notes'" in response.json()["detail"]

def test_create_task_custom_fields_validation_error_invalid_type(
    client: TestClient, normal_user_token_headers: dict, project_for_normal_user: ProjectModel, task_api_data_factory: callable
):
    payload = task_api_data_factory(project_for_normal_user.id)
    payload["custom_fields"] = {
        "task_checkbox_field": "not a boolean", # Invalid type
        "required_task_notes": "Valid note."
    }

    with patch("app.crud.task.CUSTOM_FIELDS_SCHEMA", MOCKED_TASK_CUSTOM_FIELDS_SCHEMA):
        response = client.post("/tasks/", headers=normal_user_token_headers, json=payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.text
    assert "Invalid type for field 'task_checkbox_field'" in response.json()["detail"]


def test_update_task_with_custom_fields_success(
    client: TestClient, normal_user_token_headers: dict, task_for_api_update: TaskModel, db: Session
):
    update_payload = {
        "custom_fields": {
            "task_checkbox_field": False,
            "required_task_notes": "Updated required notes."
        }
    }
    with patch("app.crud.task.CUSTOM_FIELDS_SCHEMA", MOCKED_TASK_CUSTOM_FIELDS_SCHEMA):
        response = client.patch(f"/tasks/{task_for_api_update.id}", headers=normal_user_token_headers, json=update_payload)

    assert response.status_code == HTTPStatus.OK, response.text
    db.refresh(task_for_api_update)
    assert task_for_api_update.custom_fields["task_checkbox_field"] is False
    assert task_for_api_update.custom_fields["required_task_notes"] == "Updated required notes."

def test_update_task_custom_fields_validation_error(
    client: TestClient, normal_user_token_headers: dict, task_for_api_update: TaskModel, db: Session
):
    update_payload = {
        "custom_fields": {
             "required_task_notes": 12345 # Invalid type
        }
    }
    # Ensure task initially has valid required field if schema is enforced on full custom_fields replacement
    task_for_api_update.custom_fields = {"required_task_notes": "initial valid note"}
    db.commit()

    with patch("app.crud.task.CUSTOM_FIELDS_SCHEMA", MOCKED_TASK_CUSTOM_FIELDS_SCHEMA):
        response = client.patch(f"/tasks/{task_for_api_update.id}", headers=normal_user_token_headers, json=update_payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.text
    assert "Invalid type for field 'required_task_notes'" in response.json()["detail"]

# --- End of Custom Fields Tests ---


# --- Enhanced Filter Tests for GET /tasks/ ---

def test_list_tasks_filter_search_title(client: TestClient, superuser_token_headers: dict, api_task_set: list):
    # Assuming "Alpha" is unique enough in the titles of api_task_set for this test
    # UserTask Alpha is created by api_task_set
    search_term = "Alpha"
    response = client.get(f"/tasks/?search={search_term}", headers=superuser_token_headers)
    assert response.status_code == HTTPStatus.OK, response.text
    tasks = response.json()
    assert len(tasks) > 0
    found_alpha = False
    for task in tasks:
        # Search can be on title and description. This test assumes title primarily.
        if search_term.lower() in task["title"].lower():
            found_alpha = True
            break
    assert found_alpha, f"Task with '{search_term}' in title not found."

def test_list_tasks_filter_deadline_before(client: TestClient, superuser_token_headers: dict, db: Session, project_for_superuser: ProjectModel):
    today = datetime.now(timezone.utc).date()
    task1_deadline_val = today + timedelta(days=2)
    task2_deadline_val = today + timedelta(days=8)

    with patch('app.crud.task.CUSTOM_FIELDS_SCHEMA', {}): # No custom fields needed for this
        task1 = crud_create_task(db, {"title": "DeadlineFilter Before T1", "project_id": project_for_superuser.id, "deadline": task1_deadline_val.isoformat(), "task_status": "todo"})
        crud_create_task(db, {"title": "DeadlineFilter Before T2", "project_id": project_for_superuser.id, "deadline": task2_deadline_val.isoformat(), "task_status": "todo"})

    filter_date_val = today + timedelta(days=5) # Should include task1, exclude task2
    response = client.get(f"/tasks/?deadline_before={filter_date_val.isoformat()}&project_id={project_for_superuser.id}", headers=superuser_token_headers)
    assert response.status_code == HTTPStatus.OK, response.text
    tasks_json = response.json()

    task_titles = [t["title"] for t in tasks_json]
    assert "DeadlineFilter Before T1" in task_titles
    assert "DeadlineFilter Before T2" not in task_titles
    for task_json_item in tasks_json:
        if "DeadlineFilter Before T" in task_json_item["title"]: # Only check our specific test tasks
            task_deadline = datetime.fromisoformat(task_json_item["deadline"].split("T")[0]).date()
            assert task_deadline < filter_date_val

def test_list_tasks_filter_deadline_after(client: TestClient, superuser_token_headers: dict, db: Session, project_for_superuser: ProjectModel):
    today = datetime.now(timezone.utc).date()
    task1_deadline_val = today + timedelta(days=2)
    task2_deadline_val = today + timedelta(days=8)

    with patch('app.crud.task.CUSTOM_FIELDS_SCHEMA', {}):
        crud_create_task(db, {"title": "DeadlineFilter After T1", "project_id": project_for_superuser.id, "deadline": task1_deadline_val.isoformat(), "task_status": "todo"})
        task2 = crud_create_task(db, {"title": "DeadlineFilter After T2", "project_id": project_for_superuser.id, "deadline": task2_deadline_val.isoformat(), "task_status": "todo"})

    filter_date_val = today + timedelta(days=5) # Should exclude task1, include task2
    response = client.get(f"/tasks/?deadline_after={filter_date_val.isoformat()}&project_id={project_for_superuser.id}", headers=superuser_token_headers)
    assert response.status_code == HTTPStatus.OK, response.text
    tasks_json = response.json()

    task_titles = [t["title"] for t in tasks_json]
    assert "DeadlineFilter After T1" not in task_titles
    assert "DeadlineFilter After T2" in task_titles
    for task_json_item in tasks_json:
         if "DeadlineFilter After T" in task_json_item["title"]:
            task_deadline = datetime.fromisoformat(task_json_item["deadline"].split("T")[0]).date()
            assert task_deadline > filter_date_val


def test_list_tasks_filter_deadline_range(client: TestClient, superuser_token_headers: dict, db: Session, project_for_superuser: ProjectModel):
    today = datetime.now(timezone.utc).date()
    task_early_val = today + timedelta(days=1)
    task_mid_val = today + timedelta(days=7)
    task_late_val = today + timedelta(days=12)

    with patch('app.crud.task.CUSTOM_FIELDS_SCHEMA', {}):
        crud_create_task(db, {"title": "DeadlineRange Early", "project_id": project_for_superuser.id, "deadline": task_early_val.isoformat(), "task_status": "todo"})
        task_mid_obj = crud_create_task(db, {"title": "DeadlineRange Mid", "project_id": project_for_superuser.id, "deadline": task_mid_val.isoformat(), "task_status": "todo"})
        crud_create_task(db, {"title": "DeadlineRange Late", "project_id": project_for_superuser.id, "deadline": task_late_val.isoformat(), "task_status": "todo"})

    after_filter_date = today + timedelta(days=5)
    before_filter_date = today + timedelta(days=10)

    response = client.get(f"/tasks/?deadline_after={after_filter_date.isoformat()}&deadline_before={before_filter_date.isoformat()}&project_id={project_for_superuser.id}", headers=superuser_token_headers)
    assert response.status_code == HTTPStatus.OK, response.text
    tasks_json = response.json()

    task_titles = [t["title"] for t in tasks_json]
    assert "DeadlineRange Early" not in task_titles
    assert "DeadlineRange Mid" in task_titles
    assert "DeadlineRange Late" not in task_titles
    for task_json_item in tasks_json:
        if "DeadlineRange" in task_json_item["title"]:
            task_deadline = datetime.fromisoformat(task_json_item["deadline"].split("T")[0]).date()
            assert task_deadline > after_filter_date and task_deadline < before_filter_date


def test_list_tasks_filter_parent_task_id(client: TestClient, superuser_token_headers: dict, db: Session, project_for_superuser: ProjectModel):
    with patch('app.crud.task.CUSTOM_FIELDS_SCHEMA', {}):
        parent_task = crud_create_task(db, {"title": "Parent Task For Filter", "project_id": project_for_superuser.id, "task_status": "todo"})
        sub_task = crud_create_task(db, {"title": "Sub-task For Filter", "project_id": project_for_superuser.id, "parent_task_id": parent_task.id, "task_status": "todo"})
        crud_create_task(db, {"title": "Another Task (Not Sub)", "project_id": project_for_superuser.id, "task_status": "todo"})

    response = client.get(f"/tasks/?parent_task_id={parent_task.id}", headers=superuser_token_headers)
    assert response.status_code == HTTPStatus.OK, response.text
    tasks_json = response.json()
    assert len(tasks_json) == 1
    assert tasks_json[0]["id"] == sub_task.id
    assert tasks_json[0]["title"] == "Sub-task For Filter"

def test_list_tasks_filter_assignee_id(client: TestClient, superuser_token_headers: dict, api_task_set: list, test_user: UserModel):
    assigned_task_in_fixture = None
    for task_fixture_item in api_task_set: # Corrected variable name
        if hasattr(task_fixture_item, 'assignees') and task_fixture_item.assignees and any(assignee_info['user_id'] == test_user.id for assignee_info in task_fixture_item.assignees):
             assigned_task_in_fixture = task_fixture_item
             break
    assert assigned_task_in_fixture is not None, "Task assigned to test_user not found in api_task_set fixture"

    response = client.get(f"/tasks/?assignee_id={test_user.id}", headers=superuser_token_headers)
    assert response.status_code == HTTPStatus.OK, response.text
    tasks_json = response.json()

    assert len(tasks_json) > 0
    found_in_response = False
    for task_resp_item in tasks_json:
        if task_resp_item["id"] == assigned_task_in_fixture.id:
            found_in_response = True
            if "assignees" in task_resp_item and task_resp_item["assignees"]:
                 assert any(a["user_id"] == test_user.id for a in task_resp_item["assignees"])
            break
    assert found_in_response, f"Task ID {assigned_task_in_fixture.id} expected but not found by assignee_id."


# --- Other Suggested Tests ---

def test_list_tasks_unauthenticated(client: TestClient):
    response = client.get("/tasks/")
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.text

def test_create_task_invalid_priority(
    client: TestClient, normal_user_token_headers: dict, project_for_normal_user: ProjectModel, task_api_data_factory: callable
):
    payload_low = task_api_data_factory(project_for_normal_user.id)
    payload_low["priority"] = 0

    response_low = client.post("/tasks/", json=payload_low, headers=normal_user_token_headers)
    assert response_low.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, response_low.text

    payload_high = task_api_data_factory(project_for_normal_user.id)
    payload_high["priority"] = 6

    response_high = client.post("/tasks/", json=payload_high, headers=normal_user_token_headers)
    assert response_high.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, response_high.text


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

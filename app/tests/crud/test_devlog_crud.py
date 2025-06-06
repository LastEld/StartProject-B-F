import pytest
import uuid
from sqlalchemy.orm import Session
from app.crud import devlog as crud_devlog
from app.crud.project import create_project as crud_create_project
from app.crud.task import create_task as crud_create_task
from app.models.devlog import DevLogEntry
from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.models.task import Task as TaskModel
from app.core.exceptions import DevLogNotFound, DevLogValidationError, ProjectNotFound, TaskNotFound
from app.core.custom_fields import CUSTOM_FIELDS_SCHEMA # For testing custom field validation
from datetime import datetime, timedelta, timezone
import time # For time.sleep

# --- Fixtures ---

@pytest.fixture
def test_project_for_devlog(db: Session, test_user: UserModel) -> ProjectModel:
    project_data = {
        "name": f"Devlog Test Project {uuid.uuid4().hex[:4]}",
        "author_id": test_user.id,
        "description": "Project for devlog entries"
    }
    return crud_create_project(db=db, data=project_data)

@pytest.fixture
def test_task_for_devlog(db: Session, test_user: UserModel, test_project_for_devlog: ProjectModel) -> TaskModel:
    task_data = {
        "title": f"Devlog Test Task {uuid.uuid4().hex[:4]}",
        "project_id": test_project_for_devlog.id,
        "author_id": test_user.id # Assuming tasks also have an author
    }
    # Ensure task CRUD can handle author_id if it's part of its creation logic
    # For now, assuming a simplified create_task or that author_id is set by context in API
    # If create_task strictly needs current_user, this fixture setup might need adjustment
    # For CRUD tests, directly providing author_id if model supports it.
    # The provided crud_task.create_task does not take author_id, it's set by API layer.
    # Let's assume for CRUD test, we can set it if model allows or skip if not part of TaskModel direct fields.
    # For this test, we'll assume TaskModel has author_id field and can be set.
    # If not, this part needs adjustment or task author isn't relevant for devlog.
    # The current Task model in other tests does not have author_id.
    # We'll proceed without task author_id for now.
    del task_data["author_id"] # Correcting based on existing task model
    return crud_create_task(db=db, data=task_data)


@pytest.fixture
def devlog_data_factory(test_user: UserModel, test_project_for_devlog: ProjectModel, test_task_for_devlog: TaskModel):
    def _factory(**kwargs):
        unique_suffix = uuid.uuid4().hex[:6]
        data = {
            "content": f"This is a test devlog entry {unique_suffix}.",
            "entry_type": "note",
            # author_id is passed separately to create_entry
            "project_id": test_project_for_devlog.id,
            "task_id": test_task_for_devlog.id,
            "tags": ["test_tag", "devlog"],
            "custom_fields": {}, # Default to empty for general tests
            "attachments": [{"filename": "test.txt", "url": "/path/to/test.txt"}],
            "ai_notes": "AI generated notes for this entry."
        }
        data.update(kwargs)
        return data
    return _factory

# --- Tests for create_entry ---

def test_create_devlog_entry_success_full(db: Session, test_user: UserModel, devlog_data_factory: callable):
    entry_data = devlog_data_factory()
    created_entry = crud_devlog.create_entry(db, entry_data, author_id=test_user.id)

    assert created_entry is not None
    assert created_entry.id is not None
    assert created_entry.content == entry_data["content"]
    assert created_entry.author_id == test_user.id
    assert created_entry.project_id == entry_data["project_id"]
    assert created_entry.task_id == entry_data["task_id"]
    assert created_entry.entry_type == entry_data["entry_type"]
    assert sorted(created_entry.tags) == sorted(entry_data["tags"])
    assert created_entry.custom_fields == entry_data["custom_fields"] # Will be {} if factory default is used
    assert created_entry.attachments == entry_data["attachments"]
    assert created_entry.ai_notes == entry_data["ai_notes"]
    assert created_entry.is_deleted is False

def test_create_devlog_entry_minimal_only_content_author(db: Session, test_user: UserModel, devlog_data_factory: callable):
    entry_data = devlog_data_factory(project_id=None, task_id=None, tags=None, custom_fields=None, attachments=None, ai_notes=None)
    minimal_data = {"content": entry_data["content"]} # entry_type defaults

    created_entry = crud_devlog.create_entry(db, minimal_data, author_id=test_user.id)
    assert created_entry is not None
    assert created_entry.content == minimal_data["content"]
    assert created_entry.author_id == test_user.id
    assert created_entry.project_id is None
    assert created_entry.task_id is None
    assert created_entry.entry_type == "note" # default
    assert created_entry.tags == [] # default
    assert created_entry.custom_fields == {} # default

def test_create_devlog_entry_with_project_only(db: Session, test_user: UserModel, test_project_for_devlog: ProjectModel, devlog_data_factory: callable):
    entry_data = devlog_data_factory(task_id=None) # Remove task_id
    data_for_create = {k: v for k, v in entry_data.items() if k != "task_id"}

    created_entry = crud_devlog.create_entry(db, data_for_create, author_id=test_user.id)
    assert created_entry.project_id == test_project_for_devlog.id
    assert created_entry.task_id is None

def test_create_devlog_entry_error_empty_content(db: Session, test_user: UserModel, devlog_data_factory: callable):
    entry_data = devlog_data_factory(content=" ")
    with pytest.raises(DevLogValidationError, match="DevLog entry content cannot be empty."):
        crud_devlog.create_entry(db, entry_data, author_id=test_user.id)

def test_create_devlog_entry_error_invalid_project_id(db: Session, test_user: UserModel, devlog_data_factory: callable):
    entry_data = devlog_data_factory(project_id=99999) # Non-existent project
    with pytest.raises(ProjectNotFound): # CRUD create_entry re-raises this
        crud_devlog.create_entry(db, entry_data, author_id=test_user.id)

def test_create_devlog_entry_error_invalid_task_id(db: Session, test_user: UserModel, devlog_data_factory: callable):
    entry_data = devlog_data_factory(task_id=99999) # Non-existent task
    with pytest.raises(TaskNotFound): # CRUD create_entry re-raises this
        crud_devlog.create_entry(db, entry_data, author_id=test_user.id)

# Mock CUSTOM_FIELDS_SCHEMA for testing custom field validation if not already defined elsewhere
# For this test, assume CUSTOM_FIELDS_SCHEMA = {"story_points": {"type": "int", "validator": lambda x: isinstance(x, int)}}
# This should ideally be part of a conftest.py or shared testing utility if used across many test files.
# If CUSTOM_FIELDS_SCHEMA is empty by default, these tests might not be meaningful without mocking.

def test_create_devlog_entry_error_invalid_custom_field_value(db: Session, test_user: UserModel, devlog_data_factory: callable, monkeypatch):
    # Assuming CUSTOM_FIELDS_SCHEMA is like: {"story_points": {"type": "int", "validator": lambda x: isinstance(x, int)}}
    # We need to ensure CUSTOM_FIELDS_SCHEMA is populated for this test to be effective.
    # If it's imported from app.core.custom_fields, we can monkeypatch it for this test.

    mock_schema = {
        "story_points": {"type": "int", "validator": lambda x: isinstance(x, int)},
        "priority_level": {"type": "str", "validator": lambda x: isinstance(x, str) and x in ["low", "medium", "high"]}
    }
    monkeypatch.setattr(crud_devlog, 'CUSTOM_FIELDS_SCHEMA', mock_schema)

    entry_data = devlog_data_factory(custom_fields={"story_points": "not-an-int"})
    with pytest.raises(DevLogValidationError, match="Invalid value for 'story_points'"):
        crud_devlog.create_entry(db, entry_data, author_id=test_user.id)

def test_create_devlog_entry_error_unknown_custom_field(db: Session, test_user: UserModel, devlog_data_factory: callable, monkeypatch):
    mock_schema = {"known_field": {"type": "str", "validator": lambda x: isinstance(x, str)}}
    monkeypatch.setattr(crud_devlog, 'CUSTOM_FIELDS_SCHEMA', mock_schema)

    entry_data = devlog_data_factory(custom_fields={"unknown_field": "some_value"})
    with pytest.raises(DevLogValidationError, match="Unknown custom field: unknown_field"):
        crud_devlog.create_entry(db, entry_data, author_id=test_user.id)

# --- Tests for get_entry ---

def test_get_devlog_entry_success(db: Session, test_user: UserModel, devlog_data_factory: callable):
    entry_data = devlog_data_factory()
    created_entry = crud_devlog.create_entry(db, entry_data, author_id=test_user.id)

    fetched_entry = crud_devlog.get_entry(db, created_entry.id)
    assert fetched_entry is not None
    assert fetched_entry.id == created_entry.id
    assert fetched_entry.content == entry_data["content"]
    assert fetched_entry.author_id == test_user.id
    assert fetched_entry.project_id == entry_data["project_id"]
    assert fetched_entry.task_id == entry_data["task_id"]
    assert fetched_entry.entry_type == entry_data["entry_type"]
    assert sorted(fetched_entry.tags) == sorted(entry_data["tags"])
    # Custom fields in factory are {} by default now, so this should match
    assert fetched_entry.custom_fields == entry_data.get("custom_fields", {})
    assert fetched_entry.attachments == entry_data.get("attachments", [])
    assert fetched_entry.ai_notes == entry_data.get("ai_notes")
    assert fetched_entry.is_deleted is False # Default state

def test_get_devlog_entry_not_found(db: Session):
    non_existent_id = uuid.uuid4().int & (1<<30)-1
    with pytest.raises(DevLogNotFound, match=f"DevLogEntry {non_existent_id} not found"):
        crud_devlog.get_entry(db, non_existent_id)

def test_get_devlog_entry_retrieves_soft_deleted_entry(db: Session, test_user: UserModel, devlog_data_factory: callable):
    # Based on current crud_devlog.get_entry implementation, it does not filter by is_deleted.
    entry_data = devlog_data_factory()
    created_entry = crud_devlog.create_entry(db, entry_data, author_id=test_user.id)

    # Manually soft-delete
    created_entry.is_deleted = True
    db.commit()
    db.refresh(created_entry)

    fetched_entry = crud_devlog.get_entry(db, created_entry.id)
    assert fetched_entry is not None
    assert fetched_entry.id == created_entry.id
    assert fetched_entry.is_deleted is True

# --- Fixture for a second project/task for update tests ---
@pytest.fixture
def another_project_for_devlog(db: Session, test_user: UserModel) -> ProjectModel:
    project_data = {
        "name": f"Another Devlog Test Project {uuid.uuid4().hex[:4]}",
        "author_id": test_user.id
    }
    return crud_create_project(db=db, data=project_data)

@pytest.fixture
def another_task_for_devlog(db: Session, test_user: UserModel, another_project_for_devlog: ProjectModel) -> TaskModel:
    task_data = {"title": f"Another Devlog Test Task {uuid.uuid4().hex[:4]}", "project_id": another_project_for_devlog.id}
    return crud_create_task(db=db, data=task_data)

# --- Tests for update_entry ---

def test_update_devlog_entry_success_all_fields(
    db: Session, test_user: UserModel, devlog_data_factory: callable,
    another_project_for_devlog: ProjectModel, another_task_for_devlog: TaskModel, monkeypatch
):
    entry_data = devlog_data_factory()
    created_entry = crud_devlog.create_entry(db, entry_data, author_id=test_user.id)
    db.refresh(created_entry) # Ensure created_at and updated_at are loaded
    original_updated_at = created_entry.updated_at

    # Mock CUSTOM_FIELDS_SCHEMA for this update test as well
    mock_schema = {
        "story_points": {"type": "int", "validator": lambda x: isinstance(x, int)},
        "priority_level": {"type": "str", "validator": lambda x: isinstance(x, str)},
        "mood": {"type": "str", "validator": lambda x: isinstance(x, str)} # New field for update
    }
    monkeypatch.setattr(crud_devlog, 'CUSTOM_FIELDS_SCHEMA', mock_schema)

    update_payload = {
        "content": "Updated content for the devlog entry.",
        "entry_type": "action",
        "project_id": another_project_for_devlog.id,
        "task_id": another_task_for_devlog.id,
        "tags": ["updated", "action_item"],
        "custom_fields": {"story_points": 8, "mood": "focused"}, # Modify one, add one
        "attachments": [{"filename": "updated.log", "url": "/logs/updated.log"}],
        "ai_notes": "Updated AI notes reflecting new content.",
        "edit_reason": "Content clarification and project reassignment."
    }

    time.sleep(0.01) # Ensure time difference for updated_at
    updated_entry = crud_devlog.update_entry(db, created_entry.id, update_payload)

    assert updated_entry is not None
    assert updated_entry.id == created_entry.id
    assert updated_entry.content == update_payload["content"]
    assert updated_entry.entry_type == update_payload["entry_type"]
    assert updated_entry.project_id == another_project_for_devlog.id
    assert updated_entry.task_id == another_task_for_devlog.id
    assert sorted(updated_entry.tags) == sorted(update_payload["tags"])
    # Custom fields update logic in CRUD is a merge: {**(entry.custom_fields or {}), **custom_fields_data}
    # Initial factory custom_fields is {}, so it becomes what's in update_payload
    assert updated_entry.custom_fields == update_payload["custom_fields"]
    assert updated_entry.attachments == update_payload["attachments"]
    assert updated_entry.ai_notes == update_payload["ai_notes"]
    assert updated_entry.edit_reason == update_payload["edit_reason"]
    assert updated_entry.updated_at >= original_updated_at # Using >= for safety with time resolution
    assert updated_entry.updated_at > original_updated_at # Expecting it to be greater due to sleep

def test_update_devlog_entry_unlink_project_and_task(db: Session, test_user: UserModel, devlog_data_factory: callable):
    entry = crud_devlog.create_entry(db, devlog_data_factory(), author_id=test_user.id)
    assert entry.project_id is not None
    assert entry.task_id is not None

    update_data = {"project_id": None, "task_id": None}
    updated_entry = crud_devlog.update_entry(db, entry.id, update_data)
    assert updated_entry.project_id is None
    assert updated_entry.task_id is None

def test_update_devlog_entry_clear_custom_fields(db: Session, test_user: UserModel, devlog_data_factory: callable, monkeypatch):
    # Setup with some custom fields
    mock_schema = {"initial_field": {"type": "str", "validator": lambda x: isinstance(x, str)}}
    monkeypatch.setattr(crud_devlog, 'CUSTOM_FIELDS_SCHEMA', mock_schema)
    entry = crud_devlog.create_entry(db, devlog_data_factory(custom_fields={"initial_field": "value"}), author_id=test_user.id)
    assert entry.custom_fields == {"initial_field": "value"}

    # Update with custom_fields: None (should clear to {})
    updated_entry = crud_devlog.update_entry(db, entry.id, {"custom_fields": None})
    assert updated_entry.custom_fields == {} # CRUD sets to {} if None is passed

def test_update_devlog_entry_not_found(db: Session):
    with pytest.raises(DevLogNotFound):
        crud_devlog.update_entry(db, 99999, {"content": "new content"})

def test_update_soft_deleted_devlog_entry_error(db: Session, test_user: UserModel, devlog_data_factory: callable):
    created_entry = crud_devlog.create_entry(db, devlog_data_factory(), author_id=test_user.id)
    # Manually soft-delete
    created_entry.is_deleted = True
    db.commit()

    with pytest.raises(DevLogValidationError, match="Cannot update an archived DevLog entry"):
        crud_devlog.update_entry(db, created_entry.id, {"content": "update attempt on deleted"})

def test_update_devlog_entry_invalid_project_id(db: Session, test_user: UserModel, devlog_data_factory: callable):
    created_entry = crud_devlog.create_entry(db, devlog_data_factory(), author_id=test_user.id)
    with pytest.raises(ProjectNotFound):
        crud_devlog.update_entry(db, created_entry.id, {"project_id": 99999})

def test_update_devlog_entry_invalid_task_id(db: Session, test_user: UserModel, devlog_data_factory: callable):
    created_entry = crud_devlog.create_entry(db, devlog_data_factory(), author_id=test_user.id)
    with pytest.raises(TaskNotFound):
        crud_devlog.update_entry(db, created_entry.id, {"task_id": 99999})

def test_update_devlog_entry_invalid_custom_field_value(db: Session, test_user: UserModel, devlog_data_factory: callable, monkeypatch):
    mock_schema = {"story_points": {"type": "int", "validator": lambda x: isinstance(x, int)}}
    monkeypatch.setattr(crud_devlog, 'CUSTOM_FIELDS_SCHEMA', mock_schema)
    created_entry = crud_devlog.create_entry(db, devlog_data_factory(custom_fields={}), author_id=test_user.id) # Start with no custom fields

    with pytest.raises(DevLogValidationError, match="Invalid value for 'story_points'"):
        crud_devlog.update_entry(db, created_entry.id, {"custom_fields": {"story_points": "not-an-int"}})

# --- Tests for soft_delete_entry ---

def test_soft_delete_devlog_entry_success(db: Session, test_user: UserModel, devlog_data_factory: callable):
    created_entry = crud_devlog.create_entry(db, devlog_data_factory(), author_id=test_user.id)
    db.refresh(created_entry)
    original_updated_at = created_entry.updated_at

    time.sleep(0.01) # Ensure timestamp difference
    result = crud_devlog.soft_delete_entry(db, created_entry.id)
    assert result is True

    deleted_entry = crud_devlog.get_entry(db, created_entry.id) # get_entry retrieves soft-deleted
    assert deleted_entry.is_deleted is True
    assert deleted_entry.updated_at > original_updated_at

def test_soft_delete_devlog_entry_not_found(db: Session):
    with pytest.raises(DevLogNotFound, match="not found for deletion"):
        crud_devlog.soft_delete_entry(db, 99999)

def test_soft_delete_devlog_entry_already_deleted(db: Session, test_user: UserModel, devlog_data_factory: callable):
    created_entry = crud_devlog.create_entry(db, devlog_data_factory(), author_id=test_user.id)
    crud_devlog.soft_delete_entry(db, created_entry.id) # First delete

    with pytest.raises(DevLogValidationError, match="DevLog entry already archived"):
        crud_devlog.soft_delete_entry(db, created_entry.id) # Attempt second delete

# --- Tests for restore_entry ---

def test_restore_devlog_entry_success(db: Session, test_user: UserModel, devlog_data_factory: callable):
    created_entry = crud_devlog.create_entry(db, devlog_data_factory(), author_id=test_user.id)
    crud_devlog.soft_delete_entry(db, created_entry.id) # Soft delete it

    db.refresh(created_entry) # Ensure is_deleted and updated_at are current
    time_when_deleted = created_entry.updated_at
    assert created_entry.is_deleted is True

    time.sleep(0.01)
    result = crud_devlog.restore_entry(db, created_entry.id)
    assert result is True

    restored_entry = crud_devlog.get_entry(db, created_entry.id)
    assert restored_entry.is_deleted is False
    assert restored_entry.updated_at > time_when_deleted

def test_restore_devlog_entry_not_found(db: Session):
    with pytest.raises(DevLogNotFound, match="not found for restore"):
        crud_devlog.restore_entry(db, 99999)

def test_restore_devlog_entry_not_deleted(db: Session, test_user: UserModel, devlog_data_factory: callable):
    created_entry = crud_devlog.create_entry(db, devlog_data_factory(), author_id=test_user.id)
    assert created_entry.is_deleted is False # Pre-condition

    with pytest.raises(DevLogValidationError, match="DevLog entry is not archived"):
        crud_devlog.restore_entry(db, created_entry.id)


# TODO: Add tests for get_entries

def test_devlog_placeholder(): # Placeholder
    assert True

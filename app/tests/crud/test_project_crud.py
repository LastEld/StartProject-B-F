import pytest
from sqlalchemy.orm import Session
import uuid # Added import for uuid
from app.crud.project import (
    create_project,
    get_project,
    get_all_projects,
    update_project,
    soft_delete_project,
    restore_project
)
from app.schemas.project import ProjectCreate, ProjectUpdate # Assuming these exist
from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.core.exceptions import ProjectValidationError, DuplicateProjectName, ProjectNotFound
from datetime import date, timedelta, datetime, timezone

# Mocking CUSTOM_FIELDS_SCHEMA for tests to avoid dependency on its exact state
# and to make tests for custom field validation more controlled.
from unittest.mock import patch

# A simple schema for testing custom fields validation logic in create_project
MOCKED_CUSTOM_FIELDS_SCHEMA = {
    "valid_text_field": {
        "type": "str",
        "validator": lambda v: isinstance(v, str) and len(v) < 100,
        "default": "",
        "label": "Valid Text Field",
    },
    "valid_number_field": {
        "type": "int",
        "validator": lambda v: isinstance(v, int) and v > 0,
        "default": 1,
        "label": "Valid Number Field",
    },
    "field_with_bad_validator": { # For testing validator failure
        "type": "str",
        "validator": lambda v: False,
        "default": "",
        "label": "Bad Validator Field",
    }
}


@pytest.fixture
def basic_project_data(test_user: UserModel):
    return {
        "name": f"Test Project {datetime.now().isoformat()}", # Unique name
        "description": "A test project description",
        "author_id": test_user.id,
        "project_status": "active",
        "deadline": date.today() + timedelta(days=30),
        "priority": 1,
        "tags": ["test", "pytest"],
        "custom_fields": {}
    }

def test_create_project_success(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()

    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project = create_project(db, project_data)

    assert project is not None
    assert project.name == project_data["name"]
    assert project.description == project_data["description"]
    assert project.author_id == test_user.id
    assert project.is_deleted is False

    db_project = db.query(ProjectModel).filter(ProjectModel.id == project.id).first()
    assert db_project is not None
    assert db_project.name == project_data["name"]

def test_create_project_minimal_fields(db: Session, test_user: UserModel):
    project_name = f"Minimal Project {datetime.now().isoformat()}"
    project_data = {
        "name": project_name,
        "author_id": test_user.id,
        "project_status": "active"
        # Description, status, etc., should get defaults or be nullable
    }
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project = create_project(db, project_data)

    assert project is not None
    assert project.name == project_name
    assert project.author_id == test_user.id
    assert project.description == "" # Default from model or CRUD
    assert project.project_status == "active" # Default from CRUD

def test_create_project_missing_name(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    del project_data["name"]
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        with pytest.raises(ProjectValidationError, match="Project name is required."):
            create_project(db, project_data)

def test_create_project_empty_name(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    project_data["name"] = "   " # Whitespace only
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        with pytest.raises(ProjectValidationError, match="Project name is required."):
            create_project(db, project_data)

def test_create_project_duplicate_name(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        create_project(db, project_data) # Create first project
        with pytest.raises(DuplicateProjectName, match=f"Project with name '{project_data['name']}' already exists."):
            create_project(db, project_data) # Attempt to create again

def test_create_project_past_deadline(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    project_data["name"] = f"Past Deadline Project {datetime.now().isoformat()}" # Ensure unique name
    project_data["deadline"] = date.today() - timedelta(days=1)
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        with pytest.raises(ProjectValidationError, match="Deadline cannot be in the past."):
            create_project(db, project_data)

# --- Custom Fields Tests for create_project ---
def test_create_project_with_valid_custom_fields(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    project_data["name"] = f"Custom Fields Valid Proj {datetime.now().isoformat()}"
    project_data["custom_fields"] = {
        "valid_text_field": "Some text",
        "valid_number_field": 10
    }
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project = create_project(db, project_data)
    assert project is not None
    assert project.custom_fields["valid_text_field"] == "Some text"
    assert project.custom_fields["valid_number_field"] == 10

def test_create_project_unknown_custom_field(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    project_data["name"] = f"Custom Field Unknown {datetime.now().isoformat()}"
    project_data["custom_fields"] = {"unknown_field": "some value"}

    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        with pytest.raises(ProjectValidationError, match="Unknown custom field: unknown_field"):
            create_project(db, project_data)

def test_create_project_invalid_value_for_custom_field(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    project_data["name"] = f"Custom Field Invalid Val {datetime.now().isoformat()}"
    project_data["custom_fields"] = {"valid_number_field": -5} # Validator expects > 0

    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        with pytest.raises(ProjectValidationError, match="Invalid value for 'valid_number_field': -5"):
            create_project(db, project_data)

def test_create_project_custom_field_failed_validator(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    project_data["name"] = f"Custom Field Bad Valid {datetime.now().isoformat()}"
    project_data["custom_fields"] = {"field_with_bad_validator": "any value"}

    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        with pytest.raises(ProjectValidationError, match="Invalid value for 'field_with_bad_validator': any value"):
            create_project(db, project_data)

# --- Tests for get_project ---
def test_get_project_success(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        created_project = create_project(db, project_data)
        fetched_project = get_project(db, created_project.id)

    assert fetched_project is not None
    assert fetched_project.id == created_project.id
    assert fetched_project.name == created_project.name

def test_get_project_not_found(db: Session):
    with pytest.raises(ProjectNotFound, match="Project with id=99999 not found"):
        get_project(db, 99999) # Assuming 99999 does not exist

def test_get_project_soft_deleted_default_not_found(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    project_data["name"] = f"Soft Del Proj {datetime.now().isoformat()}"
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        created_project = create_project(db, project_data)
        soft_delete_project(db, created_project.id) # Soft delete it

        with pytest.raises(ProjectNotFound, match=f"Project with id={created_project.id} not found \\(or is deleted\\)"):
            get_project(db, created_project.id) # Default include_deleted=False

def test_get_project_soft_deleted_included(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    project_data["name"] = f"Soft Del Incl Proj {datetime.now().isoformat()}"
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        created_project = create_project(db, project_data)
        soft_delete_project(db, created_project.id) # Soft delete it

        fetched_project = get_project(db, created_project.id, include_deleted=True)

    assert fetched_project is not None
    assert fetched_project.id == created_project.id
    assert fetched_project.is_deleted is True

# --- Tests for get_all_projects ---
@pytest.fixture
def project_set(db: Session, test_user: UserModel, test_superuser: UserModel):
    projects_data = [
        # User 1's projects
        {"name": "User1 Project Alpha (active, fav)", "author_id": test_user.id, "project_status": "active", "priority": 1, "tags": ["frontend", "urgent"], "is_favorite": True, "deadline": date.today() + timedelta(days=10)},
        {"name": "User1 Project Beta (planning, low)", "author_id": test_user.id, "project_status": "planning", "priority": 3, "tags": ["backend"], "is_favorite": False, "deadline": date.today() + timedelta(days=20)},
            # For archived projects, create with a valid or no deadline first, then mark as deleted.
            # The create_project validation for past deadline is strict.
            {"name": "User1 Project Gamma (archived)", "author_id": test_user.id, "project_status": "completed", "priority": 2, "tags": ["frontend", "feature"], "is_deleted": True, "deleted_at": datetime.now(timezone.utc), "deadline": date.today() + timedelta(days=1)}, # Valid deadline for creation
        # Superuser's projects (or another user's)
        {"name": "Admin Project Omega (active, high)", "author_id": test_superuser.id, "project_status": "active", "priority": 1, "tags": ["infra", "critical"], "is_favorite": True, "deadline": date.today() + timedelta(days=15)},
            {"name": "Admin Project Zeta (archived)", "author_id": test_superuser.id, "project_status": "archived", "priority": 3, "tags": ["docs"], "is_deleted": True, "deleted_at": datetime.now(timezone.utc), "deadline": date.today() + timedelta(days=1)}, # Valid deadline for creation
    ]
    created_projects = []
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        for data in projects_data:
            # Ensure unique names if tests run multiple times or overlap within session states
            data["name"] = f"{data['name']} {uuid.uuid4().hex[:6]}"
            # Handle is_deleted for creation if not directly settable via ProjectCreate schema
            is_del = data.pop("is_deleted", False)
            del_at = data.pop("deleted_at", None)

            proj = create_project(db, data)
            if is_del:
                proj.is_deleted = True
                proj.deleted_at = del_at
                proj.project_status = data.get("project_status", "archived") # Ensure status matches is_deleted
                db.commit()
                db.refresh(proj)
            created_projects.append(proj)
    return created_projects

def test_get_all_projects_as_normal_user(db: Session, test_user: UserModel, project_set):
    projects = get_all_projects(db, current_user=test_user)
    # Normal user should only see their own non-deleted projects
    assert len(projects) == 2
    for p in projects:
        assert p.author_id == test_user.id
        assert p.is_deleted is False
    project_names = [p.name for p in projects]
    assert any("User1 Project Alpha" in name for name in project_names)
    assert any("User1 Project Beta" in name for name in project_names)

def test_get_all_projects_as_superuser_default(db: Session, test_superuser: UserModel, project_set):
    projects = get_all_projects(db, current_user=test_superuser)
    # Superuser should see all non-deleted projects by default
    assert len(projects) == 3 # User1 Alpha, User1 Beta, Admin Omega
    for p in projects:
        assert p.is_deleted is False

def test_get_all_projects_as_superuser_show_archived(db: Session, test_superuser: UserModel, project_set):
    projects = get_all_projects(db, current_user=test_superuser, filters={"show_archived": True})
    # Superuser should see ALL projects (active and archived)
    assert len(projects) == 5

def test_get_all_projects_filter_status(db: Session, test_user: UserModel, project_set):
    projects = get_all_projects(db, current_user=test_user, filters={"project_status": "planning"})
    assert len(projects) == 1
    assert "User1 Project Beta" in projects[0].name

def test_get_all_projects_filter_tag(db: Session, test_user: UserModel, test_superuser: UserModel, project_set): # Added test_superuser
    projects = get_all_projects(db, current_user=test_user, filters={"tag": "frontend"})
    # User1 Project Alpha (active, fav) - tags: ["frontend", "urgent"]
    # User1 Project Gamma (archived) - tags: ["frontend", "feature"] -> but get_all_projects default no archived
    assert len(projects) == 1
    assert "User1 Project Alpha" in projects[0].name

    # Test with superuser to include archived one if show_archived is also used
    # Assuming test_superuser fixture is available and is the author of some projects with this tag
    projects_su_archived = get_all_projects(db, current_user=test_superuser, filters={"tag": "frontend", "show_archived": True})
    # Should be User1 Alpha, User1 Gamma (if test_user made them) and any by test_superuser with "frontend" tag
    # This depends on author_id of project_set[3] being a superuser or test_superuser
    # For simplicity, let's assume test_user for this tag test with archived
    projects_user_archived = get_all_projects(db, current_user=test_user, filters={"tag": "frontend", "show_archived": True})
    assert len(projects_user_archived) == 2


def test_get_all_projects_filter_is_favorite(db: Session, test_user: UserModel, project_set):
    projects = get_all_projects(db, current_user=test_user, filters={"is_favorite": True})
    assert len(projects) == 1
    assert "User1 Project Alpha" in projects[0].name

def test_get_all_projects_sort_priority(db: Session, test_user: UserModel, project_set):
    projects = get_all_projects(db, current_user=test_user, sort_by="priority")
    # User1 Project Alpha (priority 1), User1 Project Beta (priority 3)
    # Expects ascending for priority
    assert len(projects) == 2
    assert "User1 Project Alpha" in projects[0].name
    assert "User1 Project Beta" in projects[1].name

def test_get_all_projects_sort_deadline_desc(db: Session, test_user: UserModel, project_set):
    projects = get_all_projects(db, current_user=test_user, sort_by="deadline")
    # User1 Project Alpha (deadline +10), User1 Project Beta (deadline +20)
    # Expects descending by default for other fields
    assert len(projects) == 2
    assert "User1 Project Beta" in projects[0].name
    assert "User1 Project Alpha" in projects[1].name

# TODO: Add more filter tests for get_all_projects (search, deadline ranges, custom_fields, etc.)

# --- Tests for update_project ---
def test_update_project_success(db: Session, test_user: UserModel, basic_project_data: dict):
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project_to_update = create_project(db, basic_project_data.copy())

    original_updated_at = project_to_update.updated_at

    import time; time.sleep(0.001) # Ensure timestamp difference

    update_data = {
        "name": "Updated Project Name",
        "description": "Updated description.",
        "project_status": "completed",
        "deadline": date.today() + timedelta(days=60),
        "priority": 2,
        "tags": ["updated", "done"],
        "custom_fields": {"valid_text_field": "new text", "valid_number_field": 20},
        "is_favorite": True
    }
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        updated_project = update_project(db, project_to_update.id, update_data)

    assert updated_project is not None
    assert updated_project.name == "Updated Project Name"
    assert updated_project.description == "Updated description."
    assert updated_project.project_status == "completed"
    assert updated_project.deadline == date.today() + timedelta(days=60)
    assert updated_project.priority == 2
    assert "updated" in updated_project.tags and "done" in updated_project.tags
    assert updated_project.custom_fields["valid_text_field"] == "new text"
    assert updated_project.custom_fields["valid_number_field"] == 20
    assert updated_project.is_favorite is True
    assert updated_project.updated_at > original_updated_at

def test_update_project_partial(db: Session, test_user: UserModel, basic_project_data: dict):
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project_to_update = create_project(db, basic_project_data.copy())

    original_name = project_to_update.name
    update_data = {"description": "Only description updated."}
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        updated_project = update_project(db, project_to_update.id, update_data)

    assert updated_project.description == "Only description updated."
    assert updated_project.name == original_name # Ensure other fields are unchanged

def test_update_project_not_found(db: Session):
    with pytest.raises(ProjectNotFound):
        update_project(db, 99999, {"name": "Ghost Project"})

def test_update_project_empty_name(db: Session, test_user: UserModel, basic_project_data: dict):
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project_to_update = create_project(db, basic_project_data.copy())

    update_data = {"name": ""}
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        with pytest.raises(ProjectValidationError, match="Project name is required."):
            update_project(db, project_to_update.id, update_data)

def test_update_project_past_deadline(db: Session, test_user: UserModel, basic_project_data: dict):
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project_to_update = create_project(db, basic_project_data.copy())

    update_data = {"deadline": date.today() - timedelta(days=1)}
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        with pytest.raises(ProjectValidationError, match="Deadline cannot be in the past."):
            update_project(db, project_to_update.id, update_data)

def test_update_project_invalid_custom_field_value(db: Session, test_user: UserModel, basic_project_data: dict):
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project_to_update = create_project(db, basic_project_data.copy())

    update_data = {"custom_fields": {"valid_number_field": -10}} # Invalid, must be > 0
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        with pytest.raises(ProjectValidationError, match="Invalid value for 'valid_number_field': -10"):
            update_project(db, project_to_update.id, update_data)

def test_update_project_add_new_custom_field(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    project_data["custom_fields"] = {"valid_text_field": "initial"} # Start with one custom field
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project_to_update = create_project(db, project_data)

    update_data = {"custom_fields": {"valid_number_field": 50}} # Add a new one
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        updated_project = update_project(db, project_to_update.id, update_data)

    assert updated_project.custom_fields["valid_text_field"] == "initial" # Original should persist
    assert updated_project.custom_fields["valid_number_field"] == 50 # New one added

def test_update_project_modify_existing_custom_field(db: Session, test_user: UserModel, basic_project_data: dict):
    project_data = basic_project_data.copy()
    project_data["custom_fields"] = {"valid_text_field": "initial text"}
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project_to_update = create_project(db, project_data)

    update_data = {"custom_fields": {"valid_text_field": "updated text"}}
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        updated_project = update_project(db, project_to_update.id, update_data)

    assert updated_project.custom_fields["valid_text_field"] == "updated text"

# --- Tests for soft_delete_project ---
def test_soft_delete_project_success(db: Session, test_user: UserModel, basic_project_data: dict):
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project_to_delete = create_project(db, basic_project_data.copy())

    deleted_project_obj = soft_delete_project(db, project_to_delete.id) # Changed to receive the project object
    assert deleted_project_obj is not None
    assert deleted_project_obj.is_deleted is True
    assert deleted_project_obj.deleted_at is not None
    assert deleted_project_obj.project_status == "archived"

    # Verify it's not found by default get_project
    with pytest.raises(ProjectNotFound):
        get_project(db, project_to_delete.id)

    # Verify it IS found if include_deleted is True
    found_deleted_project = get_project(db, project_to_delete.id, include_deleted=True)
    assert found_deleted_project is not None
    assert found_deleted_project.is_deleted is True

    # Verify it's not in default get_all_projects for that user
    projects_after_delete = get_all_projects(db, current_user=test_user)
    assert project_to_delete.id not in [p.id for p in projects_after_delete]

def test_soft_delete_project_not_found(db: Session):
    with pytest.raises(ProjectNotFound):
        soft_delete_project(db, 88888) # Non-existent ID

def test_soft_delete_project_already_deleted(db: Session, test_user: UserModel, basic_project_data: dict):
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project_to_delete = create_project(db, basic_project_data.copy())
        soft_delete_project(db, project_to_delete.id) # First delete

    with pytest.raises(ProjectValidationError, match="Project already archived."):
        soft_delete_project(db, project_to_delete.id) # Second delete attempt

# --- Tests for restore_project ---
def test_restore_project_success(db: Session, test_user: UserModel, basic_project_data: dict):
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project_to_restore = create_project(db, basic_project_data.copy())
        soft_delete_project(db, project_to_restore.id) # Soft delete it first

    restored_project = restore_project(db, project_to_restore.id)
    assert restored_project is not None
    assert restored_project.is_deleted is False
    assert restored_project.deleted_at is None
    assert restored_project.project_status == "active"

    # Verify it's found by default get_project now
    found_restored_project = get_project(db, project_to_restore.id)
    assert found_restored_project is not None
    assert found_restored_project.is_deleted is False

def test_restore_project_not_found(db: Session):
    with pytest.raises(ProjectNotFound): # ProjectNotFound because get_project(include_deleted=True) is called first
        restore_project(db, 77777)

def test_restore_project_not_deleted(db: Session, test_user: UserModel, basic_project_data: dict):
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', MOCKED_CUSTOM_FIELDS_SCHEMA):
        project_not_deleted = create_project(db, basic_project_data.copy())

    with pytest.raises(ProjectValidationError, match=f"Project with id={project_not_deleted.id} is not archived/deleted."):
        restore_project(db, project_not_deleted.id)

# Note: get_ai_context and summarize_project are more about data transformation than core CRUD.
# Basic tests could ensure they run without error and return expected string/dict structures.
# For now, focusing on core CRUD with state changes.

# Placeholder for more tests if complex logic in get_ai_context/summarize_project needs validation.
# def test_get_ai_context_structure(db: Session, project_set):
#     project = project_set[0] # Assuming project_set[0] is a valid project
#     context = get_ai_context(db, project.id)
#     assert isinstance(context, dict)
#     assert "name" in context
#     assert "is_overdue" in context # Example check

# def test_summarize_project_output(db: Session, project_set):
#     project = project_set[0]
#     summary = summarize_project(db, project.id)
#     assert isinstance(summary, str)
#     assert project.name in summary # Example check

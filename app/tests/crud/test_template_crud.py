import pytest
from sqlalchemy.orm import Session
from app.crud.template import (
    create_template,
    get_template,
    get_all_templates,
    update_template,
    soft_delete_template,
    restore_template,
    hard_delete_template,
    clone_template_to_project # Added for testing
)
# Assuming ProjectValidationError and DuplicateProjectName are the exceptions used as per crud file
from app.core.exceptions import ProjectValidationError, DuplicateProjectName, SpecificTemplateNotFoundError
from app.models.user import User as UserModel
from app.models.template import Template as TemplateModel
from app.models.project import Project as ProjectModel # For clone_template_to_project
from app.models.task import Task as TaskModel # For clone_template_to_project
from app.schemas.project import ProjectCreate # For clone_template_to_project
from datetime import datetime, timezone, date
import uuid

@pytest.fixture
def basic_template_data(test_user: UserModel):
    return {
        "name": f"Test Template {uuid.uuid4().hex[:6]}",
        "description": "A test template description.",
        "structure": {"type": "project", "details": {"tasks": [{"title": "Sample Task"}]}},
        # author_id will be passed directly to create_template
    }

# --- Tests for create_template ---
def test_create_template_success(db: Session, test_user: UserModel, basic_template_data: dict):
    template_data = basic_template_data.copy()
    template = create_template(db, template_data, author_id=test_user.id)

    assert template is not None
    assert template.name == template_data["name"]
    assert template.description == template_data["description"]
    assert template.author_id == test_user.id
    assert template.structure == template_data["structure"]
    assert template.version == "1.0.0" # Default
    assert template.is_active is True   # Default
    assert template.is_private is False # Default
    assert template.tags == []          # Default
    assert template.is_deleted is False

    db_template = db.query(TemplateModel).filter(TemplateModel.id == template.id).first()
    assert db_template is not None
    assert db_template.name == template_data["name"]

def test_create_template_all_fields(db: Session, test_user: UserModel, basic_template_data: dict):
    template_data = basic_template_data.copy()
    template_data["name"] = f"Full Template {uuid.uuid4().hex[:6]}"
    template_data["version"] = "1.1.0"
    template_data["is_active"] = False
    template_data["is_private"] = True
    template_data["tags"] = ["complex", "setup"]
    template_data["ai_notes"] = "AI notes for full template."
    template_data["subscription_level"] = "premium"

    template = create_template(db, template_data, author_id=test_user.id)

    assert template.version == "1.1.0"
    assert template.is_active is False
    assert template.is_private is True
    assert "complex" in template.tags
    assert template.ai_notes == "AI notes for full template."
    assert template.subscription_level == "premium"

def test_create_template_missing_name(db: Session, test_user: UserModel):
    data = {"structure": {"details": "..."}}
    with pytest.raises(ProjectValidationError, match="Template name is required."):
        create_template(db, data, author_id=test_user.id)

def test_create_template_empty_name(db: Session, test_user: UserModel):
    data = {"name": "   ", "structure": {"details": "..."}}
    with pytest.raises(ProjectValidationError, match="Template name is required."):
        create_template(db, data, author_id=test_user.id)

def test_create_template_missing_structure(db: Session, test_user: UserModel):
    data = {"name": "No Structure Template"}
    with pytest.raises(ProjectValidationError, match="Template structure is required."):
        create_template(db, data, author_id=test_user.id)

def test_create_template_duplicate_name(db: Session, test_user: UserModel, basic_template_data: dict):
    template_data = basic_template_data.copy()
    create_template(db, template_data, author_id=test_user.id) # Create first

    # Attempt to create again with the same name
    with pytest.raises(DuplicateProjectName, match=f"Template with name '{template_data['name']}' already exists."):
        create_template(db, template_data, author_id=test_user.id)

# --- Tests for get_template ---
def test_get_template_success(db: Session, test_user: UserModel, basic_template_data: dict):
    created_template = create_template(db, basic_template_data, author_id=test_user.id)
    fetched_template = get_template(db, created_template.id)

    assert fetched_template is not None
    assert fetched_template.id == created_template.id
    assert fetched_template.name == created_template.name

def test_get_template_not_found(db: Session):
    with pytest.raises(SpecificTemplateNotFoundError, match="Template with id=99999 not found"):
        get_template(db, 99999) # Assuming 99999 does not exist

def test_get_template_soft_deleted_default_not_found(db: Session, test_user: UserModel, basic_template_data: dict):
    created_template = create_template(db, basic_template_data, author_id=test_user.id)
    # Manually soft-delete for testing get_template directly for now
    created_template.is_deleted = True
    created_template.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(created_template)

    with pytest.raises(SpecificTemplateNotFoundError, match=f"Template with id={created_template.id} not found \\(or is deleted\\)"):
        get_template(db, created_template.id) # Default include_deleted=False

def test_get_template_soft_deleted_included(db: Session, test_user: UserModel, basic_template_data: dict):
    created_template = create_template(db, basic_template_data, author_id=test_user.id)
    # Manually soft-delete
    created_template.is_deleted = True
    created_template.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(created_template)

    fetched_template = get_template(db, created_template.id, include_deleted=True)

    assert fetched_template is not None
    assert fetched_template.id == created_template.id
    assert fetched_template.is_deleted is True

# --- Tests for get_all_templates ---
@pytest.fixture
def template_set(db: Session, test_user: UserModel, test_superuser: UserModel):
    templates_data = [
        # test_user's templates
        {"name": f"UserTemplate PrivateActive {uuid.uuid4().hex[:4]}", "author_id": test_user.id, "structure": {"v":1}, "is_private": True, "is_active": True, "tags": ["user", "report"], "subscription_level": "free"},
        {"name": f"UserTemplate PublicActive {uuid.uuid4().hex[:4]}", "author_id": test_user.id, "structure": {"v":1}, "is_private": False, "is_active": True, "tags": ["user", "public"], "subscription_level": "pro"},
        {"name": f"UserTemplate PrivateInactive {uuid.uuid4().hex[:4]}", "author_id": test_user.id, "structure": {"v":1}, "is_private": True, "is_active": False, "tags": ["user", "old"]},
        {"name": f"UserTemplate PublicDeleted {uuid.uuid4().hex[:4]}", "author_id": test_user.id, "structure": {"v":1}, "is_private": False, "is_active": True, "is_deleted": True},
        # test_superuser's templates
        {"name": f"AdminTemplate PrivateActive {uuid.uuid4().hex[:4]}", "author_id": test_superuser.id, "structure": {"v":1}, "is_private": True, "is_active": True, "tags": ["admin", "config"], "subscription_level": "pro"},
        {"name": f"AdminTemplate PublicActive {uuid.uuid4().hex[:4]}", "author_id": test_superuser.id, "structure": {"v":1}, "is_private": False, "is_active": True, "tags": ["admin", "global"]},
        {"name": f"AdminTemplate PublicInactiveDeleted {uuid.uuid4().hex[:4]}", "author_id": test_superuser.id, "structure": {"v":1}, "is_private": False, "is_active": False, "is_deleted": True},
    ]
    created_templates = []
    for data in templates_data:
        is_del = data.pop("is_deleted", False)
        tmpl = create_template(db, data, author_id=data["author_id"]) # Pass author_id explicitly
        if is_del:
            tmpl.is_deleted = True
            tmpl.deleted_at = datetime.now(timezone.utc)
            db.commit() # Commit soft delete
            db.refresh(tmpl)
        created_templates.append(tmpl)
    return created_templates

def test_get_all_templates_normal_user_sees_own_private_and_public_active(db: Session, test_user: UserModel, template_set):
    # Default: active, non-deleted. Normal user sees own private + all public.
    templates = get_all_templates(db, current_user=test_user)
    names = {t.name for t in templates}
    # Expected: UserTemplate PrivateActive, UserTemplate PublicActive, AdminTemplate PublicActive
    assert len(names) == 3
    assert any("UserTemplate PrivateActive" in name for name in names)
    assert any("UserTemplate PublicActive" in name for name in names)
    assert any("AdminTemplate PublicActive" in name for name in names)

def test_get_all_templates_superuser_sees_all_active_non_deleted(db: Session, test_superuser: UserModel, template_set):
    # Default: active, non-deleted. Superuser sees all.
    templates = get_all_templates(db, current_user=test_superuser)
    names = {t.name for t in templates}
    # Expected: UserTemplate PrivateActive, UserTemplate PublicActive, AdminTemplate PrivateActive, AdminTemplate PublicActive
    assert len(names) == 4
    assert any("UserTemplate PrivateActive" in name for name in names)
    assert any("UserTemplate PublicActive" in name for name in names)
    assert any("AdminTemplate PrivateActive" in name for name in names)
    assert any("AdminTemplate PublicActive" in name for name in names)

def test_get_all_templates_superuser_include_deleted(db: Session, test_superuser: UserModel, template_set):
    templates = get_all_templates(db, current_user=test_superuser, filters={"show_archived": True}) # Changed key
    # Superuser, show_archived=True, is_active not specified
    # The CRUD logic: if show_archived, is_active filter is independent.
    # If is_active is NOT in filters, it won't filter by is_active.
    # So, this should return all templates (5 active/inactive non-deleted + 2 deleted = 7)
    assert len(templates) == 7

def test_get_all_templates_superuser_include_deleted_and_inactive_only(db: Session, test_superuser: UserModel, template_set):
    templates = get_all_templates(db, current_user=test_superuser, filters={"show_archived": True, "is_active": False}) # Changed key
    names = {t.name for t in templates}
    # UserTemplate PrivateInactive, AdminTemplate PublicInactiveDeleted
    assert len(names) == 2
    assert any("UserTemplate PrivateInactive" in name for name in names)
    assert any("AdminTemplate PublicInactiveDeleted" in name for name in names)

def test_get_all_templates_normal_user_include_deleted_is_ignored(db: Session, test_user: UserModel, template_set):
    # show_archived should be ignored for non-superusers if it means showing more than allowed
    templates = get_all_templates(db, current_user=test_user, filters={"show_archived": True}) # Changed key
    names = {t.name for t in templates}
    # Expected: UserTemplate PrivateActive, UserTemplate PublicActive, AdminTemplate PublicActive (same as default for normal user)
    assert len(names) == 3

def test_get_all_templates_filter_tag(db: Session, test_user: UserModel, template_set):
    templates = get_all_templates(db, current_user=test_user, filters={"tag": "user"})
    # UserTemplate PrivateActive, UserTemplate PublicActive (both have "user" tag and are active/visible)
    assert len(templates) == 2

def test_get_all_templates_filter_subscription_level_superuser(db: Session, test_superuser: UserModel, template_set):
    templates = get_all_templates(db, current_user=test_superuser, filters={"subscription_level": "pro"})
    # UserTemplate PublicActive, AdminTemplate PrivateActive (both "pro" and active/non-deleted)
    assert len(templates) == 2

# --- Tests for update_template ---
@pytest.fixture
def template_for_update(db: Session, test_user: UserModel, basic_template_data: dict) -> TemplateModel:
    return create_template(db, basic_template_data, author_id=test_user.id)

def test_update_template_success(db: Session, template_for_update: TemplateModel):
    original_updated_at = template_for_update.updated_at
    import time; time.sleep(0.001) # Ensure timestamp difference

    update_data = {
        "name": "Updated Template Name",
        "description": "Updated template description.",
        "version": "1.2.0",
        "is_active": False,
        "is_private": True,
        "tags": ["updated", "core"],
        "structure": {"new_key": "new_value"},
        "ai_notes": "Updated AI notes.",
        "subscription_level": "enterprise"
    }
    updated_template = update_template(db, template_for_update.id, update_data)

    assert updated_template.name == "Updated Template Name"
    assert updated_template.description == "Updated template description."
    assert updated_template.version == "1.2.0"
    assert updated_template.is_active is False
    assert updated_template.is_private is True
    assert "updated" in updated_template.tags and "core" in updated_template.tags
    assert updated_template.structure == {"new_key": "new_value"}
    assert updated_template.ai_notes == "Updated AI notes."
    assert updated_template.subscription_level == "enterprise"
    assert updated_template.updated_at > original_updated_at
    assert updated_template.author_id == template_for_update.author_id # Author should not change

def test_update_template_partial(db: Session, template_for_update: TemplateModel):
    original_name = template_for_update.name
    update_data = {"description": "Only description updated."}
    updated_template = update_template(db, template_for_update.id, update_data)

    assert updated_template.description == "Only description updated."
    assert updated_template.name == original_name # Other fields unchanged

def test_update_template_not_found(db: Session):
    with pytest.raises(SpecificTemplateNotFoundError):
        update_template(db, 99999, {"name": "Ghost Template"})

def test_update_template_empty_name(db: Session, template_for_update: TemplateModel):
    update_data = {"name": ""}
    # Note: create_template uses ProjectValidationError, update_template should ideally use TemplateValidationError
    with pytest.raises(ProjectValidationError, match="Template name cannot be empty."):
        update_template(db, template_for_update.id, update_data)

def test_update_template_empty_structure(db: Session, template_for_update: TemplateModel):
    update_data = {"structure": {}} # Or None, depending on how empty is defined
    with pytest.raises(ProjectValidationError, match="Template structure cannot be empty."):
        update_template(db, template_for_update.id, update_data)

def test_update_template_tags_set_to_none_becomes_empty_list(db: Session, template_for_update: TemplateModel):
    # Ensure template initially has tags
    template_for_update.tags = ["initial_tag"]
    db.commit()
    db.refresh(template_for_update)
    assert "initial_tag" in template_for_update.tags

    update_data = {"tags": None} # Client sends null for tags
    updated_template = update_template(db, template_for_update.id, update_data)
    assert updated_template.tags == []

# --- Tests for soft_delete_template, restore_template, hard_delete_template ---
def test_soft_delete_template_success(db: Session, template_for_update: TemplateModel): # Reuse fixture
    template_id = template_for_update.id

    deleted_template = soft_delete_template(db, template_id)
    assert deleted_template is not None
    assert deleted_template.is_deleted is True
    assert deleted_template.is_active is False # soft_delete also deactivates
    assert deleted_template.deleted_at is not None

    # Verify get_template default behavior
    with pytest.raises(SpecificTemplateNotFoundError):
        get_template(db, template_id)

    fetched_deleted = get_template(db, template_id, include_deleted=True)
    assert fetched_deleted is not None

def test_soft_delete_template_already_deleted(db: Session, template_for_update: TemplateModel):
    template_id = template_for_update.id
    soft_delete_template(db, template_id) # First delete

    # As per CRUD logic, soft-deleting an already soft-deleted template returns the template without error.
    # It logs "Template ... is already soft-deleted."
    already_deleted_template = soft_delete_template(db, template_id)
    assert already_deleted_template is not None
    assert already_deleted_template.is_deleted is True

def test_soft_delete_template_not_found(db: Session):
    with pytest.raises(SpecificTemplateNotFoundError): # get_template within soft_delete_template raises this
        soft_delete_template(db, 99999)

def test_restore_template_success(db: Session, template_for_update: TemplateModel):
    template_id = template_for_update.id
    soft_delete_template(db, template_id) # Delete first

    # Confirm it's deleted
    deleted_template_check = get_template(db, template_id, include_deleted=True)
    assert deleted_template_check.is_deleted is True

    restored_template = restore_template(db, template_id)
    assert restored_template is not None
    assert restored_template.is_deleted is False
    assert restored_template.deleted_at is None
    # Note: restore_template in CRUD doesn't automatically set is_active=True. This is fine.
    # It was made inactive by soft_delete. If reactivation is desired, update_template should be used.
    assert restored_template.is_active is False

def test_restore_template_not_deleted(db: Session, template_for_update: TemplateModel):
    template_id = template_for_update.id
    # Ensure it's active and not deleted
    assert template_for_update.is_deleted is False

    with pytest.raises(ProjectValidationError, match=f"Template '{template_for_update.name}' .* is not deleted."):
        restore_template(db, template_id)

def test_restore_template_not_found(db: Session):
    with pytest.raises(SpecificTemplateNotFoundError):
        restore_template(db, 88888)

def test_hard_delete_template_success(db: Session, template_for_update: TemplateModel):
    template_id = template_for_update.id

    result = hard_delete_template(db, template_id)
    assert result is True

    with pytest.raises(SpecificTemplateNotFoundError):
        get_template(db, template_id, include_deleted=True) # Should not find even if including deleted

def test_hard_delete_soft_deleted_template(db: Session, template_for_update: TemplateModel):
    template_id = template_for_update.id
    soft_delete_template(db, template_id) # Soft delete first

    result = hard_delete_template(db, template_id)
    assert result is True

    with pytest.raises(SpecificTemplateNotFoundError):
        get_template(db, template_id, include_deleted=True)

def test_hard_delete_template_not_found(db: Session):
    with pytest.raises(SpecificTemplateNotFoundError):
        hard_delete_template(db, 77777)

# --- Tests for clone_template_to_project ---
from app.schemas.project import ProjectCreate
from app.models.task import Task as TaskModel # For querying tasks
from app.crud.template import clone_template_to_project # Explicit import for clarity

@pytest.fixture
def template_for_cloning(db: Session, test_user: UserModel) -> TemplateModel:
    template_data = {
        "name": f"Clonable Template {uuid.uuid4().hex[:4]}",
        "description": "Base description from template.",
        # author_id will be passed directly to create_template
        "structure": {
            "description": "Template structure description for project.",
            "tasks": [
                {"title": "Cloned Task 1", "description": "Desc for task 1", "priority": 1, "task_status": "todo", "tags": ["tag1"], "assignees": [{"user_id": test_user.id, "name": "Test User"}]}, # Assumes Assignee schema has name
                {"title": "Cloned Task 2", "description": "Desc for task 2", "deadline": "2025-12-31"}, # Valid deadline string
                {"title": "Task with Invalid Deadline", "deadline": "not-a-date-format"}, # Invalid deadline
                {"description": "Task missing title in template"}, # Invalid task def
            ]
        }
    }
    return create_template(db, template_data, author_id=test_user.id)

def test_clone_template_to_project_success(db: Session, test_user: UserModel, template_for_cloning: TemplateModel):
    new_project_name = f"Cloned Project from {template_for_cloning.name[:10]} {uuid.uuid4().hex[:4]}"
    # For ProjectCreate, only 'name' is strictly required by its schema if author_id is handled by API
    # Here, crud_create_project (used by clone_template_to_project) expects author_id in its 'data' dict.
    # The clone_template_to_project function sets new_project.author_id = new_project_author_id.
    project_create_schema = ProjectCreate(name=new_project_name, author_id=test_user.id)


    cloned_project = clone_template_to_project(
        db,
        source_template=template_for_cloning,
        project_create_data=project_create_schema,
        new_project_author_id=test_user.id
    )

    assert cloned_project is not None
    assert cloned_project.name == new_project_name
    assert cloned_project.author_id == test_user.id
    # Description should come from template.structure.description if not in project_create_schema
    assert cloned_project.description == template_for_cloning.structure.get("description")

    # Verify tasks
    tasks = db.query(TaskModel).filter(TaskModel.project_id == cloned_project.id).order_by(TaskModel.title).all()
    # Expected 3 valid tasks: 2 fully valid, 1 with invalid deadline format (deadline becomes None)
    # 1 invalid task (missing title) is skipped.
    assert len(tasks) == 3

    task_titles = {t.title for t in tasks}
    assert "Cloned Task 1" in task_titles
    assert "Cloned Task 2" in task_titles
    assert "Task with Invalid Deadline" in task_titles

    task1 = next(t for t in tasks if t.title == "Cloned Task 1")
    assert task1.description == "Desc for task 1"
    assert task1.priority == 1
    assert task1.task_status == "todo"
    assert "tag1" in task1.tags
    assert len(task1.assignees) == 1
    # The assignees structure in template is [{"user_id": id, "name": name}], matches Task.assignees JSON
    assert task1.assignees[0]["user_id"] == test_user.id

    task2 = next(t for t in tasks if t.title == "Cloned Task 2")
    assert task2.deadline == date(2025, 12, 31)

    task3 = next(t for t in tasks if t.title == "Task with Invalid Deadline")
    assert task3.deadline is None # Invalid deadline format should result in None

def test_clone_template_override_description(db: Session, test_user: UserModel, template_for_cloning: TemplateModel):
    project_create_schema = ProjectCreate(
        name=f"Cloned Project Override {uuid.uuid4().hex[:4]}",
        description="Description from ProjectCreate payload.",
        author_id=test_user.id # Required by ProjectCreate
    )
    cloned_project = clone_template_to_project(
        db,
        source_template=template_for_cloning,
        project_create_data=project_create_schema,
        new_project_author_id=test_user.id
    )
    assert cloned_project.description == "Description from ProjectCreate payload."

def test_clone_template_with_no_tasks_in_structure(db: Session, test_user: UserModel):
    template_data = {
        "name": f"No Tasks Template {uuid.uuid4().hex[:4]}",
        "author_id": test_user.id,
        "structure": {"description": "A project with no tasks defined in template."} # No 'tasks' key
    }
    no_task_template = create_template(db, template_data, author_id=test_user.id)

    project_create_schema = ProjectCreate(
        name=f"Project from NoTask Template {uuid.uuid4().hex[:4]}",
        author_id=test_user.id # Required by ProjectCreate
    )
    new_project = clone_template_to_project(
        db,
        source_template=no_task_template,
        project_create_data=project_create_schema,
        new_project_author_id=test_user.id
    )
    assert new_project is not None
    tasks = db.query(TaskModel).filter(TaskModel.project_id == new_project.id).all()
    assert len(tasks) == 0

# Consider if TemplateValidationError should be used instead of ProjectValidationError in CRUD

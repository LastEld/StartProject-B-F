import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock # Use AsyncMock for async functions
from datetime import datetime, timezone # For JarvisResponse timestamp

from app.schemas.jarvis import JarvisRequest, JarvisResponse
from app.crud.jarvis import ChatControllerError
from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.crud.project import create_project as crud_create_project
from app.core.config import settings # For API prefix if needed, though client handles it

# A fixture to create a project for the test user
@pytest.fixture
def test_user_project(db: Session, test_user: UserModel) -> ProjectModel:
    project_data = {"name": "Test Project for Jarvis", "description": "A test project", "author_id": test_user.id}
    # Assuming create_project in crud takes a Pydantic schema or dict for creation
    # Adjust if crud_create_project expects a Pydantic model e.g. ProjectCreate
    return crud_create_project(db=db, project_in=project_data, owner_id=test_user.id)

def test_ask_jarvis_success(
    client: TestClient,
    normal_user_token_headers: dict,
    test_user_project: ProjectModel,
    # db: Session # db fixture is not directly needed if ask_ollama is fully mocked
):
    request_payload_dict = {
        "prompt": "Hello Jarvis",
        "project_id": test_user_project.id,
        "model": "test_model",
        "session_id": "test_session_123",
        "stream": False,
        "options": {"temperature": 0.5}
    }
    # JarvisRequest can be used for validation, but client sends dict
    # request_payload_obj = JarvisRequest(**request_payload_dict)

    # Ensure created_at is timezone-aware for consistent ISO formatting
    fixed_datetime = datetime.now(timezone.utc)

    mock_response_data = {
        "response": "Hello there!",
        "model": "test_model",
        "created_at": fixed_datetime, # Use a fixed datetime object
        "done": True,
        "context": [1, 2, 3],
        "total_duration": 1000000,
        "load_duration": 100000,
        "prompt_eval_count": 10,
        "prompt_eval_duration": 200000,
        "eval_count": 20,
        "eval_duration": 700000,
    }
    mock_jarvis_response_obj = JarvisResponse(**mock_response_data)
    # Convert to JSON serializable dict, Pydantic's model_dump(mode='json') handles datetime to ISO string
    mock_response_data_json = mock_jarvis_response_obj.model_dump(mode='json')

    # Patch app.api.jarvis.ask_ollama as it's called from the api_ask_jarvis endpoint handler
    with patch("app.api.jarvis.ask_ollama", new_callable=AsyncMock) as mock_ask_ollama:
        mock_ask_ollama.return_value = mock_jarvis_response_obj

        api_url = f"{settings.API_V1_STR}/jarvis/ask"
        response = client.post(api_url, headers=normal_user_token_headers, json=request_payload_dict)

        assert response.status_code == 200
        assert response.json() == mock_response_data_json # Compare JSON dicts

        mock_ask_ollama.assert_awaited_once()
        # Check call arguments:
        args, kwargs = mock_ask_ollama.call_args
        assert isinstance(kwargs['request'], JarvisRequest)
        assert kwargs['request'].prompt == request_payload_dict["prompt"]
        assert kwargs['request'].project_id == request_payload_dict["project_id"]
        assert kwargs['current_user_username'] is not None # test_user.username would be more specific if available


def test_ask_jarvis_chat_controller_error(
    client: TestClient,
    normal_user_token_headers: dict,
    test_user_project: ProjectModel
):
    request_payload_dict = {
        "prompt": "Trigger ChatControllerError",
        "project_id": test_user_project.id,
        "model": "error_model"
    }
    # request_payload_obj = JarvisRequest(**request_payload_dict)

    # Patch app.api.jarvis.ask_ollama
    with patch("app.api.jarvis.ask_ollama", new_callable=AsyncMock) as mock_ask_ollama:
        mock_ask_ollama.side_effect = ChatControllerError("Ollama service not available for test")

        api_url = f"{settings.API_V1_STR}/jarvis/ask"
        response = client.post(api_url, headers=normal_user_token_headers, json=request_payload_dict)

        assert response.status_code == 400 # As defined in api/jarvis.py for ChatControllerError
        json_response = response.json()
        assert "detail" in json_response
        assert "Ollama service not available for test" in json_response["detail"]

        mock_ask_ollama.assert_awaited_once()


def test_ask_jarvis_unexpected_error(
    client: TestClient,
    normal_user_token_headers: dict,
    test_user_project: ProjectModel
):
    request_payload_dict = {
        "prompt": "Trigger unexpected error",
        "project_id": test_user_project.id,
        "model": "unexpected_error_model"
    }

    with patch("app.api.jarvis.ask_ollama", new_callable=AsyncMock) as mock_ask_ollama:
        mock_ask_ollama.side_effect = Exception("A very unexpected issue occurred")

        api_url = f"{settings.API_V1_STR}/jarvis/ask"
        response = client.post(api_url, headers=normal_user_token_headers, json=request_payload_dict)

        assert response.status_code == 500 # As defined in api/jarvis.py for general Exception
        json_response = response.json()
        assert "detail" in json_response
        assert "An unexpected error occurred." in json_response["detail"]

        mock_ask_ollama.assert_awaited_once()

# TODO: Add tests for other Jarvis API endpoints:
# - POST /jarvis/message
# - GET /jarvis/history/{project_id}
# - DELETE /jarvis/history/{project_id}
# - GET /jarvis/history/{project_id}/last
# Consider various scenarios: success, not found, unauthorized, invalid input.
# Consider testing the db interaction of ask_ollama if project_id is present/absent (though that's more of a CRUD test).
# For /jarvis/ask, if project_id is optional and None, ensure ask_ollama is called correctly and no db ops for saving messages.
# (Current ask_ollama in CRUD saves if project_id is not None)
# Test with superuser_token_headers as well, if behavior should differ.
# Test with missing or invalid token.
# Test with invalid request payload (e.g., missing 'prompt'). FastAPI usually handles this with 422.
# Test streaming if/when implemented.
# Test different models if behavior should change.
# Test with various options in JarvisRequest.options.
# Test when current_user.username is used by ask_ollama.
# The test_user_project fixture uses crud_create_project. Ensure its signature matches.
# The current crud_create_project might take: (db: Session, project_in: schemas.ProjectCreate, owner_id: int)
# So, project_data in the fixture needs to align with ProjectCreate schema.
# The example: project_data = {"name": "Test Project for Jarvis", "author_id": test_user.id} might be missing description.
# Corrected in fixture: project_data = {"name": "Test Project for Jarvis", "description": "A test project", "author_id": test_user.id}
# And call crud_create_project(db=db, project_in=project_data, owner_id=test_user.id)
# This assumes test_user.id is the owner_id. If ProjectCreate expects author_id, ensure it's set.
# The crud_create_project might return a Project model, which is fine.
# The `API_V1_STR` is imported from `app.core.config` to construct the full URL.
# Datetime comparison needs care. Pydantic's model_dump(mode='json') converts datetimes to ISO strings.
# So, the comparison `response.json() == mock_response_data_json` should work if both are consistently serialized.
# Using `datetime.now(timezone.utc)` for `created_at` in mock_response_data ensures it's timezone-aware.
# Added a third test case for unexpected errors (HTTP 500).
# Added more detailed assertion for mock_ask_ollama call arguments.
# Updated test_user_project fixture based on typical CRUD patterns.
# The `client.post` JSON argument should be a dict, so `request_payload.model_dump()` or a plain dict is correct.
# Using request_payload_dict directly for client.post is fine.
# The `db: Session` fixture was commented out from `test_ask_jarvis_success` as it's not directly used when `ask_ollama` is mocked.
# It would be needed if testing parts of `ask_ollama` that interact with the DB (like message saving).
# For the `test_ask_jarvis_success` call arguments check, `kwargs['request']` will be a `JarvisRequest` object because
# the API endpoint `api_ask_jarvis` receives `request_data: JarvisRequest` which is then passed to `ask_ollama`.
# So, `isinstance(kwargs['request'], JarvisRequest)` is a good check.
# `kwargs['current_user_username']` should be `test_user.username`. This requires `test_user` fixture in the test.
# Let's add `test_user: UserModel` to the success test's parameters to check `current_user_username`.
# (It's implicitly available via normal_user_token_headers, but explicit fixture makes it clear).
# However, normal_user_token_headers is what sets up the user for the request. The test_user fixture itself doesn't
# guarantee that this specific user is the one authenticated by the headers.
# The current_user object is resolved by `get_current_active_user` from the token.
# So, to check `current_user_username` accurately, we'd need to know which user `normal_user_token_headers` belongs to.
# Typically, `test_user` fixture *is* that user. So `assert kwargs['current_user_username'] == test_user.username` should be fine.
# I will add this assertion.

# Final check on mock path: `app.api.jarvis.ask_ollama` is correct as `ask_ollama` is imported into `app.api.jarvis`
# and used there. So, when `api_ask_jarvis` runs, it looks for `ask_ollama` in its own module's namespace.
# Patching it there intercepts the call.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User as UserModel
from app.crud.ai_context import get_ai_context

@pytest.fixture
def ai_ctx_payload():
    return {"object_type": "project", "object_id": 1, "context_data": {"k": "v"}}


def test_create_ai_context(client: TestClient, normal_user_token_headers: dict, db: Session, ai_ctx_payload):
    response = client.post("/ai-context/", json=ai_ctx_payload, headers=normal_user_token_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["result"]
    ctx = get_ai_context(db, data["result"])
    assert ctx is not None


def test_get_ai_context(client: TestClient, normal_user_token_headers: dict, db: Session, ai_ctx_payload):
    # create first
    response = client.post("/ai-context/", json=ai_ctx_payload, headers=normal_user_token_headers)
    ctx_id = response.json()["result"]
    get_resp = client.get(f"/ai-context/{ctx_id}", headers=normal_user_token_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == ctx_id

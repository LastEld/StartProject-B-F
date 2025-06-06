import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.models.jarvis import ChatMessage as ChatMessageModel
from app.crud.project import create_project as crud_create_project

from unittest.mock import patch

@pytest.fixture
def jarvis_project(db: Session, test_user: UserModel) -> ProjectModel:
    project_data = {"name": f"JarvisProj-{uuid.uuid4().hex[:4]}", "author_id": test_user.id}
    with patch('app.crud.project.CUSTOM_FIELDS_SCHEMA', {}):
        return crud_create_project(db, project_data)

@pytest.fixture
def jarvis_message_payload_factory(jarvis_project: ProjectModel):
    def _factory(**kwargs):
        data = {
            "project_id": jarvis_project.id,
            "role": "user",
            "content": f"Hello Jarvis {uuid.uuid4().hex[:6]}"
        }
        data.update(kwargs)
        return data
    return _factory


def test_post_message_authenticated(client: TestClient, normal_user_token_headers: dict,
                                    jarvis_message_payload_factory: callable, db: Session):
    payload = jarvis_message_payload_factory()
    response = client.post("/jarvis/message", json=payload, headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == payload["content"]
    msg_in_db = db.query(ChatMessageModel).filter(ChatMessageModel.id == data["id"]).first()
    assert msg_in_db is not None
    assert msg_in_db.project_id == payload["project_id"]


def test_get_history_authenticated(client: TestClient, normal_user_token_headers: dict,
                                   jarvis_message_payload_factory: callable):
    first_payload = jarvis_message_payload_factory()
    client.post("/jarvis/message", json=first_payload, headers=normal_user_token_headers)
    second_payload = jarvis_message_payload_factory(content="Second message")
    client.post("/jarvis/message", json=second_payload, headers=normal_user_token_headers)
    project_id = first_payload["project_id"]
    response = client.get(f"/jarvis/history/{project_id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    history = response.json()
    assert len(history) >= 2
    assert all(item["project_id"] == project_id for item in history)


def test_delete_history_authenticated(client: TestClient, normal_user_token_headers: dict,
                                      jarvis_message_payload_factory: callable, db: Session):
    payload1 = jarvis_message_payload_factory()
    payload2 = jarvis_message_payload_factory(content="Another")
    client.post("/jarvis/message", json=payload1, headers=normal_user_token_headers)
    client.post("/jarvis/message", json=payload2, headers=normal_user_token_headers)
    project_id = payload1["project_id"]
    response = client.delete(f"/jarvis/history/{project_id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    result = response.json()
    assert result["result"] >= 2
    remaining = db.query(ChatMessageModel).filter(ChatMessageModel.project_id == project_id,
                                                 ChatMessageModel.is_deleted == False).all()
    assert remaining == []

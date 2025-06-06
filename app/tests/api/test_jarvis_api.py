import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.crud.project import create_project as crud_create_project


@pytest.fixture
def jarvis_project(db: Session, test_user: UserModel) -> ProjectModel:
    data = {"name": f"JarvisProj-{uuid.uuid4().hex[:6]}", "author_id": test_user.id}
    return crud_create_project(db, data)


def test_create_and_get_message(
    client: TestClient,
    normal_user_token_headers: dict,
    jarvis_project: ProjectModel,
):
    payload = {
        "project_id": jarvis_project.id,
        "role": "user",
        "content": "Hi",
        "attachments": [],
        "is_deleted": False,
    }
    resp = client.post("/jarvis/chat/", json=payload, headers=normal_user_token_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "Hi"
    msg_id = data["id"]

    resp_get = client.get(f"/jarvis/chat/{msg_id}", headers=normal_user_token_headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == msg_id

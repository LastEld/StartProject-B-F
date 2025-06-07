import pytest
from sqlalchemy.orm import Session
from app.crud import ai_context as crud
from app.models.ai_context import AIContext

@pytest.fixture
def ai_context_data():
    return {
        "object_type": "project",
        "object_id": 1,
        "context_data": {"notes": "test"},
        "created_by": "tester"
    }

def test_create_ai_context(db: Session, ai_context_data):
    ctx = crud.create_ai_context(db, **ai_context_data)
    assert ctx.id is not None
    assert ctx.object_type == ai_context_data["object_type"]


def test_update_ai_context(db: Session, ai_context_data):
    ctx = crud.create_ai_context(db, **ai_context_data)
    updated = crud.update_ai_context(db, ctx.id, {"notes": "updated"})
    assert updated.notes == "updated"

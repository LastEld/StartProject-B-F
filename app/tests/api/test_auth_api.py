#tests/api/test_auth_api.py
import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.settings import settings as app_settings
from app.models.user import User as UserModel
from app.crud.user import get_user_by_username, get_user

def _activate_user(db: Session, username: str):
    """Активирует пользователя в тесте (utility для DRY)."""
    db_user = get_user_by_username(db, username)
    if db_user and not db_user.is_active:
        db_user.is_active = True
        db.commit()
        db.refresh(db_user)

def test_login_success(client: TestClient, test_user: UserModel, db: Session):
    _activate_user(db, test_user.username)
    login_data = {"username": test_user.username, "password": "testpassword"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"

def test_login_incorrect_password(client: TestClient, test_user: UserModel, db: Session):
    _activate_user(db, test_user.username)
    login_data = {"username": test_user.username, "password": "wrongtestpassword"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_non_existent_user(client: TestClient):
    login_data = {"username": "nonexistentuser12345", "password": "anypassword"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_inactive_user(client: TestClient, test_user: UserModel, db: Session):
    db_user = get_user_by_username(db, test_user.username)
    if db_user.is_active:
        db_user.is_active = False
        db.commit()
        db.refresh(db_user)
    assert not db_user.is_active
    login_data = {"username": test_user.username, "password": "testpassword"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_refresh_token_success(client: TestClient, test_user: UserModel, db: Session):
    _activate_user(db, test_user.username)
    login_data = {"username": test_user.username, "password": "testpassword"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    tokens = response.json()
    refresh_token = tokens["refresh_token"]
    access_token = tokens["access_token"]
    time.sleep(1)
    refresh_payload = {"refresh_token": refresh_token}
    response_refresh = client.post("/auth/refresh", json=refresh_payload)
    assert response_refresh.status_code == 200
    refreshed = response_refresh.json()
    assert "access_token" in refreshed and "refresh_token" in refreshed
    assert refreshed["access_token"] != access_token
    assert refreshed["refresh_token"] != refresh_token

def test_refresh_token_invalid_token(client: TestClient):
    refresh_payload = {"refresh_token": "this.is.an.invalid.token"}
    response = client.post("/auth/refresh", json=refresh_payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token payload"

def test_refresh_token_revoked(client: TestClient, test_user: UserModel, db: Session):
    from app.core.security import verify_refresh_token
    from app.crud.auth import revoke_refresh_token as crud_revoke_refresh_token
    login_data = {"username": test_user.username, "password": "testpassword"}
    response = client.post("/auth/login", data=login_data)
    refresh_token = response.json()["refresh_token"]
    payload = verify_refresh_token(refresh_token)
    assert payload and "jti" in payload
    jti = payload["jti"]
    assert crud_revoke_refresh_token(db, token_jti=jti) is True
    refresh_payload = {"refresh_token": refresh_token}
    response_refresh = client.post("/auth/refresh", json=refresh_payload)
    assert response_refresh.status_code == 401
    assert response_refresh.json()["detail"] == "Refresh token revoked or invalid"

def test_refresh_token_user_inactive(client: TestClient, test_user: UserModel, db: Session):
    # Всегда берем id, username - и работаем только с объектами из актуальной db-сессии!
    test_user_id = test_user.id
    test_user_username = test_user.username

    # 1. Login to get tokens
    login_data = {"username": test_user_username, "password": "testpassword"}
    response_login = client.post("/auth/login", data=login_data)
    assert response_login.status_code == 200
    original_refresh_token = response_login.json()["refresh_token"]

    # 2. Make user inactive (refetch by id!)
    db_user = get_user(db, test_user_id)
    assert db_user is not None, "User not found in DB for making inactive"
    db_user.is_active = False
    db.commit()

    # 3. Attempt to refresh token
    refresh_payload = {"refresh_token": original_refresh_token}
    response_refresh = client.post("/auth/refresh", json=refresh_payload)
    assert response_refresh.status_code == 401
    assert response_refresh.json()["detail"] == "User not found or inactive"


def test_logout_success(client: TestClient, test_user: UserModel, db: Session):
    login_data = {"username": test_user.username, "password": "testpassword"}
    response = client.post("/auth/login", data=login_data)
    refresh_token = response.json()["refresh_token"]
    response_logout = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert response_logout.status_code == 200
    assert response_logout.json()["message"] == "Logout successful (token already invalid or not found)."
    from app.core.security import verify_refresh_token
    from app.crud.auth import is_refresh_token_active as crud_is_refresh_token_active
    payload = verify_refresh_token(refresh_token)
    assert payload and "jti" in payload
    assert crud_is_refresh_token_active(db, payload["jti"]) is False

def test_logout_invalid_token(client: TestClient):
    logout_payload = {"refresh_token": "invalid.refresh.token"}
    response_logout = client.post("/auth/logout", json=logout_payload)
    assert response_logout.status_code == 401
    assert response_logout.json()["detail"] == "Invalid refresh token for logout"

def test_logout_already_revoked_token(client: TestClient, test_user: UserModel, db: Session):
    login_data = {"username": test_user.username, "password": "testpassword"}
    response_login = client.post("/auth/login", data=login_data)
    refresh_token = response_login.json()["refresh_token"]
    client.post("/auth/logout", json={"refresh_token": refresh_token})
    response_logout_again = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert response_logout_again.status_code == 200
    assert response_logout_again.json()["message"] == "Logout successful (token already invalid or not found)."

def test_logout_all_success(client: TestClient, test_user: UserModel, db: Session):
    test_user_id = test_user.id
    test_user_username = test_user.username

    # 1. Login дважды — получим разные токены
    login_data = {"username": test_user_username, "password": "testpassword"}
    response1 = client.post("/auth/login", data=login_data)
    assert response1.status_code == 200
    access_token = response1.json()["access_token"]
    time.sleep(1)
    response2 = client.post("/auth/login", data=login_data)
    assert response2.status_code == 200

    from app.crud.auth import get_active_tokens_by_user
    initial_active_tokens = get_active_tokens_by_user(db, test_user_id)
    assert len(initial_active_tokens) >= 2

    headers = {"Authorization": f"Bearer {access_token}"}
    response_logout_all = client.post("/auth/logout_all", headers=headers)
    assert response_logout_all.status_code == 200
    assert "Logged out from" in response_logout_all.json()["message"]

    # Всегда рефетч после запроса!
    final_tokens = get_active_tokens_by_user(db, test_user_id)
    assert len(final_tokens) == 0


def test_logout_all_no_active_session(client: TestClient, test_user: UserModel, db: Session):
    from app.crud.auth import revoke_all_tokens_for_user as crud_revoke_all
    crud_revoke_all(db, test_user.id)
    db.commit()
    login_data = {"username": test_user.username, "password": "testpassword"}
    response_login = client.post("/auth/login", data=login_data)
    access_token = response_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    response_logout_all = client.post("/auth/logout_all", headers=headers)
    assert response_logout_all.status_code == 200
    assert response_logout_all.json()["message"] == "Logged out from 2 sessions."

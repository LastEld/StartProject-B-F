from fastapi.testclient import TestClient
from sqlalchemy.orm import Session # Though db fixture is used, good for type hinting if needed
from app.core.settings import settings as app_settings # Import app_settings
from app.models.user import User as UserModel
from app.core import security # Added import

# Test /users/me
def test_read_users_me_success(client: TestClient, normal_user_token_headers: dict, test_user: UserModel):
    response = client.get("/users/me", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email

def test_read_users_me_unauthenticated(client: TestClient):
    response = client.get("/users/me")
    assert response.status_code == 401 # Expect 401 Unauthorized

# Test POST /users/ (register_user)
def test_register_user_success(client: TestClient, db: Session): # Added db fixture
    user_data = {"username": "newapiuser", "email": "newapiuser@example.com", "password": "apipassword"}
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200 # Assuming 200 for successful creation as per current API
    data = response.json()
    assert data["username"] == "newapiuser"
    assert data["email"] == "newapiuser@example.com"
    assert "id" in data
    # Check if user is actually in DB
    user_in_db = db.query(UserModel).filter(UserModel.username == "newapiuser").first()
    assert user_in_db is not None

def test_register_user_duplicate_username(client: TestClient, test_user: UserModel):
    user_data = {"username": test_user.username, "email": "anotheremail@example.com", "password": "password"}
    response = client.post("/users/", json=user_data)
    assert response.status_code == 400 # Based on ProjectValidationError
    assert "User with this username or email already exists" in response.json()["detail"]

def test_register_user_duplicate_email(client: TestClient, test_user: UserModel):
    user_data = {"username": "anotherusername", "email": test_user.email, "password": "password"}
    response = client.post("/users/", json=user_data)
    assert response.status_code == 400 # Based on ProjectValidationError
    assert "User with this username or email already exists" in response.json()["detail"]

def test_register_user_invalid_data(client: TestClient):
    response = client.post("/users/", json={"username": "short", "email": "not-an-email", "password": "pw"})
    assert response.status_code == 422 # Pydantic validation error

# Test GET /users/{user_id} (get_user_profile)
def test_get_user_profile_superuser(client: TestClient, superuser_token_headers: dict, test_user: UserModel):
    response = client.get(f"/users/{test_user.id}", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username

def test_get_user_profile_self(client: TestClient, normal_user_token_headers: dict, test_user: UserModel):
    response = client.get(f"/users/{test_user.id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username

def test_get_user_profile_other_by_normal_user(client: TestClient, normal_user_token_headers: dict, test_superuser: UserModel):
    response = client.get(f"/users/{test_superuser.id}", headers=normal_user_token_headers)
    assert response.status_code == 403 # Forbidden

def test_get_user_profile_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.get("/users/99999", headers=superuser_token_headers)
    assert response.status_code == 404

def test_get_user_profile_unauthenticated(client: TestClient, test_user: UserModel):
    response = client.get(f"/users/{test_user.id}")
    assert response.status_code == 401

# Test GET /users/ (list_users)
def test_list_users_superuser(client: TestClient, superuser_token_headers: dict, test_user: UserModel, test_superuser: UserModel):
    response = client.get("/users/", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    usernames = [u["username"] for u in data]
    assert test_user.username in usernames
    assert test_superuser.username in usernames

def test_list_users_superuser_filter_active(client: TestClient, superuser_token_headers: dict, test_user: UserModel, db:Session):
    # Fetch the user via the current session to ensure we're working with the session-managed instance
    user_to_modify = db.query(UserModel).get(test_user.id)
    assert user_to_modify is not None, "Test user not found in DB at start of test"

    # Ensure test_user is active
    user_to_modify.is_active = True
    db.commit()
    db.refresh(user_to_modify) # Get the committed state
    assert user_to_modify.is_active is True, "User should be active after explicit set and commit/refresh"

    response = client.get("/users/?is_active=true", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert user_to_modify.username in [u['username'] for u in data]

    # Deactivate the user
    from datetime import datetime, timezone # Ensure datetime and timezone are imported
    print(f"Before change: user_to_modify (id={user_to_modify.id}) .is_active = {user_to_modify.is_active}")

    # Try direct update statement
    db.query(UserModel).filter(UserModel.id == user_to_modify.id).update({
        "is_active": False,
        "updated_at": datetime.now(timezone.utc)
    })
    db.commit()
    print(f"After direct update and commit")

    # Re-fetch to check the state
    user_to_modify_after_deactivation = db.query(UserModel).get(user_to_modify.id)
    assert user_to_modify_after_deactivation is not None, "User disappeared after deactivation commit"
    print(f"After re-fetch: user_to_modify_after_deactivation (id={user_to_modify_after_deactivation.id}).is_active = {user_to_modify_after_deactivation.is_active}")
    assert user_to_modify_after_deactivation.is_active is False, "User should be inactive in DB after direct update, commit, and re-fetch"
    user_to_modify = user_to_modify_after_deactivation # Continue using the re-fetched instance

    response_inactive = client.get("/users/?is_active=false", headers=superuser_token_headers)
    assert response_inactive.status_code == 200
    data_inactive = response_inactive.json()
    # Log the response data if the assertion fails
    if user_to_modify.username not in [u['username'] for u in data_inactive]:
        print(f"User {user_to_modify.username} not found in inactive list: {data_inactive}")
    assert user_to_modify.username in [u['username'] for u in data_inactive]

    # Reset for other tests
    # user_to_modify now refers to user_to_modify_after_deactivation
    if user_to_modify:
        user_to_modify.is_active = True # This will now use direct object modification for reset
        db.commit() # Commit the reset


def test_list_users_normal_user(client: TestClient, normal_user_token_headers: dict):
    response = client.get("/users/", headers=normal_user_token_headers)
    assert response.status_code == 403

def test_list_users_unauthenticated(client: TestClient):
    response = client.get("/users/")
    assert response.status_code == 401

# Test PATCH /users/{user_id} (patch_user)
def test_patch_user_self(client: TestClient, normal_user_token_headers: dict, test_user: UserModel):
    update_data = {"full_name": "Updated Normal User Name"}
    response = client.patch(f"/users/{test_user.id}", json=update_data, headers=normal_user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Normal User Name"
    assert data["email"] == test_user.email # Email should not change unless specified

def test_patch_user_by_superuser(client: TestClient, superuser_token_headers: dict, test_user: UserModel):
    update_data = {"full_name": "Super-Updated Name", "is_active": False}
    response = client.patch(f"/users/{test_user.id}", json=update_data, headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Super-Updated Name"
    assert data["is_active"] is False

def test_patch_user_other_by_normal_user(client: TestClient, normal_user_token_headers: dict, test_superuser: UserModel):
    update_data = {"full_name": "Attempted Update"}
    response = client.patch(f"/users/{test_superuser.id}", json=update_data, headers=normal_user_token_headers)
    assert response.status_code == 403

def test_patch_user_not_found(client: TestClient, superuser_token_headers: dict):
    update_data = {"full_name": "Ghost Update"}
    response = client.patch("/users/99999", json=update_data, headers=superuser_token_headers)
    assert response.status_code == 404

def test_patch_user_invalid_data(client: TestClient, normal_user_token_headers: dict, test_user: UserModel):
    # Example: trying to update username which might be disallowed, or invalid email format
    # For now, let's assume email format is the main validation here from UserUpdate schema
    update_data = {"email": "not-an-email"}
    response = client.patch(f"/users/{test_user.id}", json=update_data, headers=normal_user_token_headers)
    assert response.status_code == 422 # Pydantic validation

def test_patch_user_unauthenticated(client: TestClient, test_user: UserModel):
    update_data = {"full_name": "Unauth Update"}
    response = client.patch(f"/users/{test_user.id}", json=update_data)
    assert response.status_code == 401

# Test DELETE /users/{user_id} (deactivate_user)
def test_deactivate_user_self(client: TestClient, normal_user_token_headers: dict, test_user: UserModel, db: Session):
    response = client.delete(f"/users/{test_user.id}", headers=normal_user_token_headers)
    assert response.status_code == 200
    assert response.json()["detail"] == "User deactivated"
    # db.refresh(test_user) # This can cause issues if the instance is detached or from another session
    refreshed_user = db.query(UserModel).get(test_user.id)
    assert refreshed_user.is_active is False
    # Reactivate for other tests
    refreshed_user.is_active = True
    db.commit()


def test_deactivate_user_by_superuser(client: TestClient, superuser_token_headers: dict, test_user: UserModel, db: Session):
    test_user.is_active = True # Ensure active first
    db.commit()
    response = client.delete(f"/users/{test_user.id}", headers=superuser_token_headers)
    assert response.status_code == 200
    assert response.json()["detail"] == "User deactivated"
    # db.refresh(test_user) # This can cause issues if the instance is detached or from another session
    refreshed_user = db.query(UserModel).get(test_user.id)
    assert refreshed_user.is_active is False
    # Reactivate for other tests
    refreshed_user.is_active = True
    db.commit()


def test_deactivate_user_other_by_normal_user(client: TestClient, normal_user_token_headers: dict, test_superuser: UserModel):
    response = client.delete(f"/users/{test_superuser.id}", headers=normal_user_token_headers)
    assert response.status_code == 403

def test_deactivate_user_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.delete("/users/99999", headers=superuser_token_headers)
    assert response.status_code == 404

def test_deactivate_user_unauthenticated(client: TestClient, test_user: UserModel):
    response = client.delete(f"/users/{test_user.id}")
    assert response.status_code == 401

# Test GET /users/by-username/{username}
def test_get_by_username_superuser(client: TestClient, superuser_token_headers: dict, test_user: UserModel):
    response = client.get(f"/users/by-username/{test_user.username}", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email

def test_get_by_username_normal_user(client: TestClient, normal_user_token_headers: dict, test_user: UserModel):
    response = client.get(f"/users/by-username/{test_user.username}", headers=normal_user_token_headers)
    assert response.status_code == 403

def test_get_by_username_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.get("/users/by-username/nonexistentuser", headers=superuser_token_headers)
    assert response.status_code == 404

def test_get_by_username_unauthenticated(client: TestClient, test_user: UserModel):
    response = client.get(f"/users/by-username/{test_user.username}")
    assert response.status_code == 401

# Test GET /users/by-email/{email}
def test_get_by_email_superuser(client: TestClient, superuser_token_headers: dict, test_user: UserModel):
    response = client.get(f"/users/by-email/{test_user.email}", headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username

def test_get_by_email_normal_user(client: TestClient, normal_user_token_headers: dict, test_user: UserModel):
    response = client.get(f"/users/by-email/{test_user.email}", headers=normal_user_token_headers)
    assert response.status_code == 403

def test_get_by_email_not_found(client: TestClient, superuser_token_headers: dict):
    response = client.get("/users/by-email/nonexistent@example.com", headers=superuser_token_headers)
    assert response.status_code == 404

def test_get_by_email_unauthenticated(client: TestClient, test_user: UserModel):
    response = client.get(f"/users/by-email/{test_user.email}")
    assert response.status_code == 401

# Test that an inactive user cannot log in (implicitly tested by get_current_active_user dependency)
def test_inactive_user_cannot_login(client: TestClient, test_user: UserModel, db: Session):
    # Deactivate user
    test_user.is_active = False
    db.add(test_user)
    db.commit()

    # Create a token for the now inactive user
    from datetime import timedelta
    expires_delta = timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token, _ = security.create_access_token(
        data={"sub": test_user.username},
        expires_delta=expires_delta
    )
    inactive_user_headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/users/me", headers=inactive_user_headers)
    assert response.status_code == 403 # get_current_active_user should raise 403 for inactive user
    assert response.json()["detail"] == "Inactive user"

    # Reactivate user for other tests
    test_user.is_active = True
    db.add(test_user)
    db.commit()

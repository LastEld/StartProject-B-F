import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
from typing import Generator, Any

# Set environment variable for test database URL BEFORE importing settings or main app
# This ensures that when settings are loaded, they pick up the test DB URL.
# However, settings might already be loaded by the time conftest is processed in some scenarios.
# A more robust way is to override settings directly or ensure test-specific settings are loaded.
# For now, we rely on this being processed early.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
# Also override other relevant settings if necessary for testing
os.environ["SECRET_KEY"] = "testsecretkey"
os.environ["FIRST_SUPERUSER_USERNAME"] = "testadmin"
os.environ["FIRST_SUPERUSER_EMAIL"] = "testadmin@example.com"
os.environ["FIRST_SUPERUSER_PASSWORD"] = "testpassword"


# Crucial: Import all model modules FIRST via app.models (which executes app/models/__init__.py)
# This ensures Base.metadata is populated before Base is used by engine creation or create_all.
import app.models

# Then import Base (which should now be aware of all models from the above import)
from app.models.base import Base

# Import settings and override them BEFORE engine creation and app import
from app.core.settings import settings as app_settings
app_settings.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")
app_settings.SECRET_KEY = os.getenv("SECRET_KEY", "testsecretkey")
app_settings.FIRST_SUPERUSER_USERNAME = os.getenv("FIRST_SUPERUSER_USERNAME", "testadmin")
app_settings.FIRST_SUPERUSER_EMAIL = os.getenv("FIRST_SUPERUSER_EMAIL", "testadmin@example.com")
app_settings.FIRST_SUPERUSER_PASSWORD = os.getenv("FIRST_SUPERUSER_PASSWORD", "testpassword")

# Import the FastAPI app AFTER settings are overridden and models are loaded.
# This ensures that when the app and its routers are initialized, they see the correct Base and models.
from app.main import app

# Engine and SessionLocal setup using the overridden settings
SQLALCHEMY_DATABASE_URL = app_settings.DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import other necessary components for fixtures
from app.dependencies import get_db
from app.crud.user import create_user, get_user_by_username # For fixtures
from app.schemas.user import UserCreate # For fixtures
from app.core import security # For fixtures


@pytest.fixture(scope="session", autouse=True)
def create_test_tables_session_scope(): # Renamed for clarity
    """
    Create all tables once per test session, ensuring a clean state.
    Drops all tables first, then creates them. Drops them again after the session.
    """
    # Import all models here to ensure they are registered with Base.metadata
    # before create_all is called. This can help if models are in different files
    # and not automatically imported by the time conftest runs.
    # This is a common pattern to ensure Base.metadata is fully populated.

    # Example: Assuming your models are in app.models.<model_name>
    # You would list all your model modules here.
    # For now, importing app.main should have triggered most model imports via routers.
    # If specific models are missed, they can be explicitly imported here.
    # e.g. from app.models import user, project, task, team, template, plugin, devlog, settings_model etc.
    # (assuming settings_model to avoid conflict with app_settings)

    # For a more robust collection of all models, you might need to iterate through your models directory
    # or have a central place where all models are imported (e.g., app/models/__init__.py)
    # and then import that central place.

    # Let's ensure app.main (which imports routers, which import models) is fully processed.
    # The import of app from app.main should already achieve this if models are imported during app setup.

    Base.metadata.drop_all(bind=engine)  # Ensure a clean slate
    Base.metadata.create_all(bind=engine) # Create all tables
    yield
    Base.metadata.drop_all(bind=engine) # Clean up after tests


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Fixture to provide a database session for each test function.
    Rolls back any changes after the test to ensure test isolation.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Fixture to provide a TestClient instance for API testing.
    Overrides the `get_db` dependency to use the test database session.
    """
    def override_get_db():
        try:
            yield db
        finally:
            db.close() # Should be handled by the db fixture's cleanup

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    del app.dependency_overrides[get_db] # Clean up override


@pytest.fixture(scope="function")
def test_superuser(db: Session) -> Any:
    """
    Creates a superuser for testing.
    """
    user_in = UserCreate(
        username=app_settings.FIRST_SUPERUSER_USERNAME,
        email=app_settings.FIRST_SUPERUSER_EMAIL,
        password=app_settings.FIRST_SUPERUSER_PASSWORD,
        full_name="Test Super User",
        is_superuser=True,
        is_active=True
    )
    user = get_user_by_username(db, username=user_in.username)
    if not user:
      user = create_user(db=db, data=user_in.model_dump())
    return user

@pytest.fixture(scope="function")
def test_user(db: Session) -> Any:
    """
    Creates a normal user for testing.
    """
    user_in = UserCreate(
        username="testuser",
        email="testuser@example.com",
        password="testpassword",
        full_name="Test Normal User",
        is_superuser=False,
        is_active=True
    )
    user = get_user_by_username(db, username=user_in.username)
    if not user:
      user = create_user(db=db, data=user_in.model_dump())
    return user

@pytest.fixture(scope="function")
def superuser_token_headers(test_superuser: Any) -> dict[str, str]:
    """
    Returns headers with a token for the test_superuser.
    """
    from datetime import timedelta
    expires_delta = timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token, _ = security.create_access_token(
        data={"sub": test_superuser.username},
        expires_delta=expires_delta
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def normal_user_token_headers(test_user: Any) -> dict[str, str]:
    """
    Returns headers with a token for the test_user.
    """
    from datetime import timedelta
    expires_delta = timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token, _ = security.create_access_token(
        data={"sub": test_user.username},
        expires_delta=expires_delta
    )
    return {"Authorization": f"Bearer {token}"}

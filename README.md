# Project Backend API

## Overview

This project provides a robust backend API for managing various resources including users, projects, tasks, and more. It features JWT-based authentication, data validation using Pydantic, and database interactions via SQLAlchemy with Alembic for migrations. The API is built using the FastAPI framework.

## Features

*   User Authentication (JWT-based: access and refresh tokens)
*   User Management (CRUD operations)
*   Project Management
*   Task Tracking
*   Plugin System
*   Templating Engine
*   AI Context Storage
*   Development Logging
*   Team Management
*   Application Settings Configuration

## Prerequisites

*   Python 3.10+
*   Pip (Python Package Installer)
*   Git (Optional, for cloning)

## Setup & Installation

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository-url>
    cd <project-directory>
    ```

2.  **Navigate to the project directory:**
    ```bash
    cd path/to/your/project
    ```

3.  **Create and activate a Python virtual environment:**
    *   On macOS and Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```

4.  **Install dependencies:**

    *   For production or basic usage, install base dependencies:
        ```bash
        pip install -r requirements.txt
        ```
    *   For development (including tools for testing, migrations, etc.), install development dependencies as well:
        ```bash
        pip install -r requirements-dev.txt
        ```
        *(Note: `requirements-dev.txt` typically includes all dependencies from `requirements.txt` plus development-specific ones. However, if it only contains the *additional* dev dependencies, you might need to run both commands or ensure your dev requirements file includes the base ones using `-r requirements.txt` at its top.)*
        For this project, `requirements-dev.txt` contains only the additional development dependencies, so you should install both:
        ```bash
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        ```

## Configuration

Configuration for the application is managed via environment variables, typically loaded from a `.env` file.

1.  **Create a `.env` file:**
    Copy the example configuration file to a new `.env` file in the project root:
    ```bash
    cp .env.example .env
    ```

2.  **Key Environment Variables:**
    Open the `.env` file and set the following variables:

    *   `DATABASE_URL`: The connection string for your database.
        *   **SQLite Example:** `DATABASE_URL=sqlite:///./test.db` (for local development/testing) or `DATABASE_URL=sqlite:///./prod.db`
        *   **PostgreSQL Example:** `DATABASE_URL=postgresql+psycopg2://user:password@host:port/dbname`
            *(Ensure you have `psycopg2-binary` installed if using PostgreSQL: `pip install psycopg2-binary`)*

    *   `SECRET_KEY`: A strong, random string used for signing JWT tokens and other security purposes. Its secrecy is crucial.
        *   You can generate one using: `openssl rand -hex 32`

    *   `JWT_ALGORITHM`: The algorithm used for JWT encoding (default: `HS256`).
        *   Example: `JWT_ALGORITHM=HS256`

    *   `ACCESS_TOKEN_EXPIRE_MINUTES`: Lifetime of an access token in minutes.
        *   Example: `ACCESS_TOKEN_EXPIRE_MINUTES=60`

    *   `REFRESH_TOKEN_EXPIRE_DAYS`: Lifetime of a refresh token in days.
        *   Example: `REFRESH_TOKEN_EXPIRE_DAYS=30`

    *   `ENV`: The application environment.
        *   Example: `ENV=development` or `ENV=production`

    *   `DEBUG`: Toggles debug mode for FastAPI.
        *   Example: `DEBUG=True` or `DEBUG=False`

    *   `ALLOWED_ORIGINS`: A comma-separated list of allowed origins for CORS.
        *   Example: `ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"` (Note: In `.env` this might need to be a JSON-like string if `pydantic-settings` expects a list directly, or handle parsing in `settings.py`)
        *(Refer to `app/core/settings.py` for how `ALLOWED_ORIGINS` is parsed; the current code expects a list directly which is hard to set via a simple string in .env without custom parsing or specific `pydantic-settings` features for list conversion.)*

    *   `FIRST_SUPERUSER_USERNAME`: Username for the initial superuser created by `app/initial_data.py`.
        *   Example: `FIRST_SUPERUSER_USERNAME=admin`
    *   `FIRST_SUPERUSER_EMAIL`: Email for the initial superuser.
        *   Example: `FIRST_SUPERUSER_EMAIL=admin@example.com`
    *   `FIRST_SUPERUSER_PASSWORD`: Password for the initial superuser.
        *   Example: `FIRST_SUPERUSER_PASSWORD=adminpassword` (Ensure this is changed for any non-local deployment if used directly).

## Database Migrations (Alembic)

This project uses Alembic to manage database schema migrations.

*   **To apply all pending migrations to your database:**
    ```bash
    alembic upgrade head
    ```

*   **To create a new migration file after making changes to SQLAlchemy models:**
    ```bash
    alembic revision -m "Your descriptive migration message"
    ```
    Then, edit the generated migration script in `alembic/versions/` to define the `upgrade` and `downgrade` operations.

## Running the Application

To start the FastAPI development server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

*   `--reload`: Enables auto-reloading when code changes (for development).
*   `--host 0.0.0.0`: Makes the server accessible from your local network.
*   `--port 8000`: Specifies the port to run on.

The application will be available at `http://localhost:8000` or `http://<your-ip>:8000`.

## Seeding Initial Data

The project includes a script to populate the database with initial data, such as a default admin user.

*   **To run the seeding script:**
    ```bash
   python -m app.initial_data
    ```

*   **Default Admin Credentials (if applicable, check `app/initial_data.py` for specifics):**
    *   Username: `admin`
    *   Password: `adminpassword` (This should be changed immediately in a production environment or made configurable via environment variables for initial setup).

## Running Tests

This project uses `pytest` for running automated tests.

*   **To run all tests:**
    ```bash
    pytest
    ```
    Or for more verbose output:
    ```bash
    pytest -v
    ```

*   **To generate a test coverage report (if `pytest-cov` is installed):**
    ```bash
    pip install pytest-cov  # If not already in requirements.txt
    pytest --cov=app
    ```
    This will show test coverage for the `app` directory.

## API Documentation

FastAPI automatically generates interactive API documentation. Once the server is running, you can access it at:

*   **Swagger UI:** `http://localhost:8000/docs`
*   **ReDoc:** `http://localhost:8000/redoc`

## API Usage Examples

Here are a few examples of how to interact with the API using cURL. Replace placeholders like `<YOUR_TOKEN>`, `<PROJECT_ID>`, etc., with actual values.

### 1. User Login

To obtain an access token:

```bash
curl -X POST "http://localhost:8000/auth/login" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=yourusername&password=yourpassword"
```

Replace `yourusername` and `yourpassword` with actual user credentials (e.g., the first superuser credentials if you've run `app/initial_data.py`). The response will contain an `access_token`.

### 2. Create a New Project (Superuser only)

You'll need the `access_token` obtained from login. Set it as a Bearer token in the Authorization header.

```bash
ACCESS_TOKEN="<YOUR_ACCESS_TOKEN>" # Replace with your actual token

curl -X POST "http://localhost:8000/projects/" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{
  "name": "My New Awesome Project",
  "description": "This is a detailed description of the new project.",
  "status": "active",
  "deadline": "2024-12-31",
  "tags": ["new-feature", "q4-goal"],
  "is_favorite": true
}'
```
*(Note: Project creation is typically restricted to superusers as per the current API implementation in `app/api/project.py`.)*

### 3. List Tasks (Example: for a specific project)

You'll need an `access_token`.

```bash
ACCESS_TOKEN="<YOUR_ACCESS_TOKEN>" # Replace with your actual token
PROJECT_ID="<PROJECT_ID_TO_FILTER_BY>" # Replace with an actual Project ID

curl -X GET "http://localhost:8000/tasks/?project_id=$PROJECT_ID" \
-H "Authorization: Bearer $ACCESS_TOKEN"
```
*(Note: Non-superusers might be restricted to tasks within projects they have access to, or may need to provide a `project_id`. Superusers can typically list more broadly. Check `app/api/task.py` for specific authorization rules for listing tasks.)*


## Project Structure (Overview)

```
.
├── alembic/                   # Database migration scripts
│   └── versions/
├── app/                       # Main application module
│   ├── api/                   # API endpoint definitions (routers)
│   ├── core/                  # Core components (settings, security)
│   ├── crud/                  # CRUD operations (database interaction logic)
│   ├── database.py            # Database session setup
│   ├── dependencies.py        # FastAPI dependencies
│   ├── initial_data.py        # Script for initial data seeding
│   ├── main.py                # FastAPI application entry point
│   ├── models/                # SQLAlchemy database models
│   ├── schemas/               # Pydantic data validation schemas
│   └── services/              # Business logic services (if any)
├── tests/                     # Automated tests
├── .env.example               # Example environment variables file
├── alembic.ini                # Alembic configuration file
├── requirements.txt           # Application dependencies
└── README.md                  # This file
```

## Contributing

Contributions are welcome! If you'd like to contribute, please follow these general guidelines:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix (e.g., `feature/new-widget` or `fix/login-bug`).
3.  Make your changes, adhering to the project's coding style and conventions.
4.  Write tests for your changes.
5.  Ensure all tests pass.
6.  Submit a pull request with a clear description of your changes.

(More detailed contribution guidelines can be added if needed, e.g., regarding code style, commit messages, etc.)

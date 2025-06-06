#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# --- Backend .env check ---
BACKEND_ENV_FILE="app/.env"
ROOT_ENV_EXAMPLE=".env.example" # Actual path for backend .env example

echo "--- Backend (.env) Check ---"
if [ -f "$BACKEND_ENV_FILE" ]; then
    echo "$BACKEND_ENV_FILE found."
else
    echo "$BACKEND_ENV_FILE not found."
    if [ -f "$ROOT_ENV_EXAMPLE" ]; then
        echo "Copying $ROOT_ENV_EXAMPLE to $BACKEND_ENV_FILE..."
        cp "$ROOT_ENV_EXAMPLE" "$BACKEND_ENV_FILE"
        echo "$BACKEND_ENV_FILE created from $ROOT_ENV_EXAMPLE."
    else
        echo "ERROR: $ROOT_ENV_EXAMPLE not found. Cannot create $BACKEND_ENV_FILE."
        # exit 1 # Do not exit, just report
    fi
fi

# Check for key backend variables
echo "Checking for DATABASE_URL and SECRET_KEY in backend .env file..."
ENV_FILE_TO_CHECK_BACKEND="$BACKEND_ENV_FILE"
if [ ! -f "$ENV_FILE_TO_CHECK_BACKEND" ]; then
    # If app/.env still doesn't exist (because example wasn't found), check the example itself if it exists
    if [ -f "$ROOT_ENV_EXAMPLE" ]; then
        ENV_FILE_TO_CHECK_BACKEND="$ROOT_ENV_EXAMPLE"
        echo "Checking $ROOT_ENV_EXAMPLE for variables as $BACKEND_ENV_FILE was not created."
    else
        echo "ERROR: Neither $BACKEND_ENV_FILE nor $ROOT_ENV_EXAMPLE found to check for variables."
        # exit 1 # Do not exit
    fi
fi

if [ -f "$ENV_FILE_TO_CHECK_BACKEND" ]; then
    if grep -q "DATABASE_URL=" "$ENV_FILE_TO_CHECK_BACKEND"; then
        echo "DATABASE_URL is present in $ENV_FILE_TO_CHECK_BACKEND."
    else
        echo "WARNING: DATABASE_URL is NOT present in $ENV_FILE_TO_CHECK_BACKEND."
    fi
    if grep -q "SECRET_KEY=" "$ENV_FILE_TO_CHECK_BACKEND"; then
        echo "SECRET_KEY is present in $ENV_FILE_TO_CHECK_BACKEND."
    else
        echo "WARNING: SECRET_KEY is NOT present in $ENV_FILE_TO_CHECK_BACKEND."
    fi
else
    echo "No backend .env file to check for variables."
fi
echo "Backend check complete."
echo ""

# --- Frontend .env check ---
FRONTEND_ENV_FILE="frontend/.env"
FRONTEND_ENV_LOCAL="frontend/.env.local"
# Attempt to find a suitable example file for frontend
FRONTEND_ENV_EXAMPLE=""
if [ -f "frontend/.env.example" ]; then
    FRONTEND_ENV_EXAMPLE="frontend/.env.example"
elif [ -f "frontend/.env.local.example" ]; then
    FRONTEND_ENV_EXAMPLE="frontend/.env.local.example"
fi

echo "--- Frontend (.env) Check ---"
# Prefer .env.local if it exists, otherwise .env
ACTUAL_FRONTEND_ENV_FILE="$FRONTEND_ENV_LOCAL"
if [ -f "$ACTUAL_FRONTEND_ENV_FILE" ]; then
    echo "$ACTUAL_FRONTEND_ENV_FILE found."
else
    echo "$FRONTEND_ENV_LOCAL not found. Checking for $FRONTEND_ENV_FILE..."
    ACTUAL_FRONTEND_ENV_FILE="$FRONTEND_ENV_FILE"
    if [ -f "$ACTUAL_FRONTEND_ENV_FILE" ]; then
        echo "$ACTUAL_FRONTEND_ENV_FILE found."
    else
        echo "$FRONTEND_ENV_FILE not found."
        if [ -n "$FRONTEND_ENV_EXAMPLE" ]; then
            # Decide target for copying example: .env.local is common for Next.js
            TARGET_FRONTEND_ENV_FILE="$FRONTEND_ENV_LOCAL"
            echo "Copying $FRONTEND_ENV_EXAMPLE to $TARGET_FRONTEND_ENV_FILE..."
            cp "$FRONTEND_ENV_EXAMPLE" "$TARGET_FRONTEND_ENV_FILE"
            ACTUAL_FRONTEND_ENV_FILE="$TARGET_FRONTEND_ENV_FILE" # Update to the newly created file
            echo "$TARGET_FRONTEND_ENV_FILE created from $FRONTEND_ENV_EXAMPLE."
        else
            echo "ERROR: No example .env file found for frontend (e.g., frontend/.env.example or frontend/.env.local.example)."
            # exit 1 # Do not exit
        fi
    fi
fi

# Check for key frontend variable
echo "Checking for NEXT_PUBLIC_API_URL in frontend .env file..."
ENV_FILE_TO_CHECK_FRONTEND="$ACTUAL_FRONTEND_ENV_FILE"

# If the chosen env file (e.g. .env.local) was not found and not created from example,
# we might need to check the example file itself if it exists and was specified.
if [ ! -f "$ENV_FILE_TO_CHECK_FRONTEND" ] && [ -n "$FRONTEND_ENV_EXAMPLE" ] && [ -f "$FRONTEND_ENV_EXAMPLE" ]; then
    ENV_FILE_TO_CHECK_FRONTEND="$FRONTEND_ENV_EXAMPLE"
    echo "Checking $FRONTEND_ENV_EXAMPLE for variables as $ACTUAL_FRONTEND_ENV_FILE was not found/created."
fi

if [ -f "$ENV_FILE_TO_CHECK_FRONTEND" ]; then
    if grep -q "NEXT_PUBLIC_API_URL=" "$ENV_FILE_TO_CHECK_FRONTEND"; then
        echo "NEXT_PUBLIC_API_URL is present in $ENV_FILE_TO_CHECK_FRONTEND."
    else
        echo "WARNING: NEXT_PUBLIC_API_URL is NOT present in $ENV_FILE_TO_CHECK_FRONTEND."
    fi
else
    echo "No frontend .env file to check for variables."
fi
echo "Frontend check complete."
echo ""

# --- Repository Structure Check ---
echo "--- Repository Structure Check ---"
BACKEND_DIR="app"
FRONTEND_DIR="frontend"

if [ -d "$BACKEND_DIR" ]; then
    echo "Backend directory '$BACKEND_DIR' found."
else
    echo "ERROR: Backend directory '$BACKEND_DIR' NOT found."
    # exit 1 # Do not exit
fi

if [ -d "$FRONTEND_DIR" ]; then
    echo "Frontend directory '$FRONTEND_DIR' found."
else
    echo "ERROR: Frontend directory '$FRONTEND_DIR' NOT found."
    # exit 1 # Do not exit
fi
echo "Repository structure check complete."
echo ""
echo "Setup and Diagnostics subtask finished."


# app/initial_data.py

import asyncio
import logging
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.crud.user import create_user as crud_create_user, get_user_by_username
from app.core.settings import settings
from app.core.exceptions import ProjectValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DevOS.InitialData")

async def create_initial_admin_user(db: Session) -> None:
    logger.info("Checking if initial admin user needs to be created...")
    superuser_username = settings.FIRST_SUPERUSER_USERNAME
    superuser_email = settings.FIRST_SUPERUSER_EMAIL
    superuser_password = settings.FIRST_SUPERUSER_PASSWORD

    admin_user = get_user_by_username(db, username=superuser_username)
    if not admin_user:
        logger.info(f"Admin user '{superuser_username}' not found. Creating...")
        user_data = {
            "username": superuser_username,
            "email": superuser_email,
            "password": superuser_password,
            "full_name": "Admin User",
            "is_active": True,
            "is_superuser": True,
            "roles": ["admin", "superuser"],
        }
        try:
            crud_create_user(db=db, data=user_data)
            logger.info(f"Admin user '{superuser_username}' created successfully.")
        except ProjectValidationError as e:
            logger.error(f"Failed to create admin user: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during admin user creation: {e}", exc_info=True)
    else:
        logger.info(f"Admin user '{superuser_username}' already exists. No action taken.")

async def main() -> None:
    logger.info("Initializing initial data (admin user)...")
    db = SessionLocal()
    try:
        await create_initial_admin_user(db)
    finally:
        db.close()
    logger.info("Finished initial data setup.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    asyncio.run(main())

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from database import SessionLocal
from fastapi import FastAPI
from models import User
from routes import router
from security import hash_password

logger = logging.getLogger(__name__)


async def create_initial_admin_user():
    """Create admin user from environment variables if none exists"""
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_email = os.getenv("ADMIN_EMAIL", "email@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "password")

    # Skip if environment variables are not set
    if not all([admin_username, admin_email, admin_password]):
        logger.warning("ℹ️ Admin credentials not provided in environment variables")

    db = SessionLocal()
    try:
        # Validate password length
        if len(admin_password) < 8:
            print("❌ Admin password too short (min 8 chars), skipping admin creation")
            return

        # Create admin user
        hashed_password = hash_password(admin_password)
        admin_user = User(
            username=admin_username,
            email=admin_email,
            hashed_password=hashed_password,
            is_admin=True,
            is_active=True,
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("✅ Admin user created successfully!")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email}")
        print(f"   ID: {admin_user.id}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    print("🚀 Starting Authentication Service...")
    await create_initial_admin_user()
    print("✅ Startup complete")

    yield  # This is where the app runs

    # Shutdown (optional cleanup)
    print("🛑 Shutting down Authentication Service...")


app = FastAPI(
    title="Authentication Service",
    description="JWT + Database authentication for microservices architecture",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router, tags=["Authentication"])


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,  # Remove in production
        log_level="info",
    )

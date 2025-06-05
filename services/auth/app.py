# services/auth/app.py
# Monolithic authentication service with JWT + Database verification
# TODO: Later split into separate modules as indicated by comments

from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from services.auth.crud import (
    get_db,
    get_user_by_id,
)
from services.auth.models import User
from services.auth.security import verify_jwt_token

# ============================================================================
# AUTHENTICATION DEPENDENCIES SECTION
# TODO: Move to dependencies.py later
# ============================================================================

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Main authentication dependency: JWT + Database verification
    1. Verify JWT signature and expiration
    2. Lookup user in database to check current status
    3. Return active user or raise 401
    """
    # Step 1: Verify JWT token
    token_data = verify_jwt_token(credentials.credentials)

    # Step 2: Database lookup to get current user state
    user = get_user_by_id(db, token_data.user_id)

    if not user:
        # User was deleted or deactivated since token was issued
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists"
        )

    if not user.is_active:
        # User was deactivated since token was issued
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is disabled"
        )

    # TODO: Add token blacklist check here later (for immediate token revocation)

    return user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin privileges"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


async def get_premium_user(current_user: User = Depends(get_current_user)) -> User:
    """Require premium subscription"""
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required",
        )
    return current_user


async def get_optional_user(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional authentication - returns None if no valid token"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    try:
        token = auth_header.split(" ")[1]
        token_data = verify_jwt_token(token)
        user = get_user_by_id(db, token_data.user_id)
        return user if user and user.is_active else None
    except:
        return None


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    # Check for forwarded IP first (for reverse proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Authentication Service",
    description="JWT + Database authentication for microservices architecture",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================================
# MAIN APPLICATION RUNNER
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,  # Remove in production
        log_level="info",
    )

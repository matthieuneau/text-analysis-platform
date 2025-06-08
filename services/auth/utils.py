from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from services.auth.crud import get_user_by_id
from services.auth.database import get_db
from services.auth.models import User
from services.auth.security import verify_jwt_token
from services.gateway.utils import get_current_user

security = HTTPBearer()


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin privileges"""
    if current_user.is_admin is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


async def get_premium_user(current_user: User = Depends(get_current_user)) -> User:
    """Require premium subscription"""
    if current_user.is_premium is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required",
        )
    return current_user


async def get_optional_user(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    """Optional authentication - returns None if no valid token"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    try:
        token = auth_header.split(" ")[1]
        token_data = verify_jwt_token(token)
        user = get_user_by_id(db, token_data.user_id)
        return user if user and user.is_active else None
    except:  # noqa: E722
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

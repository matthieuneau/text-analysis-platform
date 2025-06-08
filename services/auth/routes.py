from datetime import datetime

from config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from crud import (
    create_user,
    get_user_by_id,
    get_user_by_username,
    log_audit_event,
    update_user_login,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt  # type: ignore
from models import AuditLog, RefreshToken, User
from security import create_access_token, create_refresh_token, verify_password
from sqlalchemy.orm import Session

from services.auth.database import get_db
from services.auth.schemas import (
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserProfile,
    UserRegister,
)
from services.auth.utils import get_admin_user, get_client_ip
from services.gateway.utils import get_current_user

router = APIRouter()


@router.post("/register", response_model=UserProfile)
async def register_user(
    user_data: UserRegister, request: Request, db: Session = Depends(get_db)
):
    """Register a new user account"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    try:
        # Create user
        user = create_user(db, user_data)

        # Log successful registration
        log_audit_event(
            db,
            user.id,
            user.username,
            "register",
            True,
            client_ip,
            user_agent,
            f"User registered with email: {user.email}",
        )

        return user

    except HTTPException as e:
        # Log failed registration attempt
        log_audit_event(
            db,
            None,
            user_data.username,
            "register",
            False,
            client_ip,
            user_agent,
            f"Registration failed: {e.detail}",
        )
        raise


@router.post("/login", response_model=TokenResponse)
async def login_user(
    credentials: UserLogin, request: Request, db: Session = Depends(get_db)
):
    """Authenticate user and return JWT tokens"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    # Get user by username
    user = get_user_by_username(db, credentials.username)

    # Verify user exists and password is correct
    if not user or not verify_password(credentials.password, user.hashed_password):
        # Log failed login attempt
        log_audit_event(
            db,
            user.id if user else None,
            credentials.username,
            "login",
            False,
            client_ip,
            user_agent,
            "Invalid credentials",
        )

        # Generic error message for security
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Check if user account is active
    if not user.is_active:
        log_audit_event(
            db,
            user.id,
            user.username,
            "login",
            False,
            client_ip,
            user_agent,
            "Account disabled",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is disabled"
        )

    # Create tokens
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user, db, user_agent, client_ip)

    # Update user's last login
    update_user_login(db, user)

    # Log successful login
    log_audit_event(
        db,
        user.id,
        user.username,
        "login",
        True,
        client_ip,
        user_agent,
        "Successful login",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    token_data: TokenRefresh, request: Request, db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    try:
        # Verify refresh token
        payload = jwt.decode(
            token_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM]
        )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        user_id = payload.get("user_id")
        if not user_id or not isinstance(user_id, int):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Check if refresh token exists in database and is not revoked
        db_token = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token == token_data.refresh_token,
                RefreshToken.user_id == user_id,
                ~RefreshToken.is_revoked,
                RefreshToken.expires_at > datetime.utcnow(),
            )
            .first()
        )

        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        # Get user and verify they're still active
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists"
            )

        # Create new tokens
        new_access_token = create_access_token(user)
        new_refresh_token = create_refresh_token(user, db, user_agent, client_ip)

        # Revoke old refresh token (token rotation for security)
        db_token.is_revoked = True
        db.commit()

        # Log token refresh
        log_audit_event(
            db,
            user.id,
            user.username,
            "token_refresh",
            True,
            client_ip,
            user_agent,
            "Token refreshed successfully",
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    except JWTError:
        # Log failed refresh attempt
        log_audit_event(
            db,
            None,
            None,
            "token_refresh",
            False,
            client_ip,
            user_agent,
            "Invalid refresh token",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout_user(
    token_data: TokenRefresh,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logout user by revoking refresh token"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    # Revoke the refresh token
    db_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token == token_data.refresh_token,
            RefreshToken.user_id == current_user.id,
            ~RefreshToken.is_revoked,
        )
        .first()
    )

    if db_token:
        db_token.is_revoked = True
        db.commit()

    # Log logout
    log_audit_event(
        db,
        current_user.id,
        current_user.username,
        "logout",
        True,
        client_ip,
        user_agent,
        "User logged out",
    )

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile information"""
    return current_user


@router.get("/verify-token")
async def verify_token_endpoint(current_user: User = Depends(get_current_user)):
    """Verify if token is valid (for other services to call)"""
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "is_premium": current_user.is_premium,
        "is_active": current_user.is_active,
    }


# ============================================================================
# ADMIN ROUTES SECTION
# ============================================================================


@router.get("/admin/users")
async def get_all_users(
    admin_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Admin: Get all users"""
    users = db.query(User).all()
    return {
        "users": [UserProfile.from_orm(user) for user in users],
        "total_count": len(users),
    }


@router.put("/admin/users/{user_id}/toggle-active")
async def toggle_user_active_status(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Admin: Activate/deactivate user account"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_active = not user.is_active
    db.commit()

    return {
        "message": f"User {user.username} {'activated' if user.is_active else 'deactivated'}",
        "is_active": user.is_active,
    }


@router.get("/admin/audit-logs")
async def get_audit_logs(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    limit: int = 100,
):
    """Admin: Get recent audit logs"""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return {"logs": logs, "count": len(logs)}


# ============================================================================
# HEALTH CHECK AND UTILITY ROUTES
# ============================================================================


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    # Test database connection
    try:
        user_count = db.query(User).count()
        return {
            "status": "healthy",
            "service": "authentication",
            "version": "1.0.0",
            "database": "connected",
            "user_count": user_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        )


@router.get("/stats")
async def get_auth_stats(db: Session = Depends(get_db)):
    """Public statistics about the auth service"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "service_uptime": "healthy",  # TODO: Add actual uptime tracking
    }

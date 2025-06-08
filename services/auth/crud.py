from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from models import AuditLog, User
from schemas import UserRegister
from security import hash_password
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID with caching potential"""
    # TODO: Add caching layer here later
    return db.query(User).filter(User.id == user_id, User.is_active).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user_data: UserRegister) -> User:
    """Create new user with validation"""
    # Check if username or email already exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create user
    hashed_password = hash_password(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        api_calls_reset_date=datetime.utcnow(),
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User creation failed - duplicate data",
        )


def update_user_login(db: Session, user: User):
    """Update user's last login timestamp"""
    user.last_login = datetime.utcnow()
    db.commit()


def increment_api_calls(db: Session, user: User):
    """Increment user's daily API call counter"""
    today = datetime.utcnow().date()
    if user.api_calls_reset_date.date() != today:
        # Reset counter for new day
        user.api_calls_today = 1
        user.api_calls_reset_date = datetime.utcnow()
    else:
        user.api_calls_today += 1

    db.commit()


def log_audit_event(
    db: Session,
    user_id: Optional[int],
    username: Optional[str],
    event_type: str,
    success: bool,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: str | None = None,
):
    """Log security audit event"""
    audit_log = AuditLog(
        user_id=user_id,
        username=username,
        event_type=event_type,
        success=success,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
    )
    db.add(audit_log)
    db.commit()

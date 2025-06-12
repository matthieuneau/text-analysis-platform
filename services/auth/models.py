from datetime import datetime
from typing import List, Optional

from database import engine
from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """User model with authentication and profile data"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # User status and metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Rate limiting and usage tracking
    api_calls_today: Mapped[int] = mapped_column(Integer, default=0)
    api_calls_reset_date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class RefreshToken(Base):
    """Refresh tokens for secure token rotation"""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Token data
    token: Mapped[str] = mapped_column(
        String(500), unique=True, index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Token metadata
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Security tracking
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)


class AuditLog(Base):
    """Security audit log for tracking authentication events"""

    __tablename__ = "audit_logs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User reference (nullable for failed login attempts)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # For failed attempts

    # Event details
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # login, logout, register, token_refresh, etc.
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional context
    details: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string for additional event data
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )


# Create indexes for better query performance
Index("idx_users_email_active", User.email, User.is_active)
Index("idx_refresh_tokens_user_active", RefreshToken.user_id, RefreshToken.is_revoked)
Index("idx_audit_logs_user_time", AuditLog.user_id, AuditLog.timestamp)

# Create all tables
Base.metadata.create_all(bind=engine)


# TODO: change to List[int] ??
class TokenizedTextResponse(BaseModel):
    original_text: str
    tokens: List[str]
    token_count: int

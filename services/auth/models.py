from datetime import datetime

from config import DATABASE_URL
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Database setup
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    """User model with authentication and profile data"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # User status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Rate limiting and usage tracking
    api_calls_today = Column(Integer, default=0)
    api_calls_reset_date = Column(DateTime, default=datetime.utcnow)


class RefreshToken(Base):
    """Refresh tokens for secure token rotation"""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, index=True, nullable=False)
    user_id = Column(Integer, nullable=False, index=True)

    # Token metadata
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Security tracking
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)


class AuditLog(Base):
    """Security audit log for tracking authentication events"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, nullable=True, index=True
    )  # Nullable for failed login attempts
    username = Column(String(50), nullable=True)  # For failed attempts

    # Event details
    event_type = Column(
        String(50), nullable=False
    )  # login, logout, register, token_refresh, etc.
    success = Column(Boolean, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Additional context
    details = Column(Text, nullable=True)  # JSON string for additional event data
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


# Create indexes for better query performance
Index("idx_users_email_active", User.email, User.is_active)
Index("idx_refresh_tokens_user_active", RefreshToken.user_id, RefreshToken.is_revoked)
Index("idx_audit_logs_user_time", AuditLog.user_id, AuditLog.timestamp)

# Create all tables
Base.metadata.create_all(bind=engine)

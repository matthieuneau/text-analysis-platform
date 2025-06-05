import uuid
from datetime import datetime, timedelta

import bcrypt
from schemas import TokenPayload


def hash_password(password: str) -> str:
    """Hash password using bcrypt with salt"""
    salt = bcrypt.gensalt(rounds=12)  # Cost factor 12 for good security
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(user: User) -> str:
    """Create JWT access token with minimal payload"""
    now = datetime.utcnow()
    jti = str(uuid.uuid4())  # Unique token ID for potential revocation

    payload = {
        "user_id": user.id,
        "username": user.username,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    user: User, db: Session, user_agent: str = None, ip_address: str = None
) -> str:
    """Create refresh token and store in database"""
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    # Create token payload
    payload = {
        "user_id": user.id,
        "jti": str(uuid.uuid4()),
        "exp": expires_at,
        "type": "refresh",
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    # Store token in database
    db_token = RefreshToken(
        token=token,
        user_id=user.id,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(db_token)
    db.commit()

    return token


def verify_jwt_token(token: str) -> TokenPayload:
    """Verify JWT token signature and expiration"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        return TokenPayload(
            user_id=payload["user_id"],
            username=payload["username"],
            jti=payload["jti"],
            iat=datetime.fromtimestamp(payload["iat"]),
            exp=datetime.fromtimestamp(payload["exp"]),
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

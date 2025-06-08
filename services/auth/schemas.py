from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    is_premium: bool
    created_at: datetime
    last_login: datetime | None
    api_calls_today: int

    class Config:
        from_attributes = True


class TokenPayload(BaseModel):
    """Internal model for JWT token data"""

    user_id: int
    username: str
    jti: str  # JWT ID for token tracking
    iat: datetime
    exp: datetime

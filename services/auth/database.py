# Database setup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.auth.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

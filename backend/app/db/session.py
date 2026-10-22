from typing import Generator, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logging import logger

sync_url = settings.sync_database_url

connect_args = {}
if "pg8000" in sync_url:
    connect_args = {"timeout": 3}
elif "psycopg" in sync_url or "postgresql" in sync_url:
    connect_args = {"connect_timeout": 3}
elif "sqlite" in sync_url:
    connect_args = {"check_same_thread": False}

# Create SQLAlchemy synchronous engine with pooling configuration
engine = create_engine(
    sync_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a database session.
    Ensures safe session termination and resource cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connectivity() -> Tuple[bool, str]:
    """
    Safely tests database connectivity without throwing unhandled exceptions
    or exposing connection credentials.

    Returns:
        Tuple[bool, str]: (is_connected, message)
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "Database connection established and responding"
    except SQLAlchemyError as exc:
        logger.warning("Database connectivity check failed: %s", type(exc).__name__)
        return False, "Database connection unavailable or rejected"
    except Exception as exc:
        logger.warning("Unexpected error during DB connectivity check: %s", type(exc).__name__)
        return False, "Database connectivity check failed"

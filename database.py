import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)
FALLBACK_SQLITE_URL = "sqlite:///./data/recruiteia_fallback.db"


def _build_engine(database_url: str):
    is_sqlite = database_url.startswith("sqlite")
    return create_engine(
        database_url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        pool_pre_ping=not is_sqlite,
    )


def _resolve_engine():
    """
    Prefer configured DATABASE_URL.
    If it is unreachable, fail over to local SQLite so auth/API remain operational.
    """
    primary_url = settings.database_url
    primary_engine = _build_engine(primary_url)

    if primary_url.startswith("sqlite"):
        return primary_engine, primary_url, False

    try:
        with primary_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return primary_engine, primary_url, False
    except Exception as db_err:
        Path("data").mkdir(parents=True, exist_ok=True)
        fallback_engine = _build_engine(FALLBACK_SQLITE_URL)
        logger.warning(
            "Primary DATABASE_URL unreachable (%s). Falling back to %s. Error: %s",
            primary_url,
            FALLBACK_SQLITE_URL,
            db_err,
        )
        return fallback_engine, FALLBACK_SQLITE_URL, True


engine, ACTIVE_DATABASE_URL, USING_FALLBACK_DB = _resolve_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

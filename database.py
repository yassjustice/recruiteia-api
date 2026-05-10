import logging
import os
import platform as _platform
from pathlib import Path

# Avoid slow/hanging WMI lookup on some Windows hosts during SQLAlchemy import.
if os.name == "nt":
    _platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE", "AMD64")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)
FALLBACK_SQLITE_URL = "sqlite:///./data/recruiteia_fallback.db"
_schema_ready = False


def _build_engine(database_url: str):
    is_sqlite = database_url.startswith("sqlite")
    return create_engine(
        database_url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        pool_pre_ping=not is_sqlite,
    )


def _activate_fallback(reason: Exception | str):
    global engine, SessionLocal, ACTIVE_DATABASE_URL, USING_FALLBACK_DB, _schema_ready
    if USING_FALLBACK_DB:
        return
    Path("data").mkdir(parents=True, exist_ok=True)
    engine = _build_engine(FALLBACK_SQLITE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    ACTIVE_DATABASE_URL = FALLBACK_SQLITE_URL
    USING_FALLBACK_DB = True
    _schema_ready = False
    logger.warning("Switched to fallback database %s. Reason: %s", FALLBACK_SQLITE_URL, reason)


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


def _ensure_primary_alive():
    if USING_FALLBACK_DB:
        return
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as db_err:
        _activate_fallback(db_err)


def _ensure_schema_ready():
    global _schema_ready
    if _schema_ready:
        return
    try:
        import src.api.models as models  # local import to avoid module cycles
        models.Base.metadata.create_all(bind=engine)
        _schema_ready = True
    except Exception as schema_err:
        if not USING_FALLBACK_DB:
            _activate_fallback(schema_err)
            import src.api.models as models
            models.Base.metadata.create_all(bind=engine)
            _schema_ready = True
        else:
            raise


class Base(DeclarativeBase):
    pass


def get_db():
    _ensure_primary_alive()
    _ensure_schema_ready()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

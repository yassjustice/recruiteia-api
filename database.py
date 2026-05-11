import logging
import os
import platform as _platform
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

# Avoid slow/hanging WMI lookup on some Windows hosts during SQLAlchemy import.
if os.name == "nt":
    _platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE", "AMD64")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

logger = logging.getLogger(__name__)

FALLBACK_SQLITE_URL = "sqlite:///./data/recruiteia_fallback.db"
PRIMARY_DATABASE_URL = settings.database_url
IS_DUAL_DB_MODE = not PRIMARY_DATABASE_URL.startswith("sqlite")


def _build_engine(database_url: str):
    is_sqlite = database_url.startswith("sqlite")
    return create_engine(
        database_url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        pool_pre_ping=not is_sqlite,
    )


def _safe_db_url(database_url: str) -> str:
    try:
        parsed = urlsplit(database_url)
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        path = parsed.path or ""
        safe_netloc = f"{host}{port}" if host else parsed.netloc
        return urlunsplit((parsed.scheme, safe_netloc, path, parsed.query, parsed.fragment))
    except Exception:
        return "unknown"


def _ping_engine(db_engine) -> tuple[bool, str | None]:
    try:
        with db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as db_err:
        return False, str(db_err)


class Base(DeclarativeBase):
    pass


Path("data").mkdir(parents=True, exist_ok=True)
PRIMARY_ENGINE = _build_engine(PRIMARY_DATABASE_URL)
FALLBACK_ENGINE = _build_engine(FALLBACK_SQLITE_URL)


def _resolve_initial_engine():
    if not IS_DUAL_DB_MODE:
        return PRIMARY_ENGINE, PRIMARY_DATABASE_URL, False

    ok, err = _ping_engine(PRIMARY_ENGINE)
    if ok:
        return PRIMARY_ENGINE, PRIMARY_DATABASE_URL, False

    logger.warning(
        "Primary DATABASE_URL unreachable (%s). Falling back to %s. Error: %s",
        _safe_db_url(PRIMARY_DATABASE_URL),
        _safe_db_url(FALLBACK_SQLITE_URL),
        err,
    )
    return FALLBACK_ENGINE, FALLBACK_SQLITE_URL, True


engine, ACTIVE_DATABASE_URL, USING_FALLBACK_DB = _resolve_initial_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
PrimarySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=PRIMARY_ENGINE)
FallbackSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=FALLBACK_ENGINE)

_schema_ready_by_key = {"active": False, "primary": False, "fallback": False}


def _switch_active_engine(use_fallback: bool, reason: str):
    global engine, ACTIVE_DATABASE_URL, USING_FALLBACK_DB

    if use_fallback and USING_FALLBACK_DB:
        return
    if (not use_fallback) and (not USING_FALLBACK_DB):
        return

    engine = FALLBACK_ENGINE if use_fallback else PRIMARY_ENGINE
    ACTIVE_DATABASE_URL = FALLBACK_SQLITE_URL if use_fallback else PRIMARY_DATABASE_URL
    USING_FALLBACK_DB = use_fallback
    SessionLocal.configure(bind=engine)
    _schema_ready_by_key["active"] = False

    target = "fallback" if use_fallback else "primary"
    logger.warning("Switched active database to %s. Reason: %s", target, reason)


def _ensure_primary_alive():
    if not IS_DUAL_DB_MODE:
        return

    primary_ok, primary_err = _ping_engine(PRIMARY_ENGINE)
    if primary_ok and USING_FALLBACK_DB:
        _switch_active_engine(False, "Primary database reachable again")
    elif (not primary_ok) and (not USING_FALLBACK_DB):
        _switch_active_engine(True, primary_err or "Primary database unreachable")


def _ensure_schema(bind_engine, schema_key: str):
    if _schema_ready_by_key.get(schema_key):
        return

    import src.api.models as models  # local import to avoid module cycles

    models.Base.metadata.create_all(bind=bind_engine)
    _schema_ready_by_key[schema_key] = True


def _ensure_schema_ready():
    # Always keep active DB schema ready.
    _ensure_schema(engine, "active")

    # For dual DB mode, keep fallback schema ready for immediate failover.
    if IS_DUAL_DB_MODE:
        try:
            _ensure_schema(FALLBACK_ENGINE, "fallback")
        except Exception as fallback_err:
            logger.warning("Could not ensure fallback schema: %s", fallback_err)

        primary_ok, _ = _ping_engine(PRIMARY_ENGINE)
        if primary_ok:
            try:
                _ensure_schema(PRIMARY_ENGINE, "primary")
            except Exception as primary_err:
                logger.warning("Could not ensure primary schema: %s", primary_err)


def get_primary_session_factory():
    return PrimarySessionLocal


def get_fallback_session_factory():
    return FallbackSessionLocal


def get_database_health_snapshot() -> dict:
    primary_ok, primary_err = _ping_engine(PRIMARY_ENGINE)
    fallback_ok, fallback_err = _ping_engine(FALLBACK_ENGINE)

    return {
        "mode": "dual" if IS_DUAL_DB_MODE else "single",
        "active_database": "fallback" if USING_FALLBACK_DB else "primary",
        "active_database_url": _safe_db_url(ACTIVE_DATABASE_URL),
        "using_fallback_db": USING_FALLBACK_DB,
        "primary": {
            "reachable": primary_ok,
            "database_url": _safe_db_url(PRIMARY_DATABASE_URL),
            "error": None if primary_ok else primary_err,
        },
        "fallback": {
            "reachable": fallback_ok,
            "database_url": _safe_db_url(FALLBACK_SQLITE_URL),
            "error": None if fallback_ok else fallback_err,
        },
    }


def get_db():
    _ensure_primary_alive()
    _ensure_schema_ready()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import logging
import threading
import time
from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, Uuid, event

from database import (
    IS_DUAL_DB_MODE,
    get_fallback_session_factory,
    get_primary_session_factory,
    get_database_health_snapshot,
)
from src.api.models import CV, JobOffer, MatchingResult, OutboxEvent, ScreeningSession, User

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = {
    "User": User,
    "JobOffer": JobOffer,
    "CV": CV,
    "ScreeningSession": ScreeningSession,
    "MatchingResult": MatchingResult,
}

_hooks_registered = False
_worker_started = False
_stop_event = threading.Event()
_worker_lock = threading.Lock()
_sync_thread = None

_sync_state = {
    "enabled": IS_DUAL_DB_MODE,
    "running": False,
    "last_run_at": None,
    "last_success_at": None,
    "last_error": None,
    "processed_events_total": 0,
    "failed_events_total": 0,
    "last_cycle": {
        "primary_to_fallback": {"processed": 0, "failed": 0, "pending_after": 0},
        "fallback_to_primary": {"processed": 0, "failed": 0, "pending_after": 0},
    },
}


def _serialize_value(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _serialize_instance(obj) -> dict:
    payload = {}
    for column in obj.__table__.columns:
        payload[column.name] = _serialize_value(getattr(obj, column.name))
    return payload


def _record_id(obj) -> str:
    pk_name = obj.__mapper__.primary_key[0].name
    return str(getattr(obj, pk_name))


def _is_supported_model(obj) -> bool:
    return obj.__class__.__name__ in SUPPORTED_MODELS


def register_outbox_hooks(session_factory):
    global _hooks_registered
    if _hooks_registered:
        return

    @event.listens_for(session_factory, "after_flush")
    def _capture_outbox_events(session, _flush_context):
        if session.info.get("skip_outbox"):
            return

        seen = set()

        for obj in session.new:
            if isinstance(obj, OutboxEvent) or not _is_supported_model(obj):
                continue
            key = ("upsert", obj.__class__.__name__, _record_id(obj))
            if key in seen:
                continue
            seen.add(key)
            session.add(
                OutboxEvent(
                    event_type="upsert",
                    model_name=obj.__class__.__name__,
                    record_id=_record_id(obj),
                    payload=_serialize_instance(obj),
                )
            )

        for obj in session.dirty:
            if isinstance(obj, OutboxEvent) or not _is_supported_model(obj):
                continue
            if not session.is_modified(obj, include_collections=False):
                continue
            key = ("upsert", obj.__class__.__name__, _record_id(obj))
            if key in seen:
                continue
            seen.add(key)
            session.add(
                OutboxEvent(
                    event_type="upsert",
                    model_name=obj.__class__.__name__,
                    record_id=_record_id(obj),
                    payload=_serialize_instance(obj),
                )
            )

        for obj in session.deleted:
            if isinstance(obj, OutboxEvent) or not _is_supported_model(obj):
                continue
            key = ("delete", obj.__class__.__name__, _record_id(obj))
            if key in seen:
                continue
            seen.add(key)
            session.add(
                OutboxEvent(
                    event_type="delete",
                    model_name=obj.__class__.__name__,
                    record_id=_record_id(obj),
                    payload=None,
                )
            )

    _hooks_registered = True


def _parse_datetime(value):
    if not isinstance(value, str):
        return value
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return value


def _coerce_for_model(model_cls, payload: dict) -> dict:
    if not payload:
        return {}

    converted = {}
    for column in model_cls.__table__.columns:
        if column.name not in payload:
            continue
        value = payload[column.name]
        if value is None:
            converted[column.name] = None
            continue

        if isinstance(column.type, Uuid) and isinstance(value, str):
            try:
                converted[column.name] = UUID(value)
                continue
            except ValueError:
                converted[column.name] = value
                continue

        if isinstance(column.type, DateTime):
            converted[column.name] = _parse_datetime(value)
            continue

        converted[column.name] = value

    return converted


def _convert_record_id(model_cls, record_id: str):
    pk_column = model_cls.__mapper__.primary_key[0]
    if isinstance(pk_column.type, Uuid):
        try:
            return UUID(record_id)
        except ValueError:
            return record_id
    return record_id


def _apply_event(target_session, outbox_event: OutboxEvent):
    model_cls = SUPPORTED_MODELS.get(outbox_event.model_name)
    if not model_cls:
        raise RuntimeError(f"Unsupported model in outbox: {outbox_event.model_name}")

    pk_value = _convert_record_id(model_cls, outbox_event.record_id)
    existing = target_session.get(model_cls, pk_value)

    if outbox_event.event_type == "delete":
        if existing is not None:
            target_session.delete(existing)
        return

    if outbox_event.event_type != "upsert":
        raise RuntimeError(f"Unsupported event type: {outbox_event.event_type}")

    payload = _coerce_for_model(model_cls, outbox_event.payload or {})
    if existing is None:
        target_session.add(model_cls(**payload))
    else:
        for key, value in payload.items():
            setattr(existing, key, value)


def _count_pending(source_session) -> int:
    return (
        source_session.query(OutboxEvent)
        .filter(OutboxEvent.processed_at.is_(None))
        .count()
    )


def _sync_direction(source_factory, target_factory, batch_size: int = 100) -> dict:
    processed = 0
    failed = 0

    with source_factory() as source_session, target_factory() as target_session:
        source_session.info["skip_outbox"] = True
        target_session.info["skip_outbox"] = True

        events = (
            source_session.query(OutboxEvent)
            .filter(OutboxEvent.processed_at.is_(None))
            .order_by(OutboxEvent.id.asc())
            .limit(batch_size)
            .all()
        )

        for evt in events:
            try:
                _apply_event(target_session, evt)
                target_session.commit()

                evt.processed_at = datetime.now(timezone.utc)
                evt.last_error = None
                source_session.commit()
                processed += 1
            except Exception as sync_err:
                target_session.rollback()
                failed += 1

                evt.attempts = int(evt.attempts or 0) + 1
                evt.last_error = str(sync_err)[:1000]
                source_session.commit()

    with source_factory() as source_session:
        source_session.info["skip_outbox"] = True
        pending_after = _count_pending(source_session)

    return {"processed": processed, "failed": failed, "pending_after": pending_after}


def _run_sync_loop(interval_seconds: int):
    primary_factory = get_primary_session_factory()
    fallback_factory = get_fallback_session_factory()

    with _worker_lock:
        _sync_state["running"] = True

    try:
        while not _stop_event.is_set():
            _sync_state["last_run_at"] = datetime.now(timezone.utc).isoformat()

            health = get_database_health_snapshot()
            primary_ok = bool(health["primary"]["reachable"])
            fallback_ok = bool(health["fallback"]["reachable"])

            if primary_ok and fallback_ok:
                try:
                    p_to_f = _sync_direction(primary_factory, fallback_factory)
                    f_to_p = _sync_direction(fallback_factory, primary_factory)

                    _sync_state["last_cycle"]["primary_to_fallback"] = p_to_f
                    _sync_state["last_cycle"]["fallback_to_primary"] = f_to_p
                    _sync_state["processed_events_total"] += p_to_f["processed"] + f_to_p["processed"]
                    _sync_state["failed_events_total"] += p_to_f["failed"] + f_to_p["failed"]
                    _sync_state["last_success_at"] = datetime.now(timezone.utc).isoformat()
                    _sync_state["last_error"] = None
                except Exception as cycle_err:
                    _sync_state["last_error"] = str(cycle_err)
                    logger.exception("DB sync cycle failed")
            else:
                reason = []
                if not primary_ok:
                    reason.append("primary_unreachable")
                if not fallback_ok:
                    reason.append("fallback_unreachable")
                _sync_state["last_error"] = ",".join(reason)

            _stop_event.wait(interval_seconds)
    finally:
        with _worker_lock:
            _sync_state["running"] = False


def start_db_sync_worker(interval_seconds: int = 10):
    global _worker_started, _sync_thread
    if not IS_DUAL_DB_MODE:
        _sync_state["enabled"] = False
        _sync_state["running"] = False
        return

    if _worker_started:
        return

    _stop_event.clear()
    _sync_thread = threading.Thread(
        target=_run_sync_loop,
        args=(interval_seconds,),
        name="db-sync-worker",
        daemon=True,
    )
    _sync_thread.start()
    _worker_started = True
    _sync_state["enabled"] = True


def get_sync_status() -> dict:
    return deepcopy(_sync_state)

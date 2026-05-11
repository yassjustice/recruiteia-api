from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import engine, get_database_health_snapshot, SessionLocal
from db_sync import get_sync_status, register_outbox_hooks, start_db_sync_worker
import src.api.models as models

# Create all tables on startup — non-fatal if DB unreachable (e.g. cold start race)
try:
    models.Base.metadata.create_all(bind=engine)
except Exception as _db_err:
    import logging
    logging.warning(f"DB create_all skipped on startup: {_db_err}")

app = FastAPI(
    title="RecruteIA API",
    description="AI-powered CV screening backend — FQIA 2026",
    version="1.0.0",
)

# CORS — allow all origins for dev/demo (Otman's WordPress frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from src.api.routers import auth, offers, cvs, sessions, results

app.include_router(auth.router, prefix="/api")
app.include_router(offers.router, prefix="/api")
app.include_router(cvs.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(results.router, prefix="/api")


@app.on_event("startup")
def _startup_sync_services():
    register_outbox_hooks(SessionLocal)
    start_db_sync_worker()


@app.get("/api/health")
def health():
    return {"success": True, "data": {"status": "ok", "version": "1.0.0"}}


@app.get("/api/health/db")
def health_db():
    return {
        "success": True,
        "data": {
            "database": get_database_health_snapshot(),
            "sync": get_sync_status(),
        },
    }


@app.get("/")
def root():
    return {"message": "RecruteIA API — see /docs for Swagger UI"}

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from config import settings
from database import engine, get_database_health_snapshot, SessionLocal, get_db
from db_sync import get_sync_status, register_outbox_hooks, start_db_sync_worker
import src.api.models as models
from src.api.models import User, JobOffer, CV, ScreeningSession
from src.api.dependencies import get_current_user

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

# CORS — allow all origins for dev/demo (Next.js frontend on Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error Handlers ────────────────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": f"HTTP_{exc.status_code}", "message": exc.detail}},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    messages = []
    for e in errors:
        loc = ".".join(str(x) for x in e["loc"])
        messages.append(loc + ": " + e["msg"])
    message = "; ".join(messages)
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": {"code": "VALIDATION_ERROR", "message": message, "details": errors}},
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


@app.get("/api/stats/summary")
def stats_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_offers = db.query(JobOffer).filter(JobOffer.user_id == user.id).count()
    total_cvs = db.query(CV).filter(CV.user_id == user.id).count()
    total_sessions = db.query(ScreeningSession).filter(ScreeningSession.user_id == user.id).count()
    active_sessions = db.query(ScreeningSession).filter(
        ScreeningSession.user_id == user.id,
        ScreeningSession.status.in_(["pending", "running"]),
    ).count()
    return {
        "success": True,
        "data": {
            "total_offers": total_offers,
            "total_sessions": total_sessions,
            "total_cvs": total_cvs,
            "active_sessions": active_sessions,
        },
    }


@app.get("/")
def root():
    return {"message": "RecruteIA API — see /docs for Swagger UI"}
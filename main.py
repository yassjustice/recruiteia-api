from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import engine
import src.api.models as models

# Create all tables on startup
models.Base.metadata.create_all(bind=engine)

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


@app.get("/api/health")
def health():
    return {"success": True, "data": {"status": "ok", "version": "1.0.0"}}


@app.get("/")
def root():
    return {"message": "RecruteIA API — see /docs for Swagger UI"}

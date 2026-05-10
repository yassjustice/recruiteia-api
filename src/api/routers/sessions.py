from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
import sys

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parents[3]))
from database import SessionLocal, get_db
from src.api.dependencies import get_current_user
from src.api.models import CV, JobOffer, MatchingResult, ScreeningSession, User
from src.api.schemas import SessionCreate
from src.services.scorer import rank_candidates

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _weights_for_legacy(weights: dict) -> dict:
    return {
        "weights_skills": weights.get("skills_match", 0.30),
        "weights_experience": weights.get("experience_relevance", 0.22),
        "weights_education": weights.get("education", 0.08),
        "weights_language": weights.get("language_match", 0.10),
        "weights_location": weights.get("location", 0.05),
    }


def _serialize_session(session: ScreeningSession, session_name: str | None = None) -> dict:
    weights = session.weights or {}
    legacy = _weights_for_legacy(weights)
    return {
        "id": str(session.id),
        "name": session_name or f"Session {str(session.id)[:8]}",
        "status": session.status,
        "user_id": str(session.user_id),
        "offer_id": str(session.offer_id),
        "job_offer_id": str(session.offer_id),  # backward compatibility
        "total_cvs": session.total_cvs,
        "processed_cvs": session.processed_cvs,
        "weights": weights,
        "created_at": session.created_at,
        "completed_at": session.completed_at,
        "scored_at": session.completed_at,  # backward compatibility
        **legacy,
    }


def _run_scoring(session_id: str):
    with SessionLocal() as db:
        session_uuid = UUID(session_id)
        session = db.query(ScreeningSession).filter(ScreeningSession.id == session_uuid).first()
        if not session:
            return

        session.status = "processing"
        db.commit()

        try:
            job = db.query(JobOffer).filter(JobOffer.id == session.offer_id).first()
            if not job:
                raise RuntimeError("Job offer not found for session")

            cv_ids = [
                row.cv_id
                for row in db.query(MatchingResult.cv_id)
                .filter(MatchingResult.session_id == session.id)
                .all()
            ]
            cvs = db.query(CV).filter(CV.id.in_(cv_ids)).all() if cv_ids else []

            job_dict = {
                "required_skills": job.required_skills or [],
                "critical_skills": job.critical_skills or [],
                "required_soft_skills": job.required_soft_skills or [],
                "required_languages": job.required_languages or [],
                "experience_required_years": job.experience_required_years or 0,
                "min_education": job.min_education or "",
                "location": job.location or "",
                "remote_ok": bool(job.remote_ok),
                "description_summary": job.description_summary or "",
                "raw_text": job.raw_text or "",
                "job_type": job.job_type or "",
            }

            candidates = [
                {
                    "cv_id": cv.id,
                    "name": cv.candidate_name,
                    "email": cv.candidate_email,
                    "skills": cv.skills or [],
                    "soft_skills": cv.soft_skills or [],
                    "experience_years": cv.experience_years or 0,
                    "education_level": cv.education_level or "",
                    "languages_spoken": cv.languages_spoken or [],
                    "location": cv.candidate_location or "",
                    "language": cv.language or "fr",
                    "profile": cv.profile or "",
                    "experience": cv.experience or "",
                    "projects": cv.projects or "",
                    "skills_in_experience": cv.skills_in_experience or [],
                    "quantified_achievements": cv.quantified_achievements or {},
                    "action_verb_scores": cv.action_verb_scores or {},
                    "buzzword_analysis": cv.buzzword_analysis or {},
                    "confidence_score": cv.confidence_score or {},
                    "flags": cv.flags or [],
                }
                for cv in cvs
            ]

            ranked = rank_candidates(candidates, job_dict, session.weights or {})

            for row in ranked:
                mr = (
                    db.query(MatchingResult)
                    .filter(
                        MatchingResult.session_id == session.id,
                        MatchingResult.cv_id == row["cv_id"],
                    )
                    .first()
                )
                if not mr:
                    continue
                mr.rank = row["rank"]
                mr.total_score = row["total_score"]
                mr.recommendation = row["recommendation"]
                mr.skills_score = row["skills_score"]
                mr.experience_score = row["experience_score"]
                mr.achievements_score = row["achievements_score"]
                mr.language_quality_score = row["language_quality_score"]
                mr.language_match_score = row["language_match_score"]
                mr.education_score = row["education_score"]
                mr.location_score = row["location_score"]
                mr.experience_relevance_reason = row.get("experience_relevance_reason")
                mr.matched_skills = row.get("matched_skills", [])
                mr.missing_skills = row.get("missing_skills", [])
                mr.critical_missing = row.get("critical_missing", [])
                mr.language_details = row.get("language_details", [])
                mr.flags = row.get("flags", [])
                mr.confidence_multiplier_applied = row.get("confidence_multiplier_applied", False)
                mr.student_profile_detected = row.get("student_profile_detected", False)
                mr.missing_critical_count = row.get("missing_critical_count", len(row.get("critical_missing", [])))
                mr.semantic_score = row.get("semantic_score")
                mr.status = "scored"

            session.status = "completed"
            session.processed_cvs = len(ranked)
            session.completed_at = datetime.now(timezone.utc)
            db.commit()

        except Exception:
            session.status = "failed"
            db.commit()
            raise


@router.post("")
def create_session(
    body: SessionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    offer = db.query(JobOffer).filter(JobOffer.id == body.offer_id, JobOffer.user_id == user.id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Job offer not found")

    cvs = db.query(CV).filter(CV.id.in_(body.cv_ids), CV.user_id == user.id).all()
    if len(cvs) != len(body.cv_ids):
        raise HTTPException(status_code=400, detail="Some CV IDs not found")

    session = ScreeningSession(
        user_id=user.id,
        offer_id=body.offer_id,
        weights=body.weights.as_dict(),
        total_cvs=len(cvs),
    )
    db.add(session)
    db.flush()

    for cv in cvs:
        db.add(
            MatchingResult(
                session_id=session.id,
                cv_id=cv.id,
                offer_id=session.offer_id,
                total_score=0.0,
                rank=0,
                recommendation="Not Recommended",
            )
        )

    db.commit()
    db.refresh(session)
    return {"success": True, "data": _serialize_session(session, session_name=body.name)}


@router.post("/{session_id}/score")
def score_session(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = (
        db.query(ScreeningSession)
        .filter(ScreeningSession.id == session_id, ScreeningSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "processing":
        raise HTTPException(status_code=409, detail="Scoring already in progress")

    session.status = "processing"
    db.commit()
    background_tasks.add_task(_run_scoring, str(session_id))
    return {"success": True, "data": {"message": "Scoring started", "session_id": str(session_id)}}


@router.get("")
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sessions = (
        db.query(ScreeningSession)
        .filter(ScreeningSession.user_id == user.id)
        .order_by(ScreeningSession.created_at.desc())
        .all()
    )
    return {"success": True, "data": [_serialize_session(s) for s in sessions]}


@router.get("/{session_id}")
def get_session(session_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = (
        db.query(ScreeningSession)
        .filter(ScreeningSession.id == session_id, ScreeningSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "data": _serialize_session(session)}

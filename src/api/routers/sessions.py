from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))
from database import get_db
from src.api.models import User, ScreeningSession, CV, JobOffer, MatchingResult
from src.api.schemas import SessionCreate, SessionOut
from src.api.dependencies import get_current_user
from src.services.scorer import rank_candidates

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _run_scoring(session_id: int, db: Session):
    session = db.query(ScreeningSession).filter(ScreeningSession.id == session_id).first()
    if not session:
        return
    session.status = "scoring"
    db.commit()

    try:
        job = db.query(JobOffer).filter(JobOffer.id == session.job_offer_id).first()
        cvs = (
            db.query(CV)
            .join(MatchingResult, MatchingResult.cv_id == CV.id)
            .filter(MatchingResult.session_id == session_id)
            .all()
        )

        job_dict = {
            "required_skills": job.required_skills or [],
            "critical_skills": job.critical_skills or [],
            "soft_skills": job.soft_skills or [],
            "experience_required_years": job.experience_required_years or 0,
            "education_required": job.education_required or "",
            "languages_required": job.languages_required or [],
            "location": job.location or "",
        }
        weights = {
            "skills": session.weights_skills,
            "experience": session.weights_experience,
            "education": session.weights_education,
            "language": session.weights_language,
            "location": session.weights_location,
        }
        candidates = [
            {
                "cv_id": cv.id,
                "name": cv.candidate_name,
                "skills": cv.skills or [],
                "soft_skills": cv.soft_skills or [],
                "experience_years": cv.experience_years or 0,
                "education_level": cv.education_level or "",
                "languages_spoken": cv.languages_spoken or [],
                "location": cv.candidate_location or "",
            }
            for cv in cvs
        ]

        ranked = rank_candidates(candidates, job_dict, weights)

        # Update MatchingResult rows
        for row in ranked:
            mr = (
                db.query(MatchingResult)
                .filter(MatchingResult.session_id == session_id, MatchingResult.cv_id == row["cv_id"])
                .first()
            )
            if mr:
                mr.rank = row["rank"]
                mr.final_score = row["final_score"]
                mr.skills_score = row["skills_score"]
                mr.experience_score = row["experience_score"]
                mr.education_score = row["education_score"]
                mr.language_score = row["language_score"]
                mr.location_score = row["location_score"]
                mr.matched_skills = row.get("matched_skills", [])
                mr.missing_critical = row.get("missing_critical", [])

        session.status = "completed"
        session.processed_cvs = len(ranked)
        session.scored_at = datetime.utcnow()
        db.commit()

    except Exception as e:
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
    # Validate weights sum ≈ 1.0
    w = body.weights
    total = round(w.skills + w.experience + w.education + w.language + w.location, 4)
    if not (0.99 <= total <= 1.01):
        raise HTTPException(status_code=400, detail=f"Weights must sum to 1.0 (got {total})")

    # Validate offer exists
    offer = db.query(JobOffer).filter(JobOffer.id == body.job_offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Job offer not found")

    # Validate CVs exist
    cvs = db.query(CV).filter(CV.id.in_(body.cv_ids)).all()
    if len(cvs) != len(body.cv_ids):
        raise HTTPException(status_code=400, detail="Some CV IDs not found")

    session = ScreeningSession(
        name=body.name,
        job_offer_id=body.job_offer_id,
        owner_id=user.id,
        total_cvs=len(cvs),
        weights_skills=w.skills,
        weights_experience=w.experience,
        weights_education=w.education,
        weights_language=w.language,
        weights_location=w.location,
    )
    db.add(session)
    db.flush()

    # Create placeholder MatchingResult rows
    for cv in cvs:
        db.add(MatchingResult(session_id=session.id, cv_id=cv.id))
    db.commit()
    db.refresh(session)

    return {"success": True, "data": SessionOut.model_validate(session)}


@router.post("/{session_id}/score")
def score_session(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(ScreeningSession).filter(
        ScreeningSession.id == session_id, ScreeningSession.owner_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "scoring":
        raise HTTPException(status_code=409, detail="Scoring already in progress")

    background_tasks.add_task(_run_scoring, session_id, db)
    return {"success": True, "data": {"message": "Scoring started", "session_id": session_id}}


@router.get("")
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sessions = db.query(ScreeningSession).filter(ScreeningSession.owner_id == user.id).order_by(ScreeningSession.created_at.desc()).all()
    return {"success": True, "data": [SessionOut.model_validate(s) for s in sessions]}


@router.get("/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(ScreeningSession).filter(
        ScreeningSession.id == session_id, ScreeningSession.owner_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "data": SessionOut.model_validate(session)}

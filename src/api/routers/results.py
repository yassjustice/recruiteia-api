import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))
from database import get_db
from src.api.models import User, ScreeningSession, MatchingResult, CV
from src.api.schemas import RankingRow
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/sessions", tags=["results"])


@router.get("/{session_id}/results")
def get_results(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(ScreeningSession).filter(
        ScreeningSession.id == session_id, ScreeningSession.owner_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in ("completed",):
        return {"success": True, "data": {"status": session.status, "results": []}}

    results = (
        db.query(MatchingResult, CV)
        .join(CV, MatchingResult.cv_id == CV.id)
        .filter(MatchingResult.session_id == session_id)
        .order_by(MatchingResult.rank)
        .all()
    )

    rows = []
    for mr, cv in results:
        rows.append({
            "rank": mr.rank,
            "cv_id": cv.id,
            "candidate_name": cv.candidate_name,
            "candidate_email": cv.candidate_email,
            "final_score": round(mr.final_score, 4),
            "final_score_pct": round(mr.final_score * 100, 1),
            "skills_score": round(mr.skills_score, 4),
            "experience_score": round(mr.experience_score, 4),
            "education_score": round(mr.education_score, 4),
            "language_score": round(mr.language_score, 4),
            "location_score": round(mr.location_score, 4),
            "matched_skills": mr.matched_skills or [],
            "missing_critical": mr.missing_critical or [],
            "status": mr.status,
            "threshold": "green" if mr.final_score >= 0.80 else ("orange" if mr.final_score >= 0.50 else "red"),
        })
    return {"success": True, "data": rows}


@router.get("/{session_id}/export")
def export_csv(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(ScreeningSession).filter(
        ScreeningSession.id == session_id, ScreeningSession.owner_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    results = (
        db.query(MatchingResult, CV)
        .join(CV, MatchingResult.cv_id == CV.id)
        .filter(MatchingResult.session_id == session_id)
        .order_by(MatchingResult.rank)
        .all()
    )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "rank", "name", "email", "phone", "location",
        "final_score_pct", "skills_score", "experience_score",
        "education_score", "language_score", "location_score",
        "matched_skills", "missing_critical", "status"
    ])
    writer.writeheader()
    for mr, cv in results:
        writer.writerow({
            "rank": mr.rank,
            "name": cv.candidate_name,
            "email": cv.candidate_email,
            "phone": cv.candidate_phone,
            "location": cv.candidate_location,
            "final_score_pct": round(mr.final_score * 100, 1),
            "skills_score": round(mr.skills_score * 100, 1),
            "experience_score": round(mr.experience_score * 100, 1),
            "education_score": round(mr.education_score * 100, 1),
            "language_score": round(mr.language_score * 100, 1),
            "location_score": round(mr.location_score * 100, 1),
            "matched_skills": "; ".join(mr.matched_skills or []),
            "missing_critical": "; ".join(mr.missing_critical or []),
            "status": mr.status,
        })
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=session_{session_id}_results.csv"},
    )

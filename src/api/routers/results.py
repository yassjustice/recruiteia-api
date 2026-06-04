import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))
from database import get_db
from src.api.models import User, ScreeningSession, MatchingResult, CV
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/sessions", tags=["results"])


def _derive_strengths(mr: MatchingResult) -> list[str]:
    """REQ-M3-8: derive an explicit list of candidate strengths from scored dimensions."""
    strengths = []
    matched = mr.matched_skills or []
    critical_missing = mr.critical_missing or []
    exp_score = float(mr.experience_score or 0.0)
    skills_score = float(mr.skills_score or 0.0)
    achieve_score = float(mr.achievements_score or 0.0)
    lang_match = float(mr.language_match_score or 0.0)
    edu_score = float(mr.education_score or 0.0)

    if matched and not critical_missing:
        strengths.append(f"Toutes les compétences critiques présentes ({len(matched)} compétences matchées)")
    elif matched:
        strengths.append(f"{len(matched)} compétence(s) requise(s) présente(s)")

    if exp_score >= 0.80:
        strengths.append("Expérience très pertinente par rapport au poste")
    elif exp_score >= 0.60:
        strengths.append("Expérience pertinente pour le poste")

    if achieve_score >= 0.70:
        strengths.append("Réalisations chiffrées significatives (impact démontré)")
    elif achieve_score >= 0.35:
        strengths.append("Réalisations chiffrées présentes")

    if lang_match >= 0.90:
        strengths.append("Maîtrise complète des langues requises")
    elif lang_match >= 0.60:
        strengths.append("Bonne correspondance linguistique")

    if edu_score >= 1.0:
        strengths.append("Niveau de formation supérieur ou égal au requis")

    if bool(mr.student_profile_detected):
        strengths.append("Profil étudiant avec projets pertinents")

    return strengths


def _serialize_result(mr: MatchingResult, cv: CV) -> dict:
    total_score = float(mr.total_score or 0.0)
    language_score_legacy = (
        (float(mr.language_quality_score or 0.0) + float(mr.language_match_score or 0.0)) / 2.0
    )
    return {
        "rank": mr.rank,
        "cv_id": str(cv.id),
        "candidate_name": cv.candidate_name or "",
        "candidate_email": cv.candidate_email or "",
        "candidate_phone": cv.candidate_phone or "",
        "candidate_location": cv.candidate_location or "",
        "total_score": round(total_score, 4),
        "final_score": round(total_score, 4),  # backward compatibility
        "final_score_pct": round(total_score * 100, 1),
        "recommendation": mr.recommendation,
        "skills_score": round(float(mr.skills_score or 0.0), 4),
        "experience_score": round(float(mr.experience_score or 0.0), 4),
        "achievements_score": round(float(mr.achievements_score or 0.0), 4),
        "language_quality_score": round(float(mr.language_quality_score or 0.0), 4),
        "language_match_score": round(float(mr.language_match_score or 0.0), 4),
        "language_score": round(language_score_legacy, 4),  # backward compatibility
        "education_score": round(float(mr.education_score or 0.0), 4),
        "location_score": round(float(mr.location_score or 0.0), 4),
        "experience_relevance_reason": mr.experience_relevance_reason,
        "matched_skills": mr.matched_skills or [],
        "missing_skills": mr.missing_skills or [],
        "critical_missing": mr.critical_missing or [],
        "missing_critical": mr.critical_missing or [],  # backward compatibility
        "language_details": mr.language_details or [],
        "flags": mr.flags or [],
        "strengths": _derive_strengths(mr),  # REQ-M3-8: explicit candidate strengths
        "missing_critical_count": mr.missing_critical_count or 0,
        "confidence_multiplier_applied": bool(mr.confidence_multiplier_applied),
        "student_profile_detected": bool(mr.student_profile_detected),
        "semantic_score": mr.semantic_score,
        "status": mr.status,
        "threshold": "green" if total_score >= 0.80 else ("orange" if total_score >= 0.50 else "red"),
    }


@router.get("/{session_id}/results")
def get_results(session_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(ScreeningSession).filter(
        ScreeningSession.id == session_id, ScreeningSession.user_id == user.id
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
        rows.append(_serialize_result(mr, cv))
    return {"success": True, "data": rows}


@router.get("/{session_id}/export")
def export_csv(session_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(ScreeningSession).filter(
        ScreeningSession.id == session_id, ScreeningSession.user_id == user.id
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
        "rank",
        "name",
        "email",
        "phone",
        "location",
        "total_score_pct",
        "recommendation",
        "skills_score",
        "experience_score",
        "achievements_score",
        "language_quality_score",
        "language_match_score",
        "education_score",
        "location_score",
        "matched_skills",
        "missing_skills",
        "critical_missing",
        "status",
    ])
    writer.writeheader()
    for mr, cv in results:
        row = _serialize_result(mr, cv)
        writer.writerow({
            "rank": row["rank"],
            "name": row["candidate_name"],
            "email": row["candidate_email"],
            "phone": row["candidate_phone"],
            "location": row["candidate_location"],
            "total_score_pct": row["final_score_pct"],
            "recommendation": row["recommendation"],
            "skills_score": round(row["skills_score"] * 100, 1),
            "experience_score": round(row["experience_score"] * 100, 1),
            "achievements_score": round(row["achievements_score"] * 100, 1),
            "language_quality_score": round(row["language_quality_score"] * 100, 1),
            "language_match_score": round(row["language_match_score"] * 100, 1),
            "education_score": round(row["education_score"] * 100, 1),
            "location_score": round(row["location_score"] * 100, 1),
            "matched_skills": "; ".join(row["matched_skills"]),
            "missing_skills": "; ".join(row["missing_skills"]),
            "critical_missing": "; ".join(row["critical_missing"]),
            "status": row["status"],
        })
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=session_{session_id}_results.csv"},
    )

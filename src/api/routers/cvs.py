import hashlib
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from uuid import UUID
import sys
sys.path.insert(0, str(Path(__file__).parents[3]))
from database import get_db
from src.api.models import User, CV
from src.api.dependencies import get_current_user
from src.services.extractor import extract_resume
from config import settings

router = APIRouter(prefix="/cvs", tags=["cvs"])

MAX_SIZE = 5 * 1024 * 1024  # 5MB


def _to_text(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    return ""


def _normalize_flags(flags):
    normalized = []
    for entry in flags or []:
        if isinstance(entry, dict):
            normalized.append(entry)
        elif isinstance(entry, str):
            normalized.append({"code": entry, "severity": "info", "message": entry.replace("_", " ")})
    return normalized


def _confidence_payload(raw_confidence, normalized_flags):
    if isinstance(raw_confidence, dict):
        return raw_confidence
    try:
        confidence = float(raw_confidence or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "confidence": confidence,
        "missing_fields": [],
        "has_critical_flags": any(flag.get("severity") == "critical" for flag in normalized_flags),
    }


def _to_examples(value):
    if isinstance(value, dict):
        examples = value.get("examples", [])
        return examples if isinstance(examples, list) else []
    if isinstance(value, list):
        return value
    return []


def _serialize_cv(cv: CV) -> dict:
    confidence_obj = cv.confidence_score or {}
    confidence_value = confidence_obj.get("confidence", 0) if isinstance(confidence_obj, dict) else 0
    return {
        "id": str(cv.id),
        "user_id": str(cv.user_id),
        "filename": cv.filename,
        "original_filename": cv.filename,  # backward compatibility
        "file_path": cv.file_path,
        "file_size_bytes": cv.file_size_bytes,
        "file_size": cv.file_size_bytes,  # backward compatibility
        "language": cv.language or "",
        "content_hash": cv.content_hash,
        "is_duplicate": cv.is_duplicate,
        "duplicate_of": str(cv.duplicate_of) if cv.duplicate_of else None,
        "extraction_status": cv.extraction_status,
        "extraction_error": None if cv.extraction_status == "done" else "extraction_failed",
        "candidate_name": cv.candidate_name or "",
        "candidate_email": cv.candidate_email or "",
        "candidate_phone": cv.candidate_phone or "",
        "candidate_location": cv.candidate_location or "",
        "candidate_linkedin": cv.candidate_linkedin or "",
        "candidate_github": cv.candidate_github or "",
        "raw_text": cv.raw_text or "",
        "profile": cv.profile or "",
        "experience": cv.experience or "",
        "education": cv.education or "",
        "projects": cv.projects or "",
        "skills": cv.skills or [],
        "skills_in_experience": cv.skills_in_experience or [],
        "orphan_skills": cv.orphan_skills or [],
        "soft_skills": cv.soft_skills or [],
        "languages_spoken": cv.languages_spoken or [],
        "experience_years": cv.experience_years or 0,
        "education_level": cv.education_level or "",
        "industry": cv.industry or "",
        "quantified_achievements": cv.quantified_achievements or {},
        "action_verb_scores": cv.action_verb_scores or {},
        "buzzword_analysis": cv.buzzword_analysis or {},
        "confidence_score": cv.confidence_score or {},
        "confidence_score_value": confidence_value,  # backward compatibility
        "flags": cv.flags or [],
        "created_at": cv.created_at,
        "uploaded_at": cv.created_at,  # backward compatibility
    }


@router.post("")
async def upload_cv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 5MB limit")

    # Duplicate detection via MD5
    content_hash = hashlib.md5(content).hexdigest()
    existing = db.query(CV).filter(CV.content_hash == content_hash).first()
    duplicate_of_id = existing.id if existing else None

    # Save file
    upload_path = Path(settings.upload_dir) / f"{content_hash}.pdf"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    with open(upload_path, "wb") as f:
        f.write(content)

    # Extract resume data
    try:
        extracted = extract_resume(str(upload_path))
        error = extracted.get("error")
    except Exception as e:
        extracted = {}
        error = str(e)

    def _list(v):
        return v if isinstance(v, list) else []

    skills = _list(extracted.get("skills"))
    skills_in_experience = _list(extracted.get("skills_in_experience"))
    skills_in_exp_set = {str(s).strip().lower() for s in skills_in_experience}
    orphan_skills = [s for s in skills if str(s).strip().lower() not in skills_in_exp_set]
    normalized_flags = _normalize_flags(_list(extracted.get("flags")))
    confidence_payload = _confidence_payload(extracted.get("confidence_score", 0), normalized_flags)
    achievements_examples = _to_examples(extracted.get("quantified_achievements"))
    quantified_achievements = {
        "count": len(achievements_examples),
        "has_achievements": len(achievements_examples) > 0,
        "examples": achievements_examples[:10],
    }

    cv = CV(
        user_id=user.id,
        filename=file.filename,
        file_path=str(upload_path),
        file_size_bytes=len(content),
        content_hash=content_hash,
        is_duplicate=duplicate_of_id is not None,
        duplicate_of=duplicate_of_id,
        extraction_status="failed" if error else "done",
        candidate_name=extracted.get("name", ""),
        candidate_email=extracted.get("email", ""),
        candidate_phone=extracted.get("phone", ""),
        candidate_location=extracted.get("location", ""),
        candidate_linkedin=extracted.get("linkedin", ""),
        candidate_github=extracted.get("github", ""),
        language=extracted.get("language", "en"),
        raw_text=_to_text(extracted.get("raw_text")),
        profile=_to_text(extracted.get("profile")),
        experience=_to_text(extracted.get("experience")),
        education=_to_text(extracted.get("education")),
        projects=_to_text(extracted.get("projects")),
        skills=skills,
        skills_in_experience=skills_in_experience,
        orphan_skills=orphan_skills,
        soft_skills=_list(extracted.get("soft_skills")),
        languages_spoken=_list(extracted.get("languages_spoken")),
        experience_years=int(float(extracted.get("experience_years", 0) or 0)),
        education_level=extracted.get("education_level", ""),
        industry=extracted.get("industry", ""),
        confidence_score=confidence_payload,
        flags=normalized_flags,
        action_verb_scores=extracted.get("action_verb_scores") or {},
        buzzword_analysis=extracted.get("buzzword_analysis") or {},
        quantified_achievements=quantified_achievements,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return {"success": True, "data": _serialize_cv(cv)}


@router.get("")
def list_cvs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cvs = db.query(CV).filter(CV.user_id == user.id).order_by(CV.created_at.desc()).all()
    return {"success": True, "data": [_serialize_cv(c) for c in cvs]}


@router.get("/{cv_id}")
def get_cv(cv_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == user.id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    return {"success": True, "data": _serialize_cv(cv)}

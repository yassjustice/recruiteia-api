import hashlib
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import sys
sys.path.insert(0, str(Path(__file__).parents[3]))
from database import get_db
from src.api.models import User, CV
from src.api.schemas import CVOut
from src.api.dependencies import get_current_user
from src.services.extractor import extract_resume
from config import settings

router = APIRouter(prefix="/cvs", tags=["cvs"])

MAX_SIZE = 5 * 1024 * 1024  # 5MB


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

    cv = CV(
        file_path=str(upload_path),
        original_filename=file.filename,
        file_size=len(content),
        content_hash=content_hash,
        is_duplicate=duplicate_of_id is not None,
        duplicate_of=duplicate_of_id,
        extraction_error=error,
        candidate_name=extracted.get("name", ""),
        candidate_email=extracted.get("email", ""),
        candidate_phone=extracted.get("phone", ""),
        candidate_location=extracted.get("location", ""),
        candidate_linkedin=extracted.get("linkedin", ""),
        candidate_github=extracted.get("github", ""),
        language=extracted.get("language", "en"),
        profile=extracted.get("profile", ""),
        experience=_list(extracted.get("experience")),
        education=_list(extracted.get("education")),
        projects=_list(extracted.get("projects")),
        certifications=_list(extracted.get("certifications")),
        skills=_list(extracted.get("skills")),
        soft_skills=_list(extracted.get("soft_skills")),
        skills_in_experience=_list(extracted.get("skills_in_experience")),
        languages_spoken=_list(extracted.get("languages_spoken")),
        interests=_list(extracted.get("interests")),
        experience_years=float(extracted.get("experience_years", 0) or 0),
        education_level=extracted.get("education_level", ""),
        industry=extracted.get("industry", ""),
        confidence_score=float(extracted.get("confidence_score", 0) or 0),
        flags=_list(extracted.get("flags")),
        action_verb_scores=extracted.get("action_verb_scores") or {},
        buzzword_analysis=extracted.get("buzzword_analysis") or {},
        quantified_achievements=_list(extracted.get("quantified_achievements")),
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return {"success": True, "data": CVOut.model_validate(cv)}


@router.get("")
def list_cvs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cvs = db.query(CV).order_by(CV.uploaded_at.desc()).all()
    return {"success": True, "data": [CVOut.model_validate(c) for c in cvs]}


@router.get("/{cv_id}")
def get_cv(cv_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cv = db.query(CV).filter(CV.id == cv_id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    return {"success": True, "data": CVOut.model_validate(cv)}

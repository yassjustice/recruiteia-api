from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))
from database import get_db
from src.api.models import User, JobOffer
from src.api.schemas import JobOfferCreate
from src.api.dependencies import get_current_user
from src.services.jd_parser import extract_job_offer

router = APIRouter(prefix="/offers", tags=["offers"])


def _legacy_languages(required_languages: list[dict]) -> list[dict]:
    legacy = []
    for item in required_languages or []:
        if not isinstance(item, dict):
            continue
        language = str(item.get("language", "")).strip()
        if not language:
            continue
        legacy.append({"language": language, "level": item.get("min_level", "")})
    return legacy


def _serialize_offer(offer: JobOffer) -> dict:
    required_languages = offer.required_languages or []
    return {
        "id": str(offer.id),
        "user_id": str(offer.user_id),
        "job_title": offer.job_title,
        "title": offer.job_title,  # backward compatibility
        "company_name": offer.company_name,
        "industry": offer.industry,
        "job_type": offer.job_type,
        "job_function": offer.job_function,
        "seniority": offer.seniority,
        "location": offer.location,
        "remote_ok": offer.remote_ok,
        "raw_text": offer.raw_text,
        "description": offer.raw_text,  # backward compatibility
        "description_summary": offer.description_summary,
        "required_skills": offer.required_skills or [],
        "critical_skills": offer.critical_skills or [],
        "normalized_skills": offer.normalized_skills or [],
        "required_soft_skills": offer.required_soft_skills or [],
        "soft_skills": offer.required_soft_skills or [],  # backward compatibility
        "required_languages": required_languages,
        "languages_required": _legacy_languages(required_languages),  # backward compatibility
        "min_education": offer.min_education,
        "education_required": offer.min_education,  # backward compatibility
        "education_field": offer.education_field,
        "experience_required_years": offer.experience_required_years or 0,
        "status": offer.status,
        "is_active": offer.status == "active",  # backward compatibility
        "created_at": offer.created_at,
    }


@router.post("")
def create_offer(body: JobOfferCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload = {
        "user_id": user.id,
        "job_title": body.job_title,
        "company_name": body.company_name,
        "industry": body.industry or body.domain,
        "job_type": body.job_type,
        "job_function": body.job_function,
        "seniority": body.seniority,
        "location": body.location,
        "remote_ok": body.remote_ok,
        "raw_text": body.raw_text,
        "description_summary": body.description_summary,
        "required_skills": body.required_skills,
        "critical_skills": body.critical_skills,
        "normalized_skills": body.normalized_skills,
        "required_soft_skills": body.required_soft_skills,
        "required_languages": body.required_languages,
        "min_education": body.min_education,
        "education_field": body.education_field,
        "experience_required_years": body.experience_required_years,
        "status": body.status,
    }
    offer = JobOffer(**payload)
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return {"success": True, "data": _serialize_offer(offer)}


@router.post("/extract")
def extract_offer(body: dict, user: User = Depends(get_current_user)):
    """Extract structured fields from raw JD text via Groq."""
    text = body.get("text", "")
    lang = body.get("lang", "fr")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    try:
        extracted = extract_job_offer(text, lang)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    return {"success": True, "data": extracted}


@router.get("")
def list_offers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    offers = (
        db.query(JobOffer)
        .filter(JobOffer.user_id == user.id, JobOffer.status == "active")
        .order_by(JobOffer.created_at.desc())
        .all()
    )
    return {"success": True, "data": [_serialize_offer(o) for o in offers]}


@router.get("/{offer_id}")
def get_offer(offer_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    offer = db.query(JobOffer).filter(JobOffer.id == offer_id, JobOffer.user_id == user.id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return {"success": True, "data": _serialize_offer(offer)}


@router.put("/{offer_id}")
def update_offer(offer_id: UUID, body: JobOfferCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    offer = db.query(JobOffer).filter(JobOffer.id == offer_id, JobOffer.user_id == user.id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    updates = {
        "job_title": body.job_title,
        "company_name": body.company_name,
        "industry": body.industry or body.domain,
        "job_type": body.job_type,
        "job_function": body.job_function,
        "seniority": body.seniority,
        "location": body.location,
        "remote_ok": body.remote_ok,
        "raw_text": body.raw_text,
        "description_summary": body.description_summary,
        "required_skills": body.required_skills,
        "critical_skills": body.critical_skills,
        "normalized_skills": body.normalized_skills,
        "required_soft_skills": body.required_soft_skills,
        "required_languages": body.required_languages,
        "min_education": body.min_education,
        "education_field": body.education_field,
        "experience_required_years": body.experience_required_years,
        "status": body.status,
    }
    for k, v in updates.items():
        setattr(offer, k, v)
    db.commit()
    db.refresh(offer)
    return {"success": True, "data": _serialize_offer(offer)}


@router.delete("/{offer_id}")
def delete_offer(offer_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    offer = db.query(JobOffer).filter(JobOffer.id == offer_id, JobOffer.user_id == user.id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer.status = "closed"
    db.commit()
    return {"success": True, "data": {"deleted": True}}

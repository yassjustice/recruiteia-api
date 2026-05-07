from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))
from database import get_db
from src.api.models import User, JobOffer
from src.api.schemas import JobOfferCreate, JobOfferOut
from src.api.dependencies import get_current_user
from src.services.jd_parser import extract_job_offer

router = APIRouter(prefix="/offers", tags=["offers"])


@router.post("")
def create_offer(body: JobOfferCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    offer = JobOffer(**body.model_dump(), owner_id=user.id)
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return {"success": True, "data": JobOfferOut.model_validate(offer)}


@router.post("/extract")
def extract_offer(body: dict, user: User = Depends(get_current_user)):
    """Extract structured fields from raw JD text via Groq."""
    text = body.get("text", "")
    lang = body.get("lang", "fr")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    extracted = extract_job_offer(text, lang)
    return {"success": True, "data": extracted}


@router.get("")
def list_offers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    offers = db.query(JobOffer).filter(JobOffer.owner_id == user.id, JobOffer.is_active == True).all()
    return {"success": True, "data": [JobOfferOut.model_validate(o) for o in offers]}


@router.get("/{offer_id}")
def get_offer(offer_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    offer = db.query(JobOffer).filter(JobOffer.id == offer_id, JobOffer.owner_id == user.id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return {"success": True, "data": JobOfferOut.model_validate(offer)}


@router.put("/{offer_id}")
def update_offer(offer_id: int, body: JobOfferCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    offer = db.query(JobOffer).filter(JobOffer.id == offer_id, JobOffer.owner_id == user.id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    for k, v in body.model_dump().items():
        setattr(offer, k, v)
    db.commit()
    db.refresh(offer)
    return {"success": True, "data": JobOfferOut.model_validate(offer)}


@router.delete("/{offer_id}")
def delete_offer(offer_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    offer = db.query(JobOffer).filter(JobOffer.id == offer_id, JobOffer.owner_id == user.id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer.is_active = False
    db.commit()
    return {"success": True, "data": {"deleted": True}}

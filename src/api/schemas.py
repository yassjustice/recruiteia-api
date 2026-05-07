from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Any
from datetime import datetime


class APIResponse(BaseModel):
    success: bool
    data: Any = None

    @classmethod
    def ok(cls, data=None):
        return cls(success=True, data=data)

    @classmethod
    def err(cls, code: str, message: str):
        return {"success": False, "error": {"code": code, "message": message}}


# ── Auth ──────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "recruiter"

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    created_at: datetime
    model_config = {"from_attributes": True}

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Job Offers ────────────────────────────────────────────────────────
class JobOfferCreate(BaseModel):
    title: str
    description: str
    required_skills: List[str] = []
    critical_skills: List[str] = []
    soft_skills: List[str] = []
    experience_required_years: int = 0
    education_required: str = ""
    languages_required: List[dict] = []
    location: str = ""
    job_type: str = "CDI"
    domain: str = ""

class JobOfferOut(JobOfferCreate):
    id: int
    is_active: bool
    owner_id: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ── CVs ───────────────────────────────────────────────────────────────
class CVOut(BaseModel):
    id: int
    original_filename: str
    candidate_name: str
    candidate_email: str
    candidate_phone: str
    candidate_location: str
    candidate_linkedin: str
    candidate_github: str
    language: str
    skills: List[str]
    soft_skills: List[str]
    experience_years: float
    education_level: str
    confidence_score: float
    flags: List[str]
    is_duplicate: bool
    extraction_error: Optional[str]
    uploaded_at: datetime
    model_config = {"from_attributes": True}


# ── Sessions ──────────────────────────────────────────────────────────
class WeightsIn(BaseModel):
    skills: float = 0.35
    experience: float = 0.25
    education: float = 0.15
    language: float = 0.15
    location: float = 0.10

    @field_validator("skills", "experience", "education", "language", "location")
    @classmethod
    def in_range(cls, v):
        assert 0.0 <= v <= 1.0, "Weight must be between 0 and 1"
        return round(v, 4)

class SessionCreate(BaseModel):
    name: str
    job_offer_id: int
    cv_ids: List[int]
    weights: WeightsIn = WeightsIn()

class SessionOut(BaseModel):
    id: int
    name: str
    status: str
    job_offer_id: int
    total_cvs: int
    processed_cvs: int
    weights_skills: float
    weights_experience: float
    weights_education: float
    weights_language: float
    weights_location: float
    created_at: datetime
    scored_at: Optional[datetime]
    model_config = {"from_attributes": True}


# ── Results ───────────────────────────────────────────────────────────
class RankingRow(BaseModel):
    rank: int
    cv_id: int
    candidate_name: str
    candidate_email: str
    final_score: float
    skills_score: float
    experience_score: float
    education_score: float
    language_score: float
    location_score: float
    matched_skills: List[str]
    missing_critical: List[str]
    status: str
    model_config = {"from_attributes": True}

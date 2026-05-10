from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


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
    id: UUID
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
    # Canonical V2 fields
    job_title: Optional[str] = None
    company_name: str = "Unknown Company"
    industry: Optional[str] = None
    job_type: Optional[str] = None
    job_function: Optional[str] = None
    seniority: Optional[str] = None
    location: Optional[str] = None
    remote_ok: bool = False
    raw_text: Optional[str] = None
    description_summary: Optional[str] = None

    required_skills: List[str] = Field(default_factory=list)
    critical_skills: List[str] = Field(default_factory=list)
    normalized_skills: List[dict] = Field(default_factory=list)
    required_soft_skills: List[str] = Field(default_factory=list)
    required_languages: List[dict] = Field(default_factory=list)
    min_education: Optional[str] = None
    education_field: Optional[str] = None
    experience_required_years: int = 0
    status: str = "active"

    # Legacy compatibility inputs
    title: Optional[str] = None
    description: Optional[str] = None
    soft_skills: List[str] = Field(default_factory=list)
    languages_required: List[dict] = Field(default_factory=list)
    education_required: Optional[str] = None
    domain: Optional[str] = None

    @model_validator(mode="after")
    def normalize_legacy_fields(self):
        if not self.job_title and self.title:
            self.job_title = self.title
        if not self.raw_text and self.description:
            self.raw_text = self.description
        if not self.required_soft_skills and self.soft_skills:
            self.required_soft_skills = self.soft_skills
        if not self.required_languages and self.languages_required:
            converted = []
            for entry in self.languages_required:
                if not isinstance(entry, dict):
                    continue
                language = str(entry.get("language", "")).strip()
                if not language:
                    continue
                converted.append(
                    {
                        "language": language,
                        "min_level": str(entry.get("min_level") or entry.get("level") or "").strip(),
                        "weight": 0.0,
                    }
                )
            self.required_languages = converted
        if not self.min_education and self.education_required:
            self.min_education = self.education_required
        if not self.job_title:
            raise ValueError("job_title (or legacy title) is required")
        return self

class JobOfferOut(JobOfferCreate):
    id: UUID
    user_id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}


# ── CVs ───────────────────────────────────────────────────────────────
class CVOut(BaseModel):
    id: UUID
    user_id: UUID
    filename: str
    file_path: str
    file_size_bytes: Optional[int]
    extraction_status: str
    language: Optional[str]
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    candidate_phone: Optional[str]
    candidate_location: Optional[str]
    candidate_linkedin: Optional[str]
    candidate_github: Optional[str]
    skills: List[str]
    orphan_skills: List[str]
    soft_skills: List[str]
    experience_years: int
    education_level: Optional[str]
    confidence_score: dict
    flags: List[dict]
    is_duplicate: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Sessions ──────────────────────────────────────────────────────────
class WeightsIn(BaseModel):
    # Canonical V2 keys
    skills_match: float = 0.30
    experience_relevance: float = 0.22
    achievements: float = 0.15
    language_quality: float = 0.10
    language_match: float = 0.10
    education: float = 0.08
    location: float = 0.05

    # Legacy compatibility keys
    skills: Optional[float] = None
    experience: Optional[float] = None
    language: Optional[float] = None

    @model_validator(mode="after")
    def apply_legacy_aliases(self):
        if self.skills is not None:
            self.skills_match = self.skills
        if self.experience is not None:
            self.experience_relevance = self.experience
        if self.language is not None:
            self.language_match = self.language
        return self

    @field_validator(
        "skills_match",
        "experience_relevance",
        "achievements",
        "language_quality",
        "language_match",
        "education",
        "location",
    )
    @classmethod
    def in_range(cls, v):
        assert 0.0 <= v <= 1.0, "Weight must be between 0 and 1"
        return round(v, 4)

    @model_validator(mode="after")
    def validate_sum(self):
        total = (
            self.skills_match
            + self.experience_relevance
            + self.achievements
            + self.language_quality
            + self.language_match
            + self.education
            + self.location
        )
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0 (got {round(total, 4)})")
        return self

    def as_dict(self) -> dict:
        return {
            "skills_match": self.skills_match,
            "experience_relevance": self.experience_relevance,
            "achievements": self.achievements,
            "language_quality": self.language_quality,
            "language_match": self.language_match,
            "education": self.education,
            "location": self.location,
        }


class SessionCreate(BaseModel):
    name: Optional[str] = None
    offer_id: Optional[UUID] = None
    job_offer_id: Optional[UUID] = None
    cv_ids: List[UUID]
    weights: WeightsIn = WeightsIn()

    @model_validator(mode="after")
    def normalize_offer_id(self):
        if not self.offer_id and self.job_offer_id:
            self.offer_id = self.job_offer_id
        if not self.offer_id:
            raise ValueError("offer_id (or legacy job_offer_id) is required")
        return self


class SessionOut(BaseModel):
    id: UUID
    user_id: UUID
    offer_id: UUID
    name: str
    status: str
    total_cvs: int
    processed_cvs: int
    weights: dict
    created_at: datetime
    completed_at: Optional[datetime]
    model_config = {"from_attributes": True}


# ── Results ───────────────────────────────────────────────────────────
class RankingRow(BaseModel):
    rank: int
    cv_id: UUID
    candidate_name: str
    candidate_email: str
    total_score: float
    final_score: float
    skills_score: float
    experience_score: float
    achievements_score: float
    language_quality_score: float
    language_match_score: float
    education_score: float
    location_score: float
    matched_skills: List[str]
    critical_missing: List[str]
    status: str
    model_config = {"from_attributes": True}

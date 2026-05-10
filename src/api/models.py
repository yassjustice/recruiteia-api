from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import relationship

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))
from database import Base


def _default_weights():
    return {
        "skills_match": 0.30,
        "experience_relevance": 0.22,
        "achievements": 0.15,
        "language_quality": 0.10,
        "language_match": 0.10,
        "education": 0.08,
        "location": 0.05,
    }


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="recruiter")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    job_offers = relationship("JobOffer", back_populates="owner")
    cvs = relationship("CV", back_populates="owner")
    screening_sessions = relationship("ScreeningSession", back_populates="owner")


class JobOffer(Base):
    __tablename__ = "job_offers"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    job_title = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    job_type = Column(String, nullable=True)
    job_function = Column(String, nullable=True)
    seniority = Column(String, nullable=True)
    location = Column(String, nullable=True)
    remote_ok = Column(Boolean, nullable=False, default=False)

    raw_text = Column(Text, nullable=True)
    description_summary = Column(Text, nullable=True)

    required_skills = Column(JSON, nullable=False, default=list)
    critical_skills = Column(JSON, nullable=False, default=list)
    normalized_skills = Column(JSON, nullable=False, default=list)
    required_soft_skills = Column(JSON, nullable=False, default=list)
    required_languages = Column(JSON, nullable=False, default=list)

    min_education = Column(String, nullable=True)
    education_field = Column(String, nullable=True)
    experience_required_years = Column(Integer, nullable=True)

    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="job_offers")
    sessions = relationship("ScreeningSession", back_populates="job_offer")


class CV(Base):
    __tablename__ = "cvs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    language = Column(String, nullable=True)
    content_hash = Column(String, nullable=True)
    is_duplicate = Column(Boolean, nullable=False, default=False)
    duplicate_of = Column(Uuid(as_uuid=True), ForeignKey("cvs.id"), nullable=True)
    extraction_status = Column(String, nullable=False, default="pending")

    candidate_name = Column(String, nullable=True)
    candidate_email = Column(String, nullable=True)
    candidate_phone = Column(String, nullable=True)
    candidate_location = Column(String, nullable=True)
    candidate_linkedin = Column(String, nullable=True)
    candidate_github = Column(String, nullable=True)

    raw_text = Column(Text, nullable=True)
    profile = Column(Text, nullable=True)
    experience = Column(Text, nullable=True)
    education = Column(Text, nullable=True)
    projects = Column(Text, nullable=True)

    skills = Column(JSON, nullable=False, default=list)
    skills_in_experience = Column(JSON, nullable=False, default=list)
    orphan_skills = Column(JSON, nullable=False, default=list)
    soft_skills = Column(JSON, nullable=False, default=list)
    languages_spoken = Column(JSON, nullable=False, default=list)

    experience_years = Column(Integer, default=0)
    education_level = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    quantified_achievements = Column(JSON, nullable=False, default=dict)
    action_verb_scores = Column(JSON, nullable=False, default=dict)
    buzzword_analysis = Column(JSON, nullable=False, default=dict)
    confidence_score = Column(JSON, nullable=False, default=dict)
    flags = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="cvs")
    matching_results = relationship("MatchingResult", back_populates="cv")


class ScreeningSession(Base):
    __tablename__ = "screening_sessions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    offer_id = Column(Uuid(as_uuid=True), ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False)

    weights = Column(JSON, nullable=False, default=_default_weights)
    status = Column(String, nullable=False, default="pending")
    total_cvs = Column(Integer, nullable=False, default=0)
    processed_cvs = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="screening_sessions")
    job_offer = relationship("JobOffer", back_populates="sessions")
    matching_results = relationship("MatchingResult", back_populates="session")


class MatchingResult(Base):
    __tablename__ = "matching_results"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("screening_sessions.id", ondelete="CASCADE"), nullable=False)
    cv_id = Column(Uuid(as_uuid=True), ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False)
    offer_id = Column(Uuid(as_uuid=True), ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False)

    total_score = Column(Float, nullable=False, default=0.0)
    rank = Column(Integer, nullable=False, default=0)
    recommendation = Column(String, nullable=False, default="Not Recommended")

    skills_score = Column(Float, nullable=True)
    experience_score = Column(Float, nullable=True)
    achievements_score = Column(Float, nullable=True)
    language_quality_score = Column(Float, nullable=True)
    language_match_score = Column(Float, nullable=True)
    education_score = Column(Float, nullable=True)
    location_score = Column(Float, nullable=True)

    experience_relevance_reason = Column(Text, nullable=True)
    matched_skills = Column(JSON, nullable=False, default=list)
    missing_skills = Column(JSON, nullable=False, default=list)
    critical_missing = Column(JSON, nullable=False, default=list)
    language_details = Column(JSON, nullable=False, default=list)
    flags = Column(JSON, nullable=False, default=list)

    confidence_multiplier_applied = Column(Boolean, nullable=False, default=False)
    student_profile_detected = Column(Boolean, nullable=False, default=False)
    missing_critical_count = Column(Integer, nullable=False, default=0)

    semantic_score = Column(Float, nullable=True)
    recruiter_note = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="scored")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("ScreeningSession", back_populates="matching_results")
    cv = relationship("CV", back_populates="matching_results")

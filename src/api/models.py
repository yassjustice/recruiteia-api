from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, Boolean, JSON
)
from sqlalchemy.orm import relationship
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="recruiter")  # recruiter | admin
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job_offers = relationship("JobOffer", back_populates="owner")
    screening_sessions = relationship("ScreeningSession", back_populates="owner")


class JobOffer(Base):
    __tablename__ = "job_offers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    required_skills = Column(JSON, default=list)      # list[str]
    critical_skills = Column(JSON, default=list)      # list[str] — must-have
    soft_skills = Column(JSON, default=list)          # list[str]
    experience_required_years = Column(Integer, default=0)
    education_required = Column(String, default="")
    languages_required = Column(JSON, default=list)   # list[{language, level}]
    location = Column(String, default="")
    job_type = Column(String, default="CDI")          # CDI | CDD | Stage | Freelance
    domain = Column(String, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="job_offers")
    sessions = relationship("ScreeningSession", back_populates="job_offer")


class CV(Base):
    __tablename__ = "cvs"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    content_hash = Column(String, default="")          # md5 for duplicate detection
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, ForeignKey("cvs.id"), nullable=True)
    extraction_error = Column(String, nullable=True)

    # Candidate extracted fields
    candidate_name = Column(String, default="")
    candidate_email = Column(String, default="")
    candidate_phone = Column(String, default="")
    candidate_location = Column(String, default="")
    candidate_linkedin = Column(String, default="")
    candidate_github = Column(String, default="")
    language = Column(String, default="en")            # 'fr' | 'en'
    profile = Column(Text, default="")
    experience = Column(JSON, default=list)            # list[str] (experience blocks)
    education = Column(JSON, default=list)             # list[str]
    projects = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    skills = Column(JSON, default=list)                # list[str] canonical
    soft_skills = Column(JSON, default=list)
    skills_in_experience = Column(JSON, default=list)
    languages_spoken = Column(JSON, default=list)      # list[{language, level}]
    interests = Column(JSON, default=list)
    experience_years = Column(Float, default=0.0)
    education_level = Column(String, default="")       # Bachelor | Master | PhD | BTS | Bac
    industry = Column(String, default="")

    # Quality signals from extractor
    confidence_score = Column(Float, default=0.0)
    flags = Column(JSON, default=list)                 # list[str] warnings
    action_verb_scores = Column(JSON, default=dict)
    buzzword_analysis = Column(JSON, default=dict)
    quantified_achievements = Column(JSON, default=list)

    uploaded_at = Column(DateTime, default=datetime.utcnow)

    matching_results = relationship("MatchingResult", back_populates="cv")


class ScreeningSession(Base):
    __tablename__ = "screening_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="pending")         # pending | scoring | completed | failed

    # Scoring weights (must sum to 1.0)
    weights_skills = Column(Float, default=0.35)
    weights_experience = Column(Float, default=0.25)
    weights_education = Column(Float, default=0.15)
    weights_language = Column(Float, default=0.15)
    weights_location = Column(Float, default=0.10)
    weights_soft_skills = Column(Float, default=0.00)  # reserved for V2

    total_cvs = Column(Integer, default=0)
    processed_cvs = Column(Integer, default=0)
    scored_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_offer_id = Column(Integer, ForeignKey("job_offers.id"), nullable=False)

    owner = relationship("User", back_populates="screening_sessions")
    job_offer = relationship("JobOffer", back_populates="sessions")
    matching_results = relationship("MatchingResult", back_populates="session")


class MatchingResult(Base):
    __tablename__ = "matching_results"

    id = Column(Integer, primary_key=True, index=True)
    rank = Column(Integer, default=0)

    # Dimension scores (0.0–1.0)
    skills_score = Column(Float, default=0.0)
    experience_score = Column(Float, default=0.0)
    education_score = Column(Float, default=0.0)
    language_score = Column(Float, default=0.0)
    location_score = Column(Float, default=0.0)
    soft_skills_score = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)           # weighted sum

    # Explanation fields
    matched_skills = Column(JSON, default=list)        # list[str]
    missing_skills = Column(JSON, default=list)        # list[str] critical missing
    missing_critical = Column(JSON, default=list)      # list[str] must-have skills absent

    # Recruiter actions
    status = Column(String, default="pending")         # pending | shortlisted | rejected
    recruiter_note = Column(Text, default="")

    scored_at = Column(DateTime, default=datetime.utcnow)

    session_id = Column(Integer, ForeignKey("screening_sessions.id"), nullable=False)
    cv_id = Column(Integer, ForeignKey("cvs.id"), nullable=False)

    session = relationship("ScreeningSession", back_populates="matching_results")
    cv = relationship("CV", back_populates="matching_results")
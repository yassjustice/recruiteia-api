-- RecruteIA Database Schema for Supabase
-- Copy and paste these SQL commands into Supabase SQL Editor
-- Or run: supabase db push

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'recruiter',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- 2. JOB OFFERS TABLE
CREATE TABLE IF NOT EXISTS job_offers (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    required_skills JSON DEFAULT '[]',
    critical_skills JSON DEFAULT '[]',
    soft_skills JSON DEFAULT '[]',
    experience_required_years INTEGER DEFAULT 0,
    education_required VARCHAR(255) DEFAULT '',
    languages_required JSON DEFAULT '[]',
    location VARCHAR(255) DEFAULT '',
    job_type VARCHAR(50) DEFAULT 'CDI',
    domain VARCHAR(255) DEFAULT '',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_job_offers_owner_id ON job_offers(owner_id);
CREATE INDEX idx_job_offers_is_active ON job_offers(is_active);

-- 3. CVS TABLE
CREATE TABLE IF NOT EXISTS cvs (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INTEGER DEFAULT 0,
    content_hash VARCHAR(255) DEFAULT '',
    is_duplicate BOOLEAN DEFAULT false,
    duplicate_of INTEGER REFERENCES cvs(id) ON DELETE SET NULL,
    extraction_error VARCHAR(255),
    candidate_name VARCHAR(255) DEFAULT '',
    candidate_email VARCHAR(255) DEFAULT '',
    candidate_phone VARCHAR(255) DEFAULT '',
    candidate_location VARCHAR(255) DEFAULT '',
    candidate_linkedin VARCHAR(255) DEFAULT '',
    candidate_github VARCHAR(255) DEFAULT '',
    language VARCHAR(50) DEFAULT 'en',
    profile TEXT DEFAULT '',
    experience JSON DEFAULT '[]',
    education JSON DEFAULT '[]',
    projects JSON DEFAULT '[]',
    certifications JSON DEFAULT '[]',
    skills JSON DEFAULT '[]',
    soft_skills JSON DEFAULT '[]',
    skills_in_experience JSON DEFAULT '[]',
    languages_spoken JSON DEFAULT '[]',
    interests JSON DEFAULT '[]',
    experience_years FLOAT DEFAULT 0.0,
    education_level VARCHAR(50) DEFAULT '',
    industry VARCHAR(255) DEFAULT '',
    confidence_score FLOAT DEFAULT 0.0,
    flags JSON DEFAULT '[]',
    action_verb_scores JSON DEFAULT '{}',
    buzzword_analysis JSON DEFAULT '{}',
    quantified_achievements JSON DEFAULT '[]',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cvs_candidate_email ON cvs(candidate_email);
CREATE INDEX idx_cvs_is_duplicate ON cvs(is_duplicate);

-- 4. SCREENING SESSIONS TABLE
CREATE TABLE IF NOT EXISTS screening_sessions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    weights_skills FLOAT DEFAULT 0.35,
    weights_experience FLOAT DEFAULT 0.25,
    weights_education FLOAT DEFAULT 0.15,
    weights_language FLOAT DEFAULT 0.15,
    weights_location FLOAT DEFAULT 0.10,
    weights_soft_skills FLOAT DEFAULT 0.00,
    total_cvs INTEGER DEFAULT 0,
    processed_cvs INTEGER DEFAULT 0,
    scored_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_offer_id INTEGER NOT NULL REFERENCES job_offers(id) ON DELETE CASCADE
);

CREATE INDEX idx_screening_sessions_owner_id ON screening_sessions(owner_id);
CREATE INDEX idx_screening_sessions_job_offer_id ON screening_sessions(job_offer_id);
CREATE INDEX idx_screening_sessions_status ON screening_sessions(status);

-- 5. MATCHING RESULTS TABLE
CREATE TABLE IF NOT EXISTS matching_results (
    id SERIAL PRIMARY KEY,
    rank INTEGER DEFAULT 0,
    skills_score FLOAT DEFAULT 0.0,
    experience_score FLOAT DEFAULT 0.0,
    education_score FLOAT DEFAULT 0.0,
    language_score FLOAT DEFAULT 0.0,
    location_score FLOAT DEFAULT 0.0,
    soft_skills_score FLOAT DEFAULT 0.0,
    final_score FLOAT DEFAULT 0.0,
    matched_skills JSON DEFAULT '[]',
    missing_skills JSON DEFAULT '[]',
    missing_critical JSON DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'pending',
    recruiter_note TEXT DEFAULT '',
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id INTEGER NOT NULL REFERENCES screening_sessions(id) ON DELETE CASCADE,
    cv_id INTEGER NOT NULL REFERENCES cvs(id) ON DELETE CASCADE
);

CREATE INDEX idx_matching_results_session_id ON matching_results(session_id);
CREATE INDEX idx_matching_results_cv_id ON matching_results(cv_id);
CREATE INDEX idx_matching_results_status ON matching_results(status);
CREATE INDEX idx_matching_results_final_score ON matching_results(final_score DESC);

-- Enable RLS if needed (optional, for security)
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE job_offers ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cvs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE screening_sessions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE matching_results ENABLE ROW LEVEL SECURITY;

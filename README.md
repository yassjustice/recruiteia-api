---
title: RecruteIA API
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# RecruteIA API — Backend

> **Part of RecruteIA (FQIA PFF N°3).**
> **Front-door repo (setup instructions + full docs):** [yassjustice/RecruteIA-FQIA-PFF3](https://github.com/yassjustice/RecruteIA-FQIA-PFF3)
> **System ground truth:** [STATE.md](STATE.md) · **Scoring engine:** [docs/SCORING_RATIONALE.md](docs/SCORING_RATIONALE.md)

FastAPI backend for AI-powered CV screening and intelligent recruitment.

## 📊 Quick Stats

- **Status**: ✅ Production Live
- **URL**: https://yassirhakimi-recruiteia-api.hf.space/api
- **Database**: Supabase PostgreSQL V2 schema (UUID + JSONB) + SQLite fallback
- **Deployment**: Docker on Hugging Face Spaces
- **API Documentation**: `/api/docs` (Swagger UI), detailed contract in `docs/API.md`
- **Health Check**: `/api/health`

## 🔧 Technology Stack

- **Backend**: FastAPI 0.111.0 + Uvicorn 0.29.0
- **Database**: Supabase PostgreSQL (primary) with SQLite automatic failover
- **ORM**: SQLAlchemy 2.0.30
- **Authentication**: JWT (python-jose) + bcrypt
- **AI/NLP**: Groq LLM (`llama-3.3-70b-versatile`) + spaCy (sm models)
- **Document Processing**: pdfplumber + python-docx
- **Containerization**: Docker (Python 3.11-slim)

## 🗄️ Database

**Primary**: Supabase PostgreSQL
```
Host: db.ogthbkujcprkmeykhict.supabase.co
Port: 5432
Database: postgres
Connection: Secure TCP/SSL
```

**Schema version**: **V2** (aligned with Brahim notebooks)
- UUID primary keys across all tables
- JSON/JSONB-first storage for extraction and scoring details
- Single `weights` JSON object on screening sessions
- Rich matching results (`experience_relevance_reason`, `language_details`, penalty/audit fields)

**Fallback**: Local SQLite (automatic zero-downtime failover)
```
Location: data/recruiteia_fallback.db
Activates if Supabase unavailable
```

## 🚀 Getting Started

### Local Development

1. Clone the repository
2. Copy `.env.example` to `.env`
3. Install dependencies: `pip install -r requirements.txt`
4. Download spaCy models: 
   ```bash
   python -m spacy download en_core_web_sm
   python -m spacy download fr_core_news_sm
   ```
5. Run development server: `uvicorn main:app --reload`

### Environment Variables

```bash
# Required
GROQ_API_KEY=your_groq_api_key
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:password@host:port/database

# Optional
ACCESS_TOKEN_EXPIRE_HOURS=24
UPLOAD_DIR=data/uploads
```

For production (Supabase), use:
```
DATABASE_URL=postgresql://postgres:[DB-PASSWORD]@db.ogthbkujcprkmeykhict.supabase.co:5432/postgres
```

## 📚 API Endpoints

- **Authentication**: `/api/auth/login`, `/api/auth/register`, `/api/auth/me`
- **CVs**: `/api/cvs` (upload, list, retrieve)
- **Job Offers**: `/api/offers` (create, extract, list)
- **Scoring**: `/api/sessions` (create, get results)
- **Health**: `/api/health`

> ⚠️ IDs are UUID strings in V2 (not integers).

## 🧪 Testing

Run tests with: `pytest`

Key test suites:
- CV extraction accuracy
- Job parsing correctness
- Scoring algorithm validation
- Authentication flow
- Database failover mechanism

## 🔄 CI/CD

GitHub Actions automatically:
- Runs tests on every push
- Builds Docker image
- Deploys to Hugging Face Spaces
- Verifies health check

## 📦 Deployment

Deployed on **Hugging Face Spaces** as a Docker container.

**Architecture**:
```
HF Spaces Container
├─ FastAPI Application
├─ Uvicorn Server (port 7860)
└─ SQLAlchemy ORM
    ├─ PRIMARY: Supabase PostgreSQL
    └─ FALLBACK: SQLite
```

**Automatic Failover**: If Supabase PostgreSQL is unavailable, the system automatically switches to local SQLite, ensuring zero-downtime operation.

## 📝 Documentation

For detailed technical documentation, see:
- `TECH_STACK_DEPLOYMENT.md` - Complete tech stack & deployment details
- `docs/API.md` - API specification & error handling
- `docs/DATABASE.md` - Database schema & queries

## 👤 Author

**Yassir Hakimi** - AI Recruitment Agent (RecruteIA) Project

## 📄 License

This project is part of the RecruteIA (FQIA PFF N°3) academic project.

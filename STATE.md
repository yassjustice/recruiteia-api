# STATE.md — RecruteIA: Ground Truth System Description

> **This file is the authoritative description of the live system as of 2026-06-04.**
> It supersedes any older PRD, prior audit, or note that contradicts it.
> Requirements source: `brief/PFF FQIA sujet 3 2026.pdf` (distilled in `audit/01_BRIEF_REQUIREMENTS.md`).
> Technical audit lives in `audit/` at the workspace root.
> **Architecture diagram:** [RecruteIA-FQIA-PFF3/assets/diagrams/architecture.png](https://github.com/yassjustice/RecruteIA-FQIA-PFF3/blob/master/assets/diagrams/architecture.png)

---

## 1. System at a glance

| Component | Working dir | GitHub repo | Deploy target |
|-----------|-------------|-------------|---------------|
| **Backend API** | `brief/recruitment-ai/` | `yassjustice/recruiteia-api` | HF Space `yassirhakimi/recruiteia-api` → `https://yassirhakimi-recruiteia-api.hf.space/api` |
| **Frontend** | `rise-hire-frontend/` | `yassjustice/rise-hire-frontend` | Vercel (Next.js 14) |
| **Team docs** | `RecruteIA-FQIA-PFF3/` | `yassjustice/RecruteIA-FQIA-PFF3` | — (docs only, no runnable code) |

> ⚠️ The brief requires ONE documented repo (REQ-DEL-1). Consolidation is underway — see GAP-03 / T03.

---

## 2. Canonical stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Language | Python 3.11+ | `requirements.txt` |
| Backend | FastAPI 0.111 + uvicorn | `main.py` |
| Auth | JWT (python-jose) + bcrypt | `auth_utils.py` |
| AI / NLP | **Groq `llama-3.3-70b-versatile`** | CV parsing, JD parsing, experience scoring |
| PDF / DOCX | pdfplumber 0.11 + python-docx | `src/services/extractor.py` |
| Language detection | langdetect | `extractor.py:17` |
| Fuzzy skill match | difflib `SequenceMatcher` | `scorer.py:67` |
| spaCy | ≥3.8 sm models | installed; minimal use in extractor |
| Database | PostgreSQL (Supabase) primary + SQLite fallback | `database.py`, `db_sync.py` |
| Frontend | Next.js 14 + TypeScript + Tailwind | `rise-hire-frontend/` |
| Hosting | HF Space (backend) + Vercel (frontend) | |

**NOT used** (despite older documents): sentence-transformers, scikit-learn, Streamlit, Gradio, WordPress.
Older PRDs and the prior audit predate the current implementation — see `audit/05_DOC_DRIFT_LOG.md`.

---

## 3. The three modules

### Module 1 — CV Extraction (`src/services/extractor.py`)
Accepts a PDF or DOCX upload. Extracts text with pdfplumber (2-column aware) and langdetect, then sends a structured prompt to Groq `llama-3.3-70b-versatile` to parse: `candidate_name`, `email`, `phone`, `location`, `linkedin`, `github`, `skills`, `soft_skills`, `education`, `experience`, `projects`, `spoken languages`, and `quantified_achievements`. Post-processing applies regex for contact fields, a skill taxonomy for normalization, experience enrichment (action verbs, buzzword analysis), and produces a `confidence_score` + `flags[]`. Stored in `cvs` table.

### Module 2 — Job Offer Analysis (`src/services/jd_parser.py`)
Accepts free-text job description. Groq parses it to structured JSON: `job_title`, `required_skills`, `critical_skills` (skills that are mandatory and carry double weight in scoring), `required_soft_skills`, `required_languages` (with CEFR min level and weight), `experience_required_years` (safe int conversion), `min_education`, `domain`, `location`, `remote_ok`, `description_summary`. Stored in `job_offers` table.

### Module 3 — Scoring & Ranking (`src/services/scorer.py`)
Combines CV data (Module 1) with offer data (Module 2) in a 7-dimension weighted engine (see §4). Returns a ranked list of candidates with per-dimension scores, matched/missing skills, recommendation band, and CSV export. A screening session groups one offer + N CVs + custom weights into one scoring run.

---

## 4. Scoring engine — 7 dimensions

| Dimension | Default weight | Method |
|-----------|:--------------:|--------|
| `skills_match` | **0.30** | Coverage of required skills; critical skills count **2×**; +10% if backed by experience |
| `experience_relevance` | **0.22** | Groq rates 0–100 relevance of candidate's experience vs JD summary (MD5-cached; rule-based fallback) |
| `achievements` | **0.15** | Count of quantified achievements → tiered score |
| `language_quality` | **0.10** | Action-verb density minus buzzword penalty |
| `language_match` | **0.10** | Required languages vs spoken CEFR levels |
| `education` | **0.08** | Education rank vs required minimum rank |
| `location` | **0.05** | Location match / remote-ok flag |

**Penalties:**
- `total × 0.90 ^ (number of critical skills missing)` — exponential penalty for missing must-have skills
- `total × 0.85` if `confidence_score < 60` — low-quality CV extraction discounts the result

**Recommendation bands:** Strong ≥ 0.75 · Potential ≥ 0.55 · Weak ≥ 0.35 · Not Recommended < 0.35

**Threshold colors** (results UI): green ≥ 0.80 · orange ≥ 0.50 · red below 0.50

Weights are **customizable** at session creation time. Default weights sum to 1.0.
Full defense, rationale, and validation: `plan/tasks/T07_scoring_engine_defense.md` (in progress).

---

## 5. API surface

**Base URL (prod):** `https://yassirhakimi-recruiteia-api.hf.space/api`  
**Base URL (dev):** `http://localhost:8000/api`  
**Envelope:** `{ "success": true, "data": ... }` | `{ "success": false, "error": { "code", "message" } }`  
**Auth:** `Authorization: Bearer <JWT>` on all endpoints except `/auth/register`, `/auth/login`, `/health`.

Full contract: `plan/references/API_CONTRACT.md`.

| Group | Key endpoints |
|-------|--------------|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Offers | `POST /offers/extract` (Module 2), `POST/GET /offers`, `GET/PUT/DELETE /offers/{id}` |
| CVs | `POST /cvs` (Module 1, single PDF ≤5 MB), `GET /cvs`, `GET /cvs/{id}` |
| Sessions | `POST /sessions`, `POST /sessions/{id}/score`, `GET /sessions/{id}` |
| Results | `GET /sessions/{id}/results`, `GET /sessions/{id}/export` (CSV) |
| Health | `GET /health`, `GET /health/db`, `GET /stats/summary` |

**Canonical demo flow:**
```
register/login → POST /offers/extract → POST /offers
→ upload N× /cvs → POST /sessions {offer_id, cv_ids, weights}
→ POST /sessions/{id}/score → poll GET /sessions/{id} until completed
→ GET /sessions/{id}/results → GET /sessions/{id}/export
```

---

## 6. Known limitations

These are documented honestly for the technical report and jury questions:

| Ref | Limitation |
|-----|-----------|
| GAP-07 | CV upload is **single-file per call** — no batch endpoint. (PRD ambition, not a brief requirement.) |
| GAP-08 | Module 3 does not surface an explicit `strengths[]` list per candidate. Strengths are implicit in the per-dimension scores and matched skills. |
| GAP-12 | **No weight re-score endpoint.** Weights are fixed at session creation. Changing weights requires creating a new session. |
| — | HF Space **cold start** (~30–60 s). Mitigated by the FE's `ColdStartBanner` component and a pre-warm script (T05). |
| — | Tech choices (Groq, Next.js) differ from the brief's suggested list; they are explicitly justified in the technical report (T04). |

---

## 7. Environment variables (no values here — placeholders only)

Backend secrets live in `.env` (gitignored) locally and in **HF Space Secrets** for production.
See `.env.example` for the full template. Key variables:

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Groq LLM access (required) |
| `DATABASE_URL` | PostgreSQL connection (falls back to SQLite if unset) |
| `SECRET_KEY` | JWT signing key |

Frontend: `NEXT_PUBLIC_API_URL` in Vercel Environment Variables (defaults to HF Space URL).

---

## 8. How to run locally

**Backend:**
```powershell
cd brief\recruitment-ai
python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m spacy download fr_core_news_sm
# Create .env from .env.example, fill in GROQ_API_KEY
uvicorn main:app --reload --port 8000
# Swagger: http://localhost:8000/docs
```

**Frontend:**
```powershell
cd rise-hire-frontend
npm install
# Optionally create .env.local with NEXT_PUBLIC_API_URL=http://localhost:8000/api
npm run dev   # http://localhost:3000
```

---

*Last verified: 2026-06-04. Requirements source: `brief/PFF FQIA sujet 3 2026.pdf`.
Audit lives in `audit/` at workspace root. Maintained by the RecruteIA team.*

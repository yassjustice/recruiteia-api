# RecruteIA API (V2 Schema)

**Base URL (production):** `https://yassirhakimi-recruiteia-api.hf.space/api`  
**Base URL (local):** `http://localhost:7860/api`

## Breaking changes (V1 -> V2)

| Area | V1 | V2 |
|---|---|---|
| IDs | Integer (`123`) | UUID string (`"a1b2..."`) |
| Session weights | Separate fields (`weights_skills`, ...) | JSON object (`weights`) |
| CV confidence | float | JSON object |
| Result score | `final_score` | `total_score` (`final_score` still returned for compatibility) |
| Critical missing skills | `missing_critical` | `critical_missing` (`missing_critical` still returned for compatibility) |

---

## Auth

### POST `/auth/register`

```json
{
  "email": "recruiter@company.ma",
  "password": "StrongPass@123",
  "full_name": "Yassir Hakimi",
  "role": "recruiter"
}
```

Success:

```json
{
  "success": true,
  "data": {
    "id": "0f6c1e2f-8cc1-4d33-a6ee-2f3df69f1fcb",
    "email": "recruiter@company.ma",
    "full_name": "Yassir Hakimi",
    "role": "recruiter",
    "created_at": "2026-05-10T02:00:00Z"
  }
}
```

### POST `/auth/login`

```json
{
  "email": "recruiter@company.ma",
  "password": "StrongPass@123"
}
```

Success:

```json
{
  "success": true,
  "data": {
    "access_token": "jwt-token",
    "token_type": "bearer",
    "user": {
      "id": "0f6c1e2f-8cc1-4d33-a6ee-2f3df69f1fcb",
      "email": "recruiter@company.ma",
      "full_name": "Yassir Hakimi",
      "role": "recruiter",
      "created_at": "2026-05-10T02:00:00Z"
    }
  }
}
```

Use token on protected routes:

`Authorization: Bearer <access_token>`

---

## Offers

### POST `/offers`

Supports both V2 and legacy V1 payload names.

**V2 payload (recommended):**

```json
{
  "job_title": "Senior Python Developer",
  "company_name": "RecruteIA",
  "industry": "Tech",
  "job_type": "CDI",
  "job_function": "Software Engineering",
  "seniority": "Senior",
  "location": "Casablanca",
  "remote_ok": false,
  "raw_text": "Full JD text...",
  "description_summary": "FastAPI backend role",
  "required_skills": ["Python", "FastAPI", "PostgreSQL"],
  "critical_skills": ["Python"],
  "normalized_skills": [{"raw": "Python", "normalized": "Python", "category": "other"}],
  "required_soft_skills": ["Communication", "Autonomy"],
  "required_languages": [{"language": "French", "min_level": "C1", "weight": 0.6}],
  "min_education": "Bachelor",
  "education_field": "Computer Science",
  "experience_required_years": 3,
  "status": "active"
}
```

**Legacy V1 payload (still accepted):**

```json
{
  "title": "Senior Python Developer",
  "description": "Full JD text...",
  "required_skills": ["Python", "FastAPI", "PostgreSQL"],
  "critical_skills": ["Python"],
  "soft_skills": ["Communication"],
  "languages_required": [{"language": "French", "level": "C1"}],
  "education_required": "Bachelor",
  "experience_required_years": 3,
  "location": "Casablanca",
  "job_type": "CDI",
  "domain": "Tech"
}
```

### GET `/offers`

Returns active offers for authenticated user.

### GET `/offers/{offer_id}`

`offer_id` is UUID.

### PUT `/offers/{offer_id}`

Same payload as create.

### DELETE `/offers/{offer_id}`

Soft-close offer (`status = "closed"`).

### POST `/offers/extract`

```json
{
  "text": "Raw job description text...",
  "lang": "fr"
}
```

---

## CVs

### POST `/cvs`

`multipart/form-data` with `file` (PDF, <= 5 MB).

Success (trimmed):

```json
{
  "success": true,
  "data": {
    "id": "b6d7f7f3-6832-4ea6-92dd-0e51d0f2ff80",
    "filename": "cv.pdf",
    "original_filename": "cv.pdf",
    "file_path": "data/uploads/....pdf",
    "file_size_bytes": 143002,
    "language": "fr",
    "candidate_name": "John Doe",
    "skills": ["Python", "SQL"],
    "skills_in_experience": ["Python"],
    "orphan_skills": ["TensorFlow"],
    "confidence_score": {
      "confidence": 82,
      "missing_fields": []
    },
    "confidence_score_value": 82,
    "flags": [
      {"code": "no_experience_section", "severity": "critical", "message": "no experience section"}
    ],
    "extraction_status": "done",
    "created_at": "2026-05-10T02:00:00Z",
    "uploaded_at": "2026-05-10T02:00:00Z"
  }
}
```

### GET `/cvs`

Returns user CVs.

### GET `/cvs/{cv_id}`

`cv_id` is UUID.

---

## Screening sessions

### POST `/sessions`

**V2 payload (recommended):**

```json
{
  "name": "Python shortlist",
  "offer_id": "eec82cc5-0cb1-49f7-90db-827f4f8da9f4",
  "cv_ids": [
    "b6d7f7f3-6832-4ea6-92dd-0e51d0f2ff80",
    "0d3e9e16-f147-48d6-84a3-fd3d53ed2c1d"
  ],
  "weights": {
    "skills_match": 0.30,
    "experience_relevance": 0.22,
    "achievements": 0.15,
    "language_quality": 0.10,
    "language_match": 0.10,
    "education": 0.08,
    "location": 0.05
  }
}
```

**Legacy V1 compatibility:**

- `job_offer_id` is accepted as alias for `offer_id`
- `weights.skills`, `weights.experience`, `weights.language` are accepted and mapped to V2 keys

Success (trimmed):

```json
{
  "success": true,
  "data": {
    "id": "9c846af8-2a2a-4a5f-a90a-a8d5ebf3f4ee",
    "name": "Python shortlist",
    "status": "pending",
    "user_id": "0f6c1e2f-8cc1-4d33-a6ee-2f3df69f1fcb",
    "offer_id": "eec82cc5-0cb1-49f7-90db-827f4f8da9f4",
    "job_offer_id": "eec82cc5-0cb1-49f7-90db-827f4f8da9f4",
    "total_cvs": 2,
    "processed_cvs": 0,
    "weights": {
      "skills_match": 0.3,
      "experience_relevance": 0.22,
      "achievements": 0.15,
      "language_quality": 0.1,
      "language_match": 0.1,
      "education": 0.08,
      "location": 0.05
    },
    "weights_skills": 0.3,
    "weights_experience": 0.22,
    "weights_education": 0.08,
    "weights_language": 0.1,
    "weights_location": 0.05,
    "created_at": "2026-05-10T02:00:00Z",
    "completed_at": null,
    "scored_at": null
  }
}
```

### POST `/sessions/{session_id}/score`

Triggers scoring asynchronously.

### GET `/sessions`

List sessions.

### GET `/sessions/{session_id}`

Get single session.

---

## Results

### GET `/sessions/{session_id}/results`

If not completed:

```json
{
  "success": true,
  "data": {"status": "processing", "results": []}
}
```

If completed (trimmed):

```json
{
  "success": true,
  "data": [
    {
      "rank": 1,
      "cv_id": "b6d7f7f3-6832-4ea6-92dd-0e51d0f2ff80",
      "candidate_name": "John Doe",
      "total_score": 0.86,
      "final_score": 0.86,
      "final_score_pct": 86.0,
      "recommendation": "Strong Match",
      "skills_score": 0.9,
      "experience_score": 0.8,
      "achievements_score": 0.7,
      "language_quality_score": 0.8,
      "language_match_score": 1.0,
      "education_score": 0.8,
      "location_score": 1.0,
      "matched_skills": ["Python", "FastAPI"],
      "missing_skills": [],
      "critical_missing": [],
      "missing_critical": [],
      "language_details": [],
      "flags": [],
      "missing_critical_count": 0,
      "confidence_multiplier_applied": false,
      "student_profile_detected": false,
      "status": "scored",
      "threshold": "green"
    }
  ]
}
```

### GET `/sessions/{session_id}/export`

CSV export with V2 score columns.

---

## Health

### GET `/health`

```json
{"success": true, "data": {"status": "ok", "version": "1.0.0"}}
```

---

## Error handling notes

1. Missing token is typically returned as `403` by `HTTPBearer`.
2. Invalid/expired token returns `401`.

Frontend should treat both as auth failure:

```js
if (response.status === 401 || response.status === 403) {
  // force relogin
}
```

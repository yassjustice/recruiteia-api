# RecruteIA API – Frontend Integration Guide

**Base URL (production):** `https://yassirhakimi-recruiteia-api.hf.space/api`  
**Base URL (local dev):** `http://localhost:7860/api`  
**OpenAPI docs:** `<base>/docs` (Swagger UI)

All endpoints return JSON. File upload uses `multipart/form-data`. All other requests use `application/json`.

---

## 1. Authentication Flow

### Overview
```
POST /auth/register  → create account
POST /auth/login     → get access_token (JWT, 24h expiry)
                     → attach as  Authorization: Bearer <token>  on every protected request
```

### 1.1 Register
```
POST /api/auth/register
Content-Type: application/json
```
**Request body:**
```json
{
  "email": "recruiter@company.ma",
  "password": "StrongPass@123",
  "full_name": "Yassir Hakimi",
  "role": "recruiter"
}
```
**Success `200`:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "recruiter@company.ma",
    "full_name": "Yassir Hakimi",
    "role": "recruiter",
    "created_at": "2024-01-15T10:00:00.000000"
  }
}
```
**Errors:**
| Code | `detail` | Cause |
|------|----------|-------|
| 400 | `Email already registered` | Duplicate email |
| 422 | Validation error object | Missing / invalid fields |

---

### 1.2 Login
```
POST /api/auth/login
Content-Type: application/json
```
**Request body:**
```json
{
  "email": "recruiter@company.ma",
  "password": "StrongPass@123"
}
```
**Success `200`:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGc...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "email": "recruiter@company.ma",
      "full_name": "Yassir Hakimi",
      "role": "recruiter",
      "created_at": "2024-01-15T10:00:00.000000"
    }
  }
}
```
**Errors:**
| Code | `detail` | Cause |
|------|----------|-------|
| 401 | `Invalid credentials` | Wrong email or password |

**Frontend — store the token:**
```js
// After login, persist it:
localStorage.setItem("recruteIA_token", data.access_token);
localStorage.setItem("recruteIA_user", JSON.stringify(data.user));

// Attach to every request:
const token = localStorage.getItem("recruteIA_token");
headers["Authorization"] = `Bearer ${token}`;
```

---

## 2. Job Offers

All offer endpoints require `Authorization: Bearer <token>`.

### 2.1 Create Offer
```
POST /api/offers
Content-Type: application/json
Authorization: Bearer <token>
```
**Request body (exact field names — use these):**
```json
{
  "title": "Développeur Backend Python",
  "description": "Texte libre de la fiche de poste...",
  "required_skills": ["Python", "FastAPI", "PostgreSQL"],
  "critical_skills": ["Python"],
  "soft_skills": ["Autonomie", "Communication"],
  "experience_required_years": 3,
  "education_required": "Bac+5",
  "languages_required": [{"language": "Français", "level": "C1"}],
  "location": "Casablanca",
  "job_type": "CDI",
  "domain": "IT"
}
```
> ⚠️ **Do NOT use** `experience_years`. The field is `experience_required_years`.

**Success `200`:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "Développeur Backend Python",
    "description": "...",
    "required_skills": ["Python", "FastAPI", "PostgreSQL"],
    "critical_skills": ["Python"],
    "soft_skills": [],
    "experience_required_years": 3,
    "education_required": "Bac+5",
    "languages_required": [],
    "location": "Casablanca",
    "job_type": "CDI",
    "domain": "IT",
    "is_active": true,
    "owner_id": 1,
    "created_at": "2024-01-15T10:00:00.000000"
  }
}
```

---

### 2.2 List Offers
```
GET /api/offers
Authorization: Bearer <token>
```
Returns only the authenticated user's active offers.

**Success `200`:**
```json
{ "success": true, "data": [ /* array of JobOfferOut */ ] }
```

---

### 2.3 Get Single Offer
```
GET /api/offers/{offer_id}
Authorization: Bearer <token>
```
**Errors:** `404 { "detail": "Offer not found" }`

---

### 2.4 Update Offer
```
PUT /api/offers/{offer_id}
Content-Type: application/json
Authorization: Bearer <token>
```
Full replacement — send all fields (same body as Create).

---

### 2.5 Delete Offer
```
DELETE /api/offers/{offer_id}
Authorization: Bearer <token>
```
**Success `200`:** `{ "success": true, "data": { "deleted": true } }`

Soft-delete: sets `is_active = false`.

---

### 2.6 Extract Offer from Raw JD Text (AI)
```
POST /api/offers/extract
Content-Type: application/json
Authorization: Bearer <token>
```
**Request body:**
```json
{
  "text": "We are looking for a Python developer with 3 years experience...",
  "lang": "fr"
}
```
`lang` is optional (default `"fr"`). Use `"en"` for English JDs.

> ⚠️ **Field name is `text`**, not `job_description`.

**Success `200`:**
```json
{
  "success": true,
  "data": {
    "title": "Python Developer",
    "domain": "IT",
    "job_type": "CDI",
    "location": "Casablanca",
    "required_skills": ["Python", "FastAPI", "PostgreSQL"],
    "critical_skills": ["FastAPI", "PostgreSQL"],
    "soft_skills": [],
    "experience_required_years": 3,
    "education_required": "Bac+5",
    "languages_required": []
  }
}
```
Use this to auto-fill the Create Offer form. Pass the response `data` directly as the body to `POST /api/offers`.
The extractor can also return extra metadata keys (for internal scoring/enrichment); frontend can safely ignore unknown keys.

**Errors:** `400 { "detail": "text is required" }`

---

## 3. CVs

### 3.1 Upload CV
```
POST /api/cvs
Content-Type: multipart/form-data
Authorization: Bearer <token>
```
**Form field:** `file` — must be a `.pdf` file, max **5 MB**.

**JavaScript example:**
```js
const formData = new FormData();
formData.append("file", fileInputElement.files[0]);

const res = await fetch(`${BASE_URL}/api/cvs`, {
  method: "POST",
  headers: { "Authorization": `Bearer ${token}` },
  // ⚠️ Do NOT set Content-Type manually — browser sets it with boundary
  body: formData,
});
```

**Success `200`:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "original_filename": "jean_dupont_cv.pdf",
    "candidate_name": "Jean Dupont",
    "candidate_email": "jean@dupont.ma",
    "candidate_phone": "+212 600 000000",
    "candidate_location": "Casablanca",
    "candidate_linkedin": "linkedin.com/in/jeandupont",
    "candidate_github": "",
    "language": "fr",
    "skills": ["Python", "Django", "SQL"],
    "soft_skills": ["Autonomie"],
    "experience_years": 4.5,
    "education_level": "Bac+5",
    "confidence_score": 0.87,
    "flags": [],
    "is_duplicate": false,
    "extraction_error": null,
    "uploaded_at": "2024-01-15T10:05:00.000000"
  }
}
```

**Notes:**
- `is_duplicate: true` means this exact file was already uploaded (MD5 hash match). Still returns `200` — the CV is saved.
- `extraction_error: "no_text_extracted"` means the PDF had no readable text (scanned/image PDF). CV is still stored.
- `confidence_score`: 0–100. Below 50 = unreliable extraction.

**Errors:**
| Code | `detail` | Cause |
|------|----------|-------|
| 400 | `Only PDF files are accepted` | Non-PDF file |
| 413 | `File exceeds 5MB limit` | File too large |
| 401 | `Not authenticated` | Missing/invalid token |

---

### 3.2 List CVs
```
GET /api/cvs
Authorization: Bearer <token>
```
Returns all CVs in the system, newest first.

**Success `200`:** `{ "success": true, "data": [ /* array of CVOut */ ] }`

---

### 3.3 Get Single CV
```
GET /api/cvs/{cv_id}
Authorization: Bearer <token>
```
**Errors:** `404 { "detail": "CV not found" }`

---

## 4. Screening Sessions

A session links a job offer + a set of CVs, then scores them.

### 4.1 Create Session
```
POST /api/sessions
Content-Type: application/json
Authorization: Bearer <token>
```
**Request body:**
```json
{
  "name": "Campagne Backend Mai 2024",
  "job_offer_id": 1,
  "cv_ids": [1, 2, 3, 4, 5],
  "weights": {
    "skills": 0.35,
    "experience": 0.25,
    "education": 0.15,
    "language": 0.15,
    "location": 0.10
  }
}
```
> ⚠️ Weights must sum to exactly **1.0** (±0.01 tolerance).

**Success `200`:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Campagne Backend Mai 2024",
    "status": "pending",
    "job_offer_id": 1,
    "total_cvs": 5,
    "processed_cvs": 0,
    "weights_skills": 0.35,
    "weights_experience": 0.25,
    "weights_education": 0.15,
    "weights_language": 0.15,
    "weights_location": 0.10,
    "created_at": "2024-01-15T10:10:00.000000",
    "scored_at": null
  }
}
```

**Errors:**
| Code | `detail` | Cause |
|------|----------|-------|
| 400 | `Weights must sum to 1.0 (got X.X)` | Bad weights |
| 400 | `Some CV IDs not found` | Invalid cv_ids |
| 404 | `Job offer not found` | Invalid job_offer_id |

---

### 4.2 Start Scoring (async)
```
POST /api/sessions/{session_id}/score
Authorization: Bearer <token>
```
No body needed. Scoring runs in the **background**.

**Success `200`:**
```json
{
  "success": true,
  "data": { "message": "Scoring started", "session_id": 1 }
}
```

**Status progression:** `pending` → `scoring` → `completed` | `failed`

**Poll pattern (frontend):**
```js
async function pollSession(sessionId, token, interval = 3000) {
  return new Promise((resolve, reject) => {
    const timer = setInterval(async () => {
      const res = await fetch(`${BASE_URL}/api/sessions/${sessionId}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const { data } = await res.json();
      if (data.status === "completed") { clearInterval(timer); resolve(data); }
      if (data.status === "failed")    { clearInterval(timer); reject(data); }
    }, interval);
  });
}

// Usage:
await fetch(`${BASE_URL}/api/sessions/${id}/score`, { method: "POST", headers: authHeaders });
const session = await pollSession(id, token);
// Now fetch results
```

**Errors:** `409 { "detail": "Scoring already in progress" }`

---

### 4.3 List Sessions
```
GET /api/sessions
Authorization: Bearer <token>
```
Returns the authenticated user's sessions, newest first.

---

### 4.4 Get Single Session
```
GET /api/sessions/{session_id}
Authorization: Bearer <token>
```
Use this to poll `status` field.

**`status` values:**
- `pending` — created, not yet scored
- `scoring` — currently running
- `completed` — results ready
- `failed` — error during scoring

---

## 5. Results

### 5.1 Get Ranked Results
```
GET /api/sessions/{session_id}/results
Authorization: Bearer <token>
```
If session is not yet `completed`, returns:
```json
{ "success": true, "data": { "status": "scoring", "results": [] } }
```

**Success `200` (completed):**
```json
{
  "success": true,
  "data": [
    {
      "rank": 1,
      "cv_id": 3,
      "candidate_name": "Amal Alaoui",
      "candidate_email": "amal@email.ma",
      "final_score": 0.8731,
      "final_score_pct": 87.3,
      "skills_score": 0.9200,
      "experience_score": 0.8000,
      "education_score": 1.0000,
      "language_score": 1.0000,
      "location_score": 1.0000,
      "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
      "missing_critical": [],
      "status": "pending",
      "threshold": "green"
    }
  ]
}
```

**Score threshold colors:**
| `threshold` | `final_score` range | UI color |
|-------------|---------------------|----------|
| `green`     | ≥ 0.80              | 🟢 Green |
| `orange`    | 0.50 – 0.79         | 🟡 Orange |
| `red`       | < 0.50              | 🔴 Red |

All scores are **0.0–1.0** range. `final_score_pct` is `final_score × 100`.

---

### 5.2 Export Results as CSV
```
GET /api/sessions/{session_id}/export
Authorization: Bearer <token>
```
Returns a CSV file download. Browser-safe approach:
```js
const res = await fetch(`${BASE_URL}/api/sessions/${sessionId}/export`, {
  headers: { "Authorization": `Bearer ${token}` }
});
const blob = await res.blob();
const url  = URL.createObjectURL(blob);
const a    = document.createElement("a");
a.href     = url;
a.download = `session_${sessionId}_results.csv`;
a.click();
```

**CSV columns:** `rank, name, email, phone, location, final_score_pct, skills_score, experience_score, education_score, language_score, location_score, matched_skills, missing_critical, status`

---

## 6. Health Check

```
GET /api/health
```
No auth required.

**`200`:**
```json
{ "success": true, "data": { "status": "ok", "version": "1.0.0" } }
```

---

## 7. Error Handling Reference

### Universal error shape
All non-2xx responses use FastAPI's default:
```json
{ "detail": "Error message here" }
```

### Common HTTP codes
| Code | Meaning |
|------|---------|
| 200  | OK |
| 400  | Bad request (validation, business logic) |
| 401  | Missing or expired token |
| 403  | Forbidden (wrong user) |
| 404  | Resource not found |
| 409  | Conflict (e.g., scoring already running) |
| 413  | File too large |
| 422  | Pydantic validation error (wrong field types/names) |
| 500  | Server error |

### Frontend error handler
```js
async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("recruteIA_token");
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (res.status === 401) {
    localStorage.removeItem("recruteIA_token");
    window.location.href = "/login";
    return;
  }

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return data;
}
```

---

## 8. CORS

The server allows `*` origins. No proxy needed in development.

---

## 9. WordPress Integration Notes (Otman)

Since the frontend runs on WordPress with custom JS:

1. **Store the token in `localStorage`** (or a cookie with `HttpOnly=false` since you need JS access):
   ```js
   localStorage.setItem("recruteIA_token", response.data.access_token);
   ```

2. **Never set `Content-Type: multipart/form-data` manually** for file uploads — let the browser set the boundary automatically via `FormData`.

3. **Polling** can be done with `setInterval` + a progress indicator (spinner/progress bar) while `status !== "completed"`.

4. **CORS**: No special server config needed; `*` is already set.

5. **Base URL**: Store it in one place:
   ```js
   const RECRUTE_IA_API = "https://yassirhakimi-recruiteia-api.hf.space/api";
   ```

6. **Authentication guard**: Before any API call, check the token:
   ```js
   if (!localStorage.getItem("recruteIA_token")) {
     // redirect to login page
   }
   ```

---

## 10. Complete Request/Response Examples

### Full recruiter workflow (JS pseudocode)

```js
// 1. Register + Login
const { data: { access_token, user } } = await apiFetch("/auth/login", {
  method: "POST", body: JSON.stringify({ email, password })
});
localStorage.setItem("recruteIA_token", access_token);

// 2. (Optional) Extract offer from JD text
const { data: extractedOffer } = await apiFetch("/offers/extract", {
  method: "POST", body: JSON.stringify({ text: rawJDText, lang: "fr" })
});

// 3. Create offer
const { data: offer } = await apiFetch("/offers", {
  method: "POST", body: JSON.stringify({
    ...extractedOffer,          // from extract, or fill manually
    title: "Développeur Backend",
    description: rawJDText,
    job_type: "CDI",
  })
});

// 4. Upload CVs
const cvIds = [];
for (const file of selectedFiles) {
  const fd = new FormData();
  fd.append("file", file);
  const { data: cv } = await fetch(`${BASE}/cvs`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}` },
    body: fd,
  }).then(r => r.json());
  cvIds.push(cv.id);
}

// 5. Create session + score
const { data: session } = await apiFetch("/sessions", {
  method: "POST", body: JSON.stringify({
    name: "Campagne Backend Mai 2024",
    job_offer_id: offer.id,
    cv_ids: cvIds,
    weights: { skills: 0.35, experience: 0.25, education: 0.15, language: 0.15, location: 0.10 }
  })
});

await apiFetch(`/sessions/${session.id}/score`, { method: "POST" });

// 6. Poll until completed
const completed = await pollSession(session.id, token);

// 7. Get ranked results
const { data: results } = await apiFetch(`/sessions/${session.id}/results`);
// results[0] = top candidate, results[0].threshold = "green"/"orange"/"red"
```

---

## 11. Quick Endpoint Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET    | `/api/health` | ❌ | Health check |
| POST   | `/api/auth/register` | ❌ | Register |
| POST   | `/api/auth/login` | ❌ | Login → token |
| POST   | `/api/offers` | ✅ | Create job offer |
| GET    | `/api/offers` | ✅ | List my offers |
| GET    | `/api/offers/{id}` | ✅ | Get offer |
| PUT    | `/api/offers/{id}` | ✅ | Update offer |
| DELETE | `/api/offers/{id}` | ✅ | Soft-delete offer |
| POST   | `/api/offers/extract` | ✅ | AI extract from JD text |
| POST   | `/api/cvs` | ✅ | Upload PDF CV |
| GET    | `/api/cvs` | ✅ | List all CVs |
| GET    | `/api/cvs/{id}` | ✅ | Get CV |
| POST   | `/api/sessions` | ✅ | Create session |
| POST   | `/api/sessions/{id}/score` | ✅ | Start scoring (async) |
| GET    | `/api/sessions` | ✅ | List my sessions |
| GET    | `/api/sessions/{id}` | ✅ | Get session + status |
| GET    | `/api/sessions/{id}/results` | ✅ | Get ranked results |
| GET    | `/api/sessions/{id}/export` | ✅ | Download CSV |

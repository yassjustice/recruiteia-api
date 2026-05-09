# PDF Script / Storyboard 02 - API Documentation Pack

Status: **script only** (no design execution yet).

Target format: **A4 portrait**  
Target length: **12 pages**

---

## 1. Objective

Produce a frontend-ready API documentation PDF that can be used by Otman (and future frontend devs) without guessing behavior.

Must include:
1. endpoint groups,
2. request/response schemas,
3. auth and token flow,
4. async scoring behavior,
5. error handling,
6. WordPress integration notes.

Primary source: `docs/API.md` (authoritative).

---

## 2. Narrative arc

1. Quick orientation (base URL, auth model, conventions).
2. Endpoint-by-endpoint operational mapping.
3. Integration pitfalls and robust patterns.
4. Final implementation checklist.

---

## 3. Page-by-page storyboard

## Page 1 - Cover + how to use
- Title: `Rise Hire API Integration Guide`
- Include:
  - production/local base URLs,
  - docs endpoint (`/docs`),
  - versioning note.

## Page 2 - Global conventions
- JSON envelope conventions and file upload exception.
- Auth header standard.
- Required content types by route family.

## Page 3 - Authentication module
- Endpoints:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
- Include:
  - request schemas,
  - success schema,
  - error cases.

## Page 4 - Job offers module
- Endpoints:
  - create/list/get/update/delete,
  - extract from JD text.
- Highlight naming pitfalls:
  - `experience_required_years` exact field,
  - `text` exact extract input key.

## Page 5 - CV ingestion module
- Endpoint:
  - `POST /api/cvs`
- Cover:
  - multipart usage,
  - file limits (.pdf, 5MB),
  - duplicate behavior (`is_duplicate`),
  - extraction quality fields (`confidence_score`, `extraction_error`).

## Page 6 - CV retrieval module
- `GET /api/cvs`
- `GET /api/cvs/{cv_id}`
- Include table of important CV output fields for UI display.

## Page 7 - Sessions module (orchestration)
- `POST /api/sessions`
- Explain weights object and sum-to-1.0 rule.
- Schema examples and validation errors.

## Page 8 - Async scoring lifecycle
- `POST /api/sessions/{id}/score`
- Polling flow diagram:
  - pending -> scoring -> completed/failed.
- Include recommended polling interval and stop conditions.

## Page 9 - Results and thresholds
- `GET /api/sessions/{id}/results`
- Explain:
  - `final_score` vs `final_score_pct`,
  - threshold mapping (green/orange/red),
  - ranked list interpretation.

## Page 10 - Export and reporting
- `GET /api/sessions/{id}/export`
- CSV download flow and columns table.

## Page 11 - Error handling and resilience
- Universal error shape:
  - `{ "detail": "..." }`
- HTTP status reference table.
- Frontend error strategy:
  - token expiry handling,
  - retries,
  - user-safe messaging.

## Page 12 - WordPress integration implementation checklist
- Token storage and guard checks.
- FormData rules.
- CORS notes.
- End-to-end pseudocode summary.

---

## 4. Required data blocks to include verbatim

1. Endpoint list from `docs/API.md` section 11.
2. Polling logic pattern from session section.
3. WordPress notes from section 9.
4. Error code matrix from section 7.

---

## 5. Visual structure rules for this PDF

1. Every endpoint section uses same card pattern:
   - method/path,
   - auth,
   - request,
   - success,
   - errors.
2. Tables for schema fields, not paragraph walls.
3. Distinct badges for method verbs (GET/POST/PUT/DELETE).
4. Warning callouts for common integration mistakes.


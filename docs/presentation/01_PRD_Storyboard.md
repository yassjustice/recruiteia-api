# PDF Script / Storyboard 01 - PRD & Product Vision

Status: **script only** (no design execution yet).

Target format: **A4 portrait**  
Target length: **10 pages**

---

## 1. Objective

Build a professional PRD document that explains:
1. the problem,
2. product scope,
3. users/personas,
4. feature set,
5. business and technical rationale,
6. success criteria and delivery status.

Audience: IDS evaluators, project mentors, product/design/backend contributors.

---

## 2. Narrative arc

1. Why this exists (problem pressure).
2. What we built (solution framing).
3. Who uses it (personas and use cases).
4. How it works (functional journey).
5. Why it is credible (constraints, assumptions, KPIs, roadmap).

---

## 3. Page-by-page storyboard

## Page 1 - Cover + positioning
- Title: `Rise Hire - Product Requirements Document`
- Subhead: `AI-driven CV Screening for IDS Sujet 3`
- Blocks:
  - project identity,
  - one-sentence mission,
  - team credits (compact),
  - version/date/status.
- Visual: clean cover, light background, subtle brand accents.

## Page 2 - Executive summary
- Sections:
  - context (RH screening pain),
  - what Rise Hire changes,
  - key outcomes.
- Include three measurable statements:
  - faster triage,
  - more consistent ranking,
  - clearer decision traceability.

## Page 3 - Problem and opportunity
- Two-column model:
  - left: current workflow pain points,
  - right: opportunity and expected impact.
- Include quantified pain examples (time, inconsistency, overload).

## Page 4 - Scope (in / out)
- In-scope:
  - auth + offer creation,
  - CV ingestion,
  - extraction,
  - scoring,
  - ranking,
  - export.
- Out-of-scope:
  - full ATS replacement,
  - interview scheduling automation,
  - payroll/HRIS integration.

## Page 5 - Personas and jobs-to-be-done
- Persona cards:
  - recruiter,
  - hiring manager,
  - project admin.
- For each:
  - goal,
  - pain,
  - success condition.

## Page 6 - End-to-end user journey
- Steps:
  1. login,
  2. create/extract offer,
  3. upload CVs,
  4. create session + score,
  5. review ranked results,
  6. export.
- Add decision points and failure points.

## Page 7 - Feature detail matrix
- Table with columns:
  - feature,
  - user value,
  - technical owner,
  - status,
  - risk.
- Must include: upload limits, duplicate detection, async scoring behavior.

## Page 8 - Scoring model summary
- Explain weighted criteria and penalty concept.
- Use simplified formula and readable example.
- Reference Mohamed guide as methodological grounding.

## Page 9 - Success metrics and acceptance criteria
- Product KPIs:
  - scoring completion rate,
  - extraction confidence distribution,
  - recruiter decision time reduction.
- Acceptance criteria for release readiness.

## Page 10 - Delivery state and next phase
- What is complete (backend, API contract).
- What is in progress (frontend integration, UX polish).
- Next milestones and operational checklist.

---

## 4. Required assets/data

1. `docs/API.md` for endpoint reality and constraints.
2. Team role facts supplied in project history.
3. Scoring rationale from `GUIDE_MOHAMED_SCORING_DESIGN.md`.
4. Any approved brand assets from Otman (if provided later).

---

## 5. Copy style rules for this PDF

1. Sentence length short-to-medium.
2. No dense paragraphs over 5 lines in A4.
3. Prefer bullets for procedural content.
4. Every page has:
   - one headline message,
   - one supporting structure (table/flow/card).


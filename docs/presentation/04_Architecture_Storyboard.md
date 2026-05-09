# PDF Script / Storyboard 04 - Architecture, Connections, and Workflow Logic

Status: **script only** (no design execution yet).

Target format: **landscape (non-A4)**  
Target length: **8 pages**

---

## 1. Objective

Provide a clear system-level explanation of:
1. department interactions,
2. runtime data flow,
3. backend module boundaries,
4. scoring/extraction orchestration,
5. operational and error-handling flows.

This document should be presentation-grade for technical + semi-technical audiences.

---

## 2. Narrative arc

1. System at a glance.
2. Actor-to-service interactions.
3. Backend internals and pipelines.
4. Data and control flows.
5. Reliability and governance.

---

## 3. Page-by-page storyboard

## Page 1 - Cover and legend
- Title: `Rise Hire Architecture and Workflow`
- Include symbol legend:
  - actor,
  - service,
  - datastore,
  - async job,
  - output/report.

## Page 2 - Department connection map
- Department nodes:
  - RH/Product stakeholders,
  - NLP/scoring contributors,
  - backend engineering,
  - frontend/branding.
- Show directional collaboration links.

## Page 3 - Context diagram (C4-level context style)
- External users and interfaces.
- Rise Hire platform as central system.
- External dependencies:
  - Supabase/PostgreSQL,
  - model providers (if abstracted),
  - export consumers.

## Page 4 - Container/service view
- Backend containers/modules:
  - auth,
  - offers,
  - CV ingestion/extraction,
  - sessions/scoring,
  - results/export.
- Include API boundaries and ownership notes.

## Page 5 - Runtime workflow: recruiter journey
- Sequence-style flow:
  1. authenticate,
  2. create/extract offer,
  3. upload CVs,
  4. launch scoring,
  5. poll status,
  6. fetch results/export.
- Include async branch for scoring.

## Page 6 - Scoring and extraction logic flow
- Data transformation stages:
  - CV raw input -> parsed profile,
  - requirements extraction,
  - weighted scoring,
  - threshold classification.
- Include critical skill penalty behavior summary.

## Page 7 - Error paths and operational safety
- Show key failure branches:
  - auth failure,
  - invalid payload/weights,
  - extraction low confidence,
  - scoring conflict / failed status.
- Include frontend-facing handling strategy.

## Page 8 - Deployment and final integration map
- Production topology summary:
  - backend deployment,
  - frontend consumer,
  - DB and persistent storage,
  - export/reporting channel.
- Include final "ready-to-finish" integration checklist.

---

## 4. Required technical anchors

1. Endpoint families must align with `docs/API.md`.
2. Scoring narrative must align with Mohamed scoring guide.
3. Async session scoring lifecycle must be explicit.
4. CSV export flow must be represented.

---

## 5. Visual standards for this PDF

1. Use landscape to preserve flow readability.
2. Avoid crossing connectors where possible.
3. Use color only as semantic coding (not decoration).
4. Every complex diagram page needs:
   - title,
   - short reading instruction,
   - legend block.


# Frontend Notice: API V2 Migration

This document is the WordPress frontend handoff for the V2 migration.

## Effective changes

1. **IDs are UUID strings**
   - Old: `id: 123`
   - New: `id: "7c9f7a0c-3f34-44b7-aac6-5f7ee0d2dc3d"`

2. **Sessions use `weights` JSON**
   - V2 canonical payload:
     - `skills_match`
     - `experience_relevance`
     - `achievements`
     - `language_quality`
     - `language_match`
     - `education`
     - `location`

3. **Results now expose richer scoring**
   - Canonical fields:
     - `total_score`
     - `recommendation`
     - `achievements_score`
     - `language_quality_score`
     - `language_match_score`
     - `critical_missing`
     - `experience_relevance_reason`
     - `language_details`
     - `confidence_multiplier_applied`
     - `student_profile_detected`
     - `missing_critical_count`

4. **CV payload now stores extractor-rich outputs**
   - `orphan_skills`
   - `confidence_score` (object)
   - `flags` (array of objects)
   - `action_verb_scores`
   - `buzzword_analysis`
   - `quantified_achievements`

## Backward compatibility (kept intentionally)

The backend still returns legacy aliases so frontend migration can be progressive:

- `final_score` (alias of `total_score`)
- `missing_critical` (alias of `critical_missing`)
- `job_offer_id` (alias of `offer_id`)
- `weights_skills` / `weights_experience` / ... (derived from `weights`)
- CV aliases:
  - `original_filename` (alias of `filename`)
  - `file_size` (alias of `file_size_bytes`)
  - `uploaded_at` (alias of `created_at`)

## Frontend action list

1. Treat all IDs as strings.
2. Update TypeScript/JS models to include V2 fields.
3. Prefer `total_score` and `critical_missing` in UI.
4. Keep fallback support for legacy aliases during transition.
5. Keep auth-failure handling as:
   - `401` invalid/expired token
   - `403` missing/blocked auth header

## Contract source of truth

- `docs/API.md`

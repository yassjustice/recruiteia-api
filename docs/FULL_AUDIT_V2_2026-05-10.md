# Full V2 Audit Report

**Date:** 2026-05-10  
**Scope:** Production API, Supabase schema, deployment pipeline, compatibility, stress sanity.

## Final verdict

**PASS** — V2 is correctly in place end-to-end.

## 1. Production API audit (full flow)

**Result:** `23 passed / 0 failed`  
**Status:** PASS

Validated on production:

- Health + auth edge cases (`403` unauth, `401` bad credentials)
- Register/login (UUID user IDs confirmed)
- Offers: create/list/get/extract/update/delete
- CVs: upload/list/get
- Sessions: create/list/get/score
- Results: get/export
- Backward-compatibility aliases verified (`final_score`, `missing_critical`, `job_offer_id`, legacy weight aliases)

## 2. Supabase schema audit vs `brief/schema_updated.sql`

**Result:** schema match = `true`  
**Status:** PASS

- Tables: `5 expected / 5 actual`
- Columns (expected tables): `100 / 100`
- Indexes: all expected indexes present
- Policies: `5 / 5`
- RLS: enabled on all expected tables

## 3. Deployment pipeline audit

**Workflow:** `Sync to Hugging Face Spaces`  
**Latest run:** `25619262550`  
**Conclusion:** `success`  
**Commit:** `b30f94002a0a3b16f0a4a6b9596afc28b1121614`

## 4. Stress sanity re-check

**Status:** PASS

- JD extraction burst: `10/10` success, avg `0.584s`, max `0.812s`
- Health concurrent checks: `24/24` success, avg `0.826s`, max `0.969s`

## 5. Migration artifacts present

- Backup: `data/db_backups/v1_backup_20260510_034623.json`
- Migration report: `data/db_backups/v2_migration_report_20260510_034624.json`

## Conclusion

The platform is consistent across:

1. **Database schema (V2)**
2. **Production API behavior**
3. **Frontend compatibility layer**
4. **Deployment automation**

No blocking issues found in this re-audit.

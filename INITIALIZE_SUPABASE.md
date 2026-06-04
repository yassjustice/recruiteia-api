# Initialize Supabase Schema - Quick Guide

## Problem: No Tables in Supabase

Your Supabase project (`ogthbkujcprkmeykhict`) is currently empty because the schema has never been created.

**Solution:** Initialize the database schema with 5 tables.

---

## ✅ Quick Steps to Initialize

### **STEP 1: Copy the SQL**

```sql
-- Located in: docs/SCHEMA.sql
-- Copy all the CREATE TABLE statements
```

### **STEP 2: Go to Supabase SQL Editor**

```
https://supabase.com/dashboard/project/ogthbkujcprkmeykhict/sql/new
```

### **STEP 3: Paste & Run**

1. Go to Supabase dashboard → SQL Editor
2. Create new query
3. Paste the entire contents of `docs/SCHEMA.sql`
4. Click the **"RUN"** button (▶️)

### **STEP 4: Verify Tables Created**

After ~5 seconds, you should see:

```
✅ CREATE TABLE "public"."users" - Success
✅ CREATE TABLE "public"."job_offers" - Success
✅ CREATE TABLE "public"."cvs" - Success
✅ CREATE TABLE "public"."screening_sessions" - Success
✅ CREATE TABLE "public"."matching_results" - Success
✅ CREATE INDEX "public"."idx_users_email" - Success
... (and 11 more indexes)
```

---

## 📊 What Gets Created

### 5 Tables:
- ✅ **users** - Recruiter accounts
- ✅ **job_offers** - Job descriptions
- ✅ **cvs** - Uploaded CVs with extracted data
- ✅ **screening_sessions** - Batch scoring runs
- ✅ **matching_results** - Scoring results

### 12 Indexes:
- Fast lookups by email, owner, job offer, status, score

### Foreign Key Constraints:
- Automatic cascade deletion
- Referential integrity

---

## 🎯 Expected Result After Initialization

**Before:**
```
Database: ogthbkujcprkmeykhict
Tables: (empty)
```

**After:**
```
Database: ogthbkujcprkmeykhict
Tables:
  ✓ users
  ✓ job_offers
  ✓ cvs
  ✓ screening_sessions
  ✓ matching_results

Indexes: 12
Relationships: 8
```

You should now see all tables in Supabase Dashboard:
```
https://supabase.com/dashboard/project/ogthbkujcprkmeykhict/database/tables
```

---

## 🔄 Alternative: Using Python Script

If you prefer using Python:

```bash
cd recruitment-ai
python init_database.py
```

This will:
1. ✅ Connect to Supabase
2. ✅ Create all tables
3. ✅ Create all indexes
4. ✅ Show schema visualization
5. ✅ Display success report

---

## 📋 Files Reference

- **SQL Script:** `docs/SCHEMA.sql` - Complete CREATE TABLE statements
- **Schema Documentation:** `docs/SCHEMA.md` - Detailed table descriptions
- **Python Initializer:** `init_database.py` - Automated initialization script

---

## ✨ After Initialization

Your Supabase database will be ready for:

1. **User Registration** - Store recruiter accounts
2. **Job Posting** - Add job descriptions
3. **CV Upload** - Upload and extract CVs
4. **Scoring** - Create screening sessions and score candidates
5. **Results** - Store and retrieve matching results

---

## 🆘 Troubleshooting

### Issue: "Connection refused" when running Python script

**Solution:** Check environment variables
```bash
# Make sure DATABASE_URL is set
echo $DATABASE_URL
# Should show: postgresql://postgres:[DB-PASSWORD]@db.ogthbkujcprkmeykhict.supabase.co:5432/postgres
```

### Issue: "Permission denied" in Supabase

**Solution:** Use the `postgres` user (not authenticated user)
- Use the full connection string from `.env`
- Ensure PASSWORD is correct: `[DB-PASSWORD]`

### Issue: Tables already exist

**Solution:** Drop them first (careful - data loss!)
```bash
python init_database.py --drop
```

---

## 📝 Next Steps

1. ✅ Initialize schema (this guide)
2. ✅ Verify tables exist in Supabase dashboard
3. ✅ Deploy API (will auto-create schema if missing)
4. ✅ Test endpoints (POST /auth/register, POST /cvs, etc.)
5. ✅ Monitor application logs

---

**Status:** Ready to initialize  
**Database:** Supabase PostgreSQL (ogthbkujcprkmeykhict)  
**Tables:** 5  
**Indexes:** 12

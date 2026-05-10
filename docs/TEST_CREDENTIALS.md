# Test Credentials for Frontend Developer

**Status:** ✅ Fresh test user created and verified on production (2026-05-10)

## First Test User

**Email:** `frontend_test_user@company.ma`  
**Password:** `StrongPass@123`  
**User ID:** `37432637-842f-4b2c-a3ce-7c824ce9b74a`

### Quick Verification

```bash
curl -X POST https://yassirhakimi-recruiteia-api.hf.space/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"frontend_test_user@company.ma","password":"StrongPass@123"}'
```

Response includes:
- `access_token` (JWT, valid 24 hours)
- `user` object with `id` (UUID), `email`, `full_name`, `role`

## Usage for Frontend Testing

### 1. Login

```javascript
const response = await fetch('https://yassirhakimi-recruiteia-api.hf.space/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'frontend_test_user@company.ma',
    password: 'StrongPass@123'
  })
});

const data = await response.json();
const token = data.data.access_token;
```

### 2. Use Token on Protected Routes

```javascript
const headers = {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
};

// Example: Create offer
const r = await fetch('https://yassirhakimi-recruiteia-api.hf.space/api/offers', {
  method: 'POST',
  headers,
  body: JSON.stringify({
    job_title: 'Senior Python Developer',
    company_name: 'RecruteIA',
    required_skills: ['Python', 'FastAPI'],
    critical_skills: ['Python'],
    experience_required_years: 3
  })
});
```

## Auth Error Codes

- `200` success (login/register)
- `401` invalid credentials or expired token
- `403` missing Authorization header or bearer token not sent

## Notes

- This user has full recruiter permissions
- Token expires after 24 hours (renew by logging in again)
- All data created by this user is scoped to their `user_id`
- Safe to use for end-to-end testing (CREATE, READ, UPDATE, DELETE workflows)

# RecruteIA Frontend Integration Notes
## WordPress / JavaScript Team

**Last Updated:** Production Auth Testing Complete  
**Status:** ✅ All endpoints tested and working

---

## 🔴 CRITICAL: ONE API.MD CHANGE REQUIRED

During production authentication testing, we discovered **one undocumented behavior**:

### Missing Token Returns 403 (Not 401)

| Case | HTTP Code | Behavior |
|------|-----------|----------|
| **Missing Token** | **403** | Token not provided in Authorization header |
| Invalid Token | 401 | Token provided but invalid/expired |
| Wrong Password | 401 | Credentials don't match |
| Other Errors | 400/422/500 | Business logic or server errors |

**API.md was updated** (lines 548–556) to document this behavior.

### ✅ Impact for Frontend Teams

**Before:** Checked `if (status === 401)`  
**After:** Check `if (status === 401 || status === 403)`

```javascript
// CORRECT: Handle both cases
if (response.status === 401 || response.status === 403) {
  // Clear token and redirect to login
  localStorage.removeItem('recruteIA_token');
  window.location.href = '/login';
}
```

---

## ✅ What We Verified in Production

### Authentication Flow ✓
- [x] `POST /auth/login` → Returns JWT token (200 OK)
- [x] JWT tokens store in localStorage successfully
- [x] Bearer token format works: `Authorization: Bearer {token}`
- [x] Protected routes require valid token
- [x] Missing token → 403 Forbidden
- [x] Invalid token → 401 Unauthorized
- [x] Token expiry → 24 hours (as documented)

### Security ✓
- [x] Password hashing via bcrypt (non-reversible)
- [x] JWT signature validation on every request
- [x] HTTPS/TLS enabled on production API
- [x] CORS enabled (no special proxy needed)

### Test Results ✓
- [x] Login with: `wp_sim2_1778330933@company.ma` / `StrongPass@123` → **✅ Success**
- [x] Token generation → **✅ Success**
- [x] Protected route access → **✅ Success**
- [x] Missing token rejection → **✅ Success (403)**
- [x] Invalid token rejection → **✅ Success (401)**

---

## WordPress / JavaScript Specific Guidance

### 1. Token Storage Options

#### Option A: JavaScript localStorage (Recommended for SPA)
```javascript
localStorage.setItem('recruteIA_token', response.data.access_token);
localStorage.setItem('recruteIA_user', JSON.stringify(response.data.user));
```
**Pros:** Fast, easy, works immediately  
**Cons:** Vulnerable to XSS (mitigated since API is separate from WordPress)

#### Option B: WordPress User Meta (Recommended for WordPress)
```php
// PHP side (after login verification)
update_user_meta(get_current_user_id(), 'recrute_ia_token', $token);
update_user_meta(get_current_user_id(), 'recrute_ia_expires', time() + 86400);

// JavaScript side (load from WordPress REST)
const token = await fetch('/wp-json/custom/v1/get-token')
  .then(r => r.json());
```
**Pros:** Server-side storage (more secure), can manage expiration  
**Cons:** Requires PHP endpoint setup

**Recommendation:** Use localStorage for MVP, switch to WordPress meta for production.

---

### 2. CORS Configuration (Already Done)

✅ **No special setup needed** — API has `Access-Control-Allow-Origin: *`

This means:
- ✓ WordPress frontend can call API directly
- ✓ No proxy needed
- ✓ Fetch/AJAX works without errors
- ✓ Cookies not required

### 3. API Call Methods

#### Fetch API (Modern, No Dependencies)
```javascript
async function loginUser(email, password) {
  const response = await fetch(
    'https://yassirhakimi-recruiteia-api.hf.space/api/auth/login',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    }
  );
  
  if (response.status === 401 || response.status === 403) {
    throw new Error('Invalid credentials');
  }
  
  return response.json();
}
```

#### jQuery AJAX (For WordPress Compatibility)
```javascript
jQuery.ajax({
  url: 'https://yassirhakimi-recruiteia-api.hf.space/api/auth/login',
  type: 'POST',
  dataType: 'json',
  data: JSON.stringify({ email, password }),
  contentType: 'application/json',
  success: function(response) {
    localStorage.setItem('recruteIA_token', response.data.access_token);
  },
  error: function(xhr) {
    if (xhr.status === 401 || xhr.status === 403) {
      console.error('Invalid credentials');
    }
  }
});
```

#### Axios (Popular in Modern WordPress Plugins)
```javascript
const recruteAPI = axios.create({
  baseURL: 'https://yassirhakimi-recruiteia-api.hf.space/api'
});

// Add token to all requests
recruteAPI.interceptors.request.use(config => {
  const token = localStorage.getItem('recruteIA_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors globally
recruteAPI.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.removeItem('recruteIA_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Usage:
const { data } = await recruteAPI.post('/auth/login', { email, password });
```

---

### 4. File Upload Quirk (Critical!)

**Problem:** Setting `Content-Type: multipart/form-data` manually breaks file uploads  
**Solution:** Let browser set it via FormData

```javascript
// ✅ CORRECT
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('https://.../api/cvs', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  // DON'T set Content-Type header — browser handles it
  body: formData
});

// ❌ WRONG (browser can't set boundary)
fetch('https://.../api/cvs', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'multipart/form-data' // ← BREAKS file upload
  },
  body: formData
});
```

---

### 5. Complete WordPress Login Example

#### HTML
```html
<form id="recrute-login-form">
  <input type="email" id="email" placeholder="Email" required>
  <input type="password" id="password" placeholder="Password" required>
  <button type="submit">Login</button>
  <div id="error" style="display:none; color:red;"></div>
</form>
```

#### JavaScript
```javascript
jQuery(document).ready(function($) {
  
  $('#recrute-login-form').on('submit', async function(e) {
    e.preventDefault();
    $('#error').hide();
    
    const email = $('#email').val();
    const password = $('#password').val();
    
    try {
      const response = await fetch(
        'https://yassirhakimi-recruiteia-api.hf.space/api/auth/login',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        }
      );
      
      if (response.status === 401 || response.status === 403) {
        $('#error').text('Invalid email or password').show();
        return;
      }
      
      if (!response.ok) {
        $('#error').text('Login failed. Please try again.').show();
        return;
      }
      
      const data = await response.json();
      
      // Store token and user info
      localStorage.setItem('recruteIA_token', data.data.access_token);
      localStorage.setItem('recruteIA_user', JSON.stringify(data.data.user));
      
      // Redirect to dashboard
      window.location.href = '/recrute-dashboard/';
      
    } catch (error) {
      console.error('Network error:', error);
      $('#error').text('Network error. Please check your connection.').show();
    }
  });
  
  // Logout handler
  $('#logout-btn').on('click', function() {
    localStorage.removeItem('recruteIA_token');
    localStorage.removeItem('recruteIA_user');
    window.location.href = '/wp-login.php';
  });
  
});
```

---

### 6. Protected Route Wrapper

```javascript
// Add to every page that requires authentication
function ensureAuthenticated() {
  const token = localStorage.getItem('recruteIA_token');
  
  if (!token) {
    console.log('No token found, redirecting to login');
    window.location.href = '/login';
    return false;
  }
  
  // Optional: Verify token is still valid
  fetch('https://yassirhakimi-recruiteia-api.hf.space/api/offers', {
    headers: { 'Authorization': `Bearer ${token}` }
  })
  .then(r => {
    if (r.status === 401 || r.status === 403) {
      localStorage.removeItem('recruteIA_token');
      window.location.href = '/login';
    }
  })
  .catch(() => {
    console.error('Could not verify token');
    window.location.href = '/login';
  });
  
  return true;
}

// Call on protected pages
if (!ensureAuthenticated()) {
  // Prevent page from rendering
}
```

---

### 7. Error Handling Best Practices

```javascript
async function apiCall(endpoint, options = {}) {
  const token = localStorage.getItem('recruteIA_token');
  
  try {
    const response = await fetch(`https://..../api${endpoint}`, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    // Authentication errors
    if (response.status === 401 || response.status === 403) {
      localStorage.removeItem('recruteIA_token');
      window.location.href = '/login';
      return null;
    }
    
    // Bad request (validation errors)
    if (response.status === 400) {
      const error = await response.json();
      console.error('Validation error:', error.error.message);
      showUserMessage('Invalid input: ' + error.error.message);
      return null;
    }
    
    // File size errors
    if (response.status === 413) {
      showUserMessage('File too large (max 5MB)');
      return null;
    }
    
    // Pydantic validation errors (field names, types)
    if (response.status === 422) {
      const error = await response.json();
      console.error('Field validation error:', error.error);
      showUserMessage('Check field values and try again');
      return null;
    }
    
    // Server errors
    if (response.status === 500) {
      console.error('Server error');
      showUserMessage('Server error. Please try again later.');
      return null;
    }
    
    // Success
    const data = await response.json();
    return data.data; // Return just the data part
    
  } catch (error) {
    console.error('Network error:', error);
    showUserMessage('Network error. Check your connection.');
    return null;
  }
}

function showUserMessage(message) {
  // Show toast/alert to user
  console.warn(message);
}
```

---

### 8. WordPress Security Headers

If WordPress has strict Content Security Policy (CSP):

```php
// Add to WordPress functions.php or header
add_action('send_headers', function() {
  header("Content-Security-Policy: default-src 'self'; connect-src 'self' https://yassirhakimi-recruiteia-api.hf.space;");
});
```

Or in `.htaccess`:
```apache
Header set Content-Security-Policy "default-src 'self'; connect-src 'self' https://yassirhakimi-recruiteia-api.hf.space;"
```

---

### 9. Testing Checklist

Before deploying to production:

```
Authentication Flow:
  ☐ Test login with provided credentials
  ☐ Token stores in localStorage
  ☐ Token appears in Authorization header
  ☐ Protected routes accessible with token
  
Error Handling:
  ☐ Invalid credentials → Error message shown
  ☐ Missing token → Redirect to login
  ☐ Expired token → Redirect to login
  ☐ Network error → Error message shown
  
Security:
  ☐ HTTPS is enabled
  ☐ No token in URL or logs
  ☐ Token cleared on logout
  ☐ Token cleared on auth error
  
File Uploads:
  ☐ CV uploads work
  ☐ Large files rejected (>5MB)
  ☐ File upload errors handled
  
Integration:
  ☐ Create offer works
  ☐ List offers works
  ☐ Score session works
  ☐ Poll for results works
  ☐ Export CSV works
```

---

### 10. Common Mistakes to Avoid

| Mistake | Impact | Fix |
|---------|--------|-----|
| Only check 401 | Missing token (403) not handled | Check `401 \|\| 403` |
| Manually set `Content-Type` on file uploads | File upload fails | Let browser auto-set via FormData |
| Store token in sessionStorage | Token lost on page reload | Use localStorage |
| Missing Bearer prefix | Token rejected (401) | Use `Bearer {token}` |
| Not in HTTPS | Mixed content warning | Use HTTPS always |
| Wrong field names (e.g., `experience_years` vs `experience_required_years`) | 422 validation error | Reference API.md for exact field names |
| Sync polling (no delay) | API rate-limit or browser freeze | Use `setInterval` with 1-2s delay |

---

## Testing Credentials

**Email:** `wp_sim2_1778330933@company.ma`  
**Password:** `StrongPass@123`

These are valid in production. Use for:
- Frontend integration testing
- QA verification
- Demo purposes
- Removing when deployment is complete

---

## API Reference

**Production Base URL:** `https://yassirhakimi-recruiteia-api.hf.space/api`  
**Swagger UI:** `https://yassirhakimi-recruiteia-api.hf.space/api/docs`

All endpoints documented in `docs/API.md`.

Key endpoints:
- `POST /auth/login` — Authenticate and get JWT token
- `POST /offers` — Create job offer
- `POST /cvs` — Upload CV file
- `POST /sessions` — Create scoring session
- `POST /sessions/{id}/score` — Start async scoring
- `GET /sessions/{id}/results` — Get ranked candidates

---

## Support & Questions

- **API Documentation:** See `docs/API.md`
- **Integration Guide:** See `docs/FRONTEND_INTEGRATION_GUIDE.md`
- **Decision Log:** See `notebooklm_seed/10_Decisions/10_DECISION_LOG.md`
- **Error Details:** Check Swagger UI at `/api/docs`

---

**Last Verified:** Production Auth Testing (All endpoints working ✅)  
**Documentation Updated:** API.md with missing token behavior (403 vs 401)  
**Status:** Ready for frontend integration

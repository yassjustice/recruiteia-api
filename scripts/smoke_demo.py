"""
smoke_demo.py — End-to-end smoke test for RecruteIA demo.

Runs the canonical demo flow against the configured base URL and asserts
each step passes. Designed to run 2–3 minutes before the jury presentation
(pre-warm + functional check) and as a post-deployment sanity check.

Usage (from brief/recruitment-ai/):
    # Minimal — uses live HF Space with env credentials:
    python scripts/smoke_demo.py

    # Against local backend:
    RECRUTE_BASE_URL=http://localhost:8000/api python scripts/smoke_demo.py

    # Full demo seed (creates a completed session):
    RECRUTE_SEED=1 python scripts/smoke_demo.py

Environment variables:
    RECRUTE_BASE_URL   API base URL (default: HF Space)
    RECRUTE_EMAIL      Demo account email  (default: demo@recruteai.test)
    RECRUTE_PASSWORD   Demo account password (default: DemoRecruteIA2026!)
    RECRUTE_SEED       If set to "1", creates a fresh session (seed mode)
"""

import os
import sys
import time
import json
import requests
from pathlib import Path

# Make console output UTF-8 safe on Windows (cp1252 cannot encode ✅/❌/→)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

BASE_URL = os.environ.get("RECRUTE_BASE_URL", "https://yassirhakimi-recruiteia-api.hf.space/api")
EMAIL = os.environ.get("RECRUTE_EMAIL", "demo@recruteai.test")
PASSWORD = os.environ.get("RECRUTE_PASSWORD", "DemoRecruteIA2026!")
SEED_MODE = os.environ.get("RECRUTE_SEED", "") == "1"

DEMO_DIR = Path(__file__).parent.parent / "data" / "demo"
JOB_OFFER_FILE = DEMO_DIR / "job_offer_backend_python.txt"
CV_FILES = list(DEMO_DIR.glob("cv_*.pdf"))

TIMEOUT = 30  # seconds per request
SCORE_POLL_MAX = 120  # seconds to wait for scoring to complete
SCORE_POLL_INTERVAL = 5

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

_token = None
_session = requests.Session()
_results = []


def step(name: str):
    print(f"\n{'='*60}\n  STEP: {name}\n{'='*60}")


def ok(msg: str):
    print(f"  {GREEN}✅ {msg}{RESET}")
    _results.append(("PASS", msg))


def fail(msg: str, detail: str = ""):
    print(f"  {RED}❌ {msg}{RESET}")
    if detail:
        print(f"     {detail}")
    _results.append(("FAIL", msg))


def warn(msg: str):
    print(f"  {YELLOW}⚠️  {msg}{RESET}")


def api(method: str, path: str, *, auth: bool = True, **kwargs) -> requests.Response:
    url = f"{BASE_URL}/{path.lstrip('/')}"
    headers = kwargs.pop("headers", {})
    if auth and _token:
        headers["Authorization"] = f"Bearer {_token}"
    resp = _session.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)
    return resp


# ── Steps ─────────────────────────────────────────────────────────────────

def test_health():
    step("Health check (pre-warm)")
    t0 = time.time()
    try:
        r = api("GET", "/health", auth=False)
        elapsed = time.time() - t0
        if r.status_code == 200:
            ok(f"GET /health → 200 ({elapsed:.1f}s)")
            if elapsed > 20:
                warn(f"Cold start detected ({elapsed:.0f}s) — wait ~60s before re-running")
        else:
            fail(f"GET /health → {r.status_code}", r.text[:200])
    except Exception as e:
        fail("GET /health failed", str(e))


def test_register_or_login():
    global _token
    step("Auth — login or register")
    # Try login first
    r = api("POST", "/auth/login", auth=False, json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 200:
        data = r.json().get("data", {})
        _token = data.get("access_token")
        ok(f"Login → 200  |  user: {data.get('user', {}).get('email', '?')}")
        return
    # Try register
    warn(f"Login returned {r.status_code} — trying register")
    r2 = api("POST", "/auth/register", auth=False, json={
        "email": EMAIL, "password": PASSWORD, "full_name": "Demo RecruteIA"
    })
    if r2.status_code in (200, 201):
        # Now login
        r3 = api("POST", "/auth/login", auth=False, json={"email": EMAIL, "password": PASSWORD})
        if r3.status_code == 200:
            _token = r3.json().get("data", {}).get("access_token")
            ok(f"Register + Login → 200")
        else:
            fail("Login after register failed", r3.text[:200])
    else:
        fail(f"Register → {r2.status_code}", r2.text[:200])


def test_offer_extract() -> dict | None:
    step("Module 2 — Offer extraction")
    if not JOB_OFFER_FILE.exists():
        fail(f"Job offer file not found: {JOB_OFFER_FILE}")
        return None
    jd_text = JOB_OFFER_FILE.read_text(encoding="utf-8")
    r = api("POST", "/offers/extract", json={"text": jd_text})
    if r.status_code == 200:
        offer = r.json().get("data", {})
        skills = offer.get("required_skills", [])
        critical = offer.get("critical_skills", [])
        ok(f"POST /offers/extract → 200  |  {len(skills)} skills, {len(critical)} critical")
        return offer
    else:
        fail(f"POST /offers/extract → {r.status_code}", r.text[:300])
        return None


def test_create_offer(extracted: dict) -> str | None:
    step("Create and save offer")
    r = api("POST", "/offers", json=extracted)
    if r.status_code in (200, 201):
        offer_id = r.json().get("data", {}).get("id")
        ok(f"POST /offers → {r.status_code}  |  id: {offer_id}")
        return offer_id
    else:
        fail(f"POST /offers → {r.status_code}", r.text[:200])
        return None


def test_upload_cvs() -> list[str]:
    step("Module 1 — CV upload and extraction")
    if not CV_FILES:
        fail(f"No CV PDFs found in {DEMO_DIR}")
        return []
    cv_ids = []
    for cv_file in CV_FILES[:3]:  # upload up to 3
        with open(cv_file, "rb") as f:
            r = api("POST", "/cvs", files={"file": (cv_file.name, f, "application/pdf")})
        if r.status_code in (200, 201):
            data = r.json().get("data", {})
            cv_id = data.get("id")
            name = data.get("candidate_name", "?")
            status = data.get("extraction_status", "?")
            ok(f"  {cv_file.name} → id={cv_id}  name={name}  status={status}")
            cv_ids.append(cv_id)
        else:
            fail(f"  {cv_file.name} → {r.status_code}", r.text[:200])
    return cv_ids


def test_create_session(offer_id: str, cv_ids: list[str]) -> str | None:
    step("Create screening session")
    payload = {
        "name": "Demo Session — Jury Presentation",
        "offer_id": offer_id,
        "cv_ids": cv_ids,
        "weights": {
            "skills_match": 0.30,
            "experience_relevance": 0.22,
            "achievements": 0.15,
            "language_quality": 0.10,
            "language_match": 0.10,
            "education": 0.08,
            "location": 0.05,
        }
    }
    r = api("POST", "/sessions", json=payload)
    if r.status_code in (200, 201):
        session_id = r.json().get("data", {}).get("id")
        ok(f"POST /sessions → {r.status_code}  |  id: {session_id}")
        return session_id
    else:
        fail(f"POST /sessions → {r.status_code}", r.text[:300])
        return None


def test_score_and_poll(session_id: str) -> bool:
    step("Module 3 — Score and poll to completion")
    r = api("POST", f"/sessions/{session_id}/score")
    if r.status_code not in (200, 201, 202):
        fail(f"POST /sessions/{session_id}/score → {r.status_code}", r.text[:200])
        return False
    ok(f"Scoring started → {r.status_code}")

    deadline = time.time() + SCORE_POLL_MAX
    while time.time() < deadline:
        time.sleep(SCORE_POLL_INTERVAL)
        r = api("GET", f"/sessions/{session_id}")
        if r.status_code == 200:
            status = r.json().get("data", {}).get("status", "?")
            print(f"  ... polling status: {status}", end="\r")
            if status == "completed":
                ok(f"\n  Session status → completed")
                return True
            elif status == "failed":
                fail("Session scoring failed", r.json().get("data", {}).get("error", ""))
                return False
        else:
            warn(f"Poll returned {r.status_code}")

    fail(f"Scoring did not complete within {SCORE_POLL_MAX}s")
    return False


def test_results(session_id: str):
    step("Fetch and validate results")
    r = api("GET", f"/sessions/{session_id}/results")
    if r.status_code == 200:
        raw = r.json().get("data", [])
        # API returns either a list directly or {"status": ..., "results": [...]}
        if isinstance(raw, list):
            results = raw
        elif isinstance(raw, dict):
            results = raw.get("results", [])
        else:
            results = []
        if results:
            ok(f"GET /results → 200  |  {len(results)} candidates ranked")
            for row in results[:3]:
                print(f"    #{row.get('rank','-')} {row.get('candidate_name','?'):20s}  "
                      f"score={row.get('total_score',0):.3f}  "
                      f"band={row.get('recommendation','?')}")
        else:
            fail("GET /results → 200 but results list is empty")
    else:
        fail(f"GET /results → {r.status_code}", r.text[:200])


def test_export(session_id: str):
    step("CSV export")
    r = api("GET", f"/sessions/{session_id}/export")
    if r.status_code == 200 and "text/csv" in r.headers.get("Content-Type", ""):
        lines = r.text.strip().split("\n")
        ok(f"GET /export → 200  |  CSV: {len(lines)} lines (header + {len(lines)-1} rows)")
    elif r.status_code == 200:
        ok(f"GET /export → 200 (content-type: {r.headers.get('Content-Type', '?')})")
    else:
        fail(f"GET /export → {r.status_code}", r.text[:200])


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'#'*60}")
    print(f"  RecruteIA Smoke Test  —  {BASE_URL}")
    print(f"  Mode: {'SEED (creates new session)' if SEED_MODE else 'SMOKE (verify existing)'}")
    print(f"{'#'*60}")

    test_health()
    if not any(r[0] == "FAIL" for r in _results):
        test_register_or_login()

    if _token:
        extracted = test_offer_extract()
        if extracted:
            offer_id = test_create_offer(extracted)
            if offer_id:
                cv_ids = test_upload_cvs()
                if cv_ids:
                    session_id = test_create_session(offer_id, cv_ids)
                    if session_id:
                        done = test_score_and_poll(session_id)
                        if done:
                            test_results(session_id)
                            test_export(session_id)

    # Summary
    print(f"\n{'='*60}")
    passed = sum(1 for r in _results if r[0] == "PASS")
    failed = sum(1 for r in _results if r[0] == "FAIL")
    print(f"  RESULTS: {passed} passed / {failed} failed")
    if failed == 0:
        print(f"  {GREEN}ALL TESTS PASSED — demo is ready!{RESET}")
    else:
        print(f"  {RED}FAILURES — fix before demo day{RESET}")
        for tag, msg in _results:
            if tag == "FAIL":
                print(f"    ❌ {msg}")
    print(f"{'='*60}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

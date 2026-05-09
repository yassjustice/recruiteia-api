"""
RecruteIA Real-World Stress Testing Suite
==========================================

Comprehensive stress testing with:
- Real PDF CV generation & uploads
- Concurrent batch processing
- Database performance measurement
- All 3 main functionalities under load
"""

import requests
import json
import time
import sys
from io import BytesIO
from typing import Dict, List, Any, Tuple
import asyncio
import random
from datetime import datetime

BASE_URL = "https://yassirhakimi-recruiteia-api.hf.space/api"

# Test credentials  
TEST_EMAIL = "stress_test_recruiter@company.ma"
TEST_PASSWORD = "StressTest@2026!Secure"

# ────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ────────────────────────────────────────────────────────────────────────────

def create_text_pdf(content: str, size_bytes: int = 100000) -> bytes:
    """Create a minimal PDF from text (no reportlab needed)."""
    # Simple PDF template
    pdf_header = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< >>
stream
BT
/F1 12 Tf
50 700 Td
"""
    pdf_footer = b"""ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000229 00000 n
0000000322 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
999
%%EOF
"""
    
    # Embed content
    content_bytes = content.encode('utf-8')
    pdf = pdf_header + content_bytes + pdf_footer
    
    # Pad to approximate size
    if len(pdf) < size_bytes:
        pdf += b'\n% ' + b'x' * (size_bytes - len(pdf) - 5)
    
    return pdf[:size_bytes]


def generate_realistic_cv() -> str:
    """Generate a realistic CV text."""
    roles = ["Senior Developer", "Data Scientist", "DevOps Engineer", "Product Manager", "QA Engineer"]
    companies = ["TechCorp", "StartupXYZ", "BigTech Inc", "CloudFirst", "DataSolutions"]
    skills = ["Python", "JavaScript", "SQL", "Docker", "AWS", "React", "FastAPI", "PostgreSQL"]
    
    role = random.choice(roles)
    
    return f"""
PROFESSIONAL RESUME

{random.choice(['Jean', 'Marie', 'Ahmed', 'Yassir', 'Fatima'])} {random.choice(['Dupont', 'Martin', 'Alaoui', 'Hassan', 'Singh'])}
Email: candidate_{random.randint(1000, 9999)}@example.ma
Phone: +212 6{random.randint(10000000, 99999999)}
Location: Casablanca, Morocco

PROFESSIONAL SUMMARY
{random.randint(2, 15)} years of experience as a {role} with expertise in {', '.join(random.sample(skills, 3))}.
Proven track record of delivering high-quality solutions and leading teams.

WORK EXPERIENCE
20{random.randint(15, 22)} - Present: {role} at {random.choice(companies)}
- Led implementation of {random.choice(['microservices', 'cloud migration', 'data pipeline'])}
- Improved performance by {random.randint(20, 80)}%
- Managed team of {random.randint(1, 10)} engineers
- Technologies: {', '.join(random.sample(skills, 3))}

20{random.randint(10, 14)} - 20{random.randint(15, 21)}: Mid-Level {role} at {random.choice(companies)}
- Developed and maintained {random.choice(['APIs', 'dashboards', 'infrastructure'])}
- Collaborated with cross-functional teams
- Mentored junior engineers

EDUCATION
Bachelor's degree in Computer Science
University of Casablanca, 20{random.randint(12, 18)}

SKILLS
Languages: {', '.join(random.sample(['Python', 'JavaScript', 'Go', 'Rust', 'Java'], 3))}
Databases: {', '.join(random.sample(['PostgreSQL', 'MongoDB', 'Redis', 'Cassandra'], 2))}
Cloud: {', '.join(random.sample(['AWS', 'GCP', 'Azure'], 2))}
Tools: {', '.join(random.sample(['Docker', 'Kubernetes', 'Git', 'CI/CD', 'Terraform'], 3))}

CERTIFICATIONS
AWS Certified Solutions Architect
Kubernetes Certified Application Developer

LANGUAGES
French: Native
English: Fluent
Arabic: Professional Working Proficiency
"""


class StressTestRunner:
    """Stress test orchestrator."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.user_id = None
        self.results = {}
    
    def _headers(self):
        """Build headers."""
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h
    
    def setup(self):
        """Setup: register and login."""
        print("\n[SETUP] Registering test user...")
        
        # Register
        resp = self.session.post(
            f"{self.base_url}/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "full_name": "Stress Test Recruiter",
                "role": "recruiter"
            },
            headers={"Content-Type": "application/json"}
        )
        
        if resp.status_code == 200:
            self.user_id = resp.json()["data"]["id"]
            print(f"  Registered: User ID {self.user_id}")
        elif "already registered" in resp.text.lower():
            print(f"  User already exists (reusing)")
        else:
            print(f"  Error: {resp.status_code} {resp.text[:100]}")
            return False
        
        # Login
        print("\n[SETUP] Logging in...")
        resp = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        
        if resp.status_code == 200:
            self.token = resp.json()["data"]["access_token"]
            print(f"  Logged in: Token {self.token[:20]}...")
            return True
        else:
            print(f"  Login failed: {resp.status_code}")
            return False
    
    def test_jd_extraction(self):
        """Test JD extraction under load."""
        print("\n" + "="*70)
        print("TEST 1: JD Extraction (Load Test)")
        print("="*70)
        
        jds = [
            "Senior Python Developer, 3+ years, must know FastAPI and PostgreSQL",
            "Data Scientist position, ML experience required, Python and R skills essential",
            "DevOps Engineer, Kubernetes and Docker expertise, AWS certified preferred",
            "Full-stack Developer, React and Node.js, 5+ years experience"
        ]
        
        results = []
        times = []
        
        for i, jd_text in enumerate(jds * 3):  # 12 tests
            start = time.time()
            
            resp = self.session.post(
                f"{self.base_url}/offers/extract",
                json={"text": jd_text, "lang": "fr"},
                headers=self._headers()
            )
            
            elapsed = time.time() - start
            times.append(elapsed)
            
            if resp.status_code == 200:
                data = resp.json()["data"]
                results.append({
                    "index": i,
                    "status": "OK",
                    "duration": elapsed,
                    "title": data.get("title", "")[:30],
                    "skills": len(data.get("required_skills", []))
                })
                print(f"  [{i+1:2d}/12] {elapsed:.2f}s - {data.get('title', '')[:40]}")
            else:
                results.append({
                    "index": i,
                    "status": "FAIL",
                    "error": resp.status_code
                })
                print(f"  [{i+1:2d}/12] FAIL - {resp.status_code}")
        
        self.results["jd_extraction"] = {
            "total": len(results),
            "passed": sum(1 for r in results if r["status"] == "OK"),
            "avg_time": sum(times) / len(times) if times else 0,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "results": results
        }
    
    def test_cv_uploads(self):
        """Test CV upload with real PDF generation."""
        print("\n" + "="*70)
        print("TEST 2: CV Upload & Extraction (Real PDFs)")
        print("="*70)
        
        num_cvs = 5
        results = []
        times = []
        cv_ids = []
        
        for i in range(num_cvs):
            print(f"\n  [{i+1}/{num_cvs}] Generating and uploading CV...")
            
            # Generate CV
            cv_text = generate_realistic_cv()
            pdf_data = create_text_pdf(cv_text, size_bytes=random.randint(50000, 200000))
            
            start = time.time()
            
            # Upload
            files = {"file": ("cv_{:03d}.pdf".format(i), pdf_data, "application/pdf")}
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            resp = self.session.post(
                f"{self.base_url}/cvs",
                files=files,
                headers=headers
            )
            
            elapsed = time.time() - start
            times.append(elapsed)
            
            if resp.status_code == 200:
                data = resp.json()["data"]
                cv_id = data.get("id")
                cv_ids.append(cv_id)
                
                results.append({
                    "index": i,
                    "status": "OK",
                    "cv_id": cv_id,
                    "duration": elapsed,
                    "name": data.get("candidate_name", "")[:30],
                    "skills": len(data.get("skills", []))
                })
                
                print(f"    Uploaded: CV ID {cv_id}, {data.get('candidate_name', 'N/A')}")
                print(f"    Extracted {len(data.get('skills', []))} skills, confidence {data.get('confidence_score', 0):.0%}")
            else:
                results.append({
                    "index": i,
                    "status": "FAIL",
                    "error": resp.status_code,
                    "duration": elapsed
                })
                print(f"    Upload failed: {resp.status_code}")
        
        self.results["cv_uploads"] = {
            "total": num_cvs,
            "passed": sum(1 for r in results if r["status"] == "OK"),
            "avg_time": sum(times) / len(times) if times else 0,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "cv_ids": cv_ids,
            "results": results
        }
    
    def test_scoring(self):
        """Test scoring with uploaded CVs."""
        print("\n" + "="*70)
        print("TEST 3: Session Creation & Scoring (Real Database)")
        print("="*70)
        
        # Get offer
        print("\n  Retrieving job offer...")
        resp = self.session.get(
            f"{self.base_url}/offers",
            headers=self._headers()
        )
        
        offers = resp.json()["data"] if resp.status_code == 200 else []
        if not offers:
            print("  No job offers found, creating one...")
            # Create an offer
            resp = self.session.post(
                f"{self.base_url}/offers",
                json={
                    "title": "Senior Python Developer",
                    "description": "Backend development role",
                    "required_skills": ["Python", "SQL", "FastAPI"],
                    "critical_skills": ["Python"],
                    "experience_required_years": 3,
                    "education_required": "Bachelor",
                    "location": "Casablanca",
                    "job_type": "CDI",
                    "domain": "IT"
                },
                headers=self._headers()
            )
            if resp.status_code == 200:
                offer_id = resp.json()["data"]["id"]
            else:
                print(f"  Failed to create offer: {resp.status_code}")
                return
        else:
            offer_id = offers[0]["id"]
        
        print(f"  Using offer ID {offer_id}")
        
        # Get CVs
        print("\n  Retrieving uploaded CVs...")
        resp = self.session.get(
            f"{self.base_url}/cvs",
            headers=self._headers()
        )
        
        cvs = resp.json()["data"] if resp.status_code == 200 else []
        cv_ids = [cv["id"] for cv in cvs[:5]]  # Use up to 5 CVs
        
        if not cv_ids:
            print("  No CVs available for scoring")
            return
        
        print(f"  Found {len(cv_ids)} CVs")
        
        # Create session
        print("\n  Creating screening session...")
        start = time.time()
        
        resp = self.session.post(
            f"{self.base_url}/sessions",
            json={
                "name": f"Stress Test Session {datetime.now().strftime('%H:%M:%S')}",
                "job_offer_id": offer_id,
                "cv_ids": cv_ids,
                "weights": {
                    "skills": 0.35,
                    "experience": 0.25,
                    "education": 0.15,
                    "language": 0.15,
                    "location": 0.10
                }
            },
            headers=self._headers()
        )
        
        if resp.status_code != 200:
            print(f"  Failed to create session: {resp.status_code}")
            return
        
        session_id = resp.json()["data"]["id"]
        print(f"  Session created: ID {session_id}")
        
        # Start scoring
        print(f"\n  Starting async scoring ({len(cv_ids)} CVs)...")
        resp = self.session.post(
            f"{self.base_url}/sessions/{session_id}/score",
            json={},
            headers=self._headers()
        )
        
        if resp.status_code != 200:
            print(f"  Failed to start scoring: {resp.status_code}")
            return
        
        # Poll for completion
        print("  Polling for completion...")
        polling_times = []
        max_polls = 30
        
        for poll_num in range(max_polls):
            poll_start = time.time()
            
            resp = self.session.get(
                f"{self.base_url}/sessions/{session_id}",
                headers=self._headers()
            )
            
            if resp.status_code == 200:
                session_data = resp.json()["data"]
                status = session_data.get("status")
                processed = session_data.get("processed_cvs", 0)
                total = session_data.get("total_cvs", 0)
                
                polling_times.append(time.time() - poll_start)
                
                print(f"    Poll {poll_num+1}: {status} ({processed}/{total} CVs)")
                
                if status == "completed":
                    elapsed_total = time.time() - start
                    print(f"  Scoring completed in {elapsed_total:.2f}s")
                    
                    # Get results
                    resp = self.session.get(
                        f"{self.base_url}/sessions/{session_id}/results",
                        headers=self._headers()
                    )
                    
                    if resp.status_code == 200:
                        results_list = resp.json()["data"]
                        if results_list:
                            top = results_list[0]
                            print(f"  Top candidate: {top.get('candidate_name', 'N/A')}, Score {top.get('final_score', 0):.1%}")
                    
                    self.results["scoring"] = {
                        "session_id": session_id,
                        "status": "completed",
                        "num_cvs": len(cv_ids),
                        "total_time": elapsed_total,
                        "polling_rounds": poll_num + 1,
                        "avg_poll_time": sum(polling_times) / len(polling_times) if polling_times else 0
                    }
                    return
                
                elif status == "failed":
                    print(f"  Scoring failed")
                    self.results["scoring"] = {"status": "failed"}
                    return
            
            time.sleep(2)
        
        print(f"  Timeout: Scoring did not complete after {max_polls * 2}s")
        self.results["scoring"] = {"status": "timeout"}
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print("STRESS TEST SUMMARY")
        print("="*70)
        
        print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base URL: {self.base_url}")
        print()
        
        for test_name, test_data in self.results.items():
            print(f"\n{test_name.upper()}")
            print("-" * 40)
            
            if "avg_time" in test_data:
                passed = test_data.get("passed", 0)
                total = test_data.get("total", 0)
                print(f"  Passed: {passed}/{total}")
                print(f"  Avg time: {test_data.get('avg_time', 0):.2f}s")
                print(f"  Min/Max: {test_data.get('min_time', 0):.2f}s / {test_data.get('max_time', 0):.2f}s")
            elif "status" in test_data:
                print(f"  Status: {test_data.get('status')}")
                if "total_time" in test_data:
                    print(f"  Total time: {test_data.get('total_time'):.2f}s")
                    print(f"  CVs processed: {test_data.get('num_cvs')}")
        
        # Save full report
        report_path = "STRESS_TEST_REAL_REPORT.json"
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✓ Report saved: {report_path}")


def main():
    """Main entry point."""
    print("="*70)
    print("  RecruteIA Real-World Stress Testing")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}")
    
    runner = StressTestRunner(BASE_URL)
    
    if not runner.setup():
        print("\nSetup failed, exiting")
        return
    
    # Run tests
    runner.test_jd_extraction()
    runner.test_cv_uploads()
    runner.test_scoring()
    
    runner.print_summary()


if __name__ == "__main__":
    main()

"""
seed_demo_account.py — Populate the live demo account with a polished, varied
set of candidates and one showpiece scored session for the jury demo.

- Generates 4 NEW distinct synthetic CVs (fully fictional) to add ranking variety.
- Uploads only the new CVs (avoids re-duplicating the original 3).
- Creates a clearly-named offer + one completed "showpiece" session that mixes the
  new candidates with the existing Amira/Mehdi/Sofia for a clean 7-candidate ranking.

Usage (from brief/recruitment-ai/):
    python scripts/seed_demo_account.py
Env overrides: RECRUTE_BASE_URL, RECRUTE_EMAIL, RECRUTE_PASSWORD
"""
import os
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

BASE = os.environ.get("RECRUTE_BASE_URL", "https://yassirhakimi-recruiteia-api.hf.space/api")
EMAIL = os.environ.get("RECRUTE_EMAIL", "demo@recruteai.test")
PASSWORD = os.environ.get("RECRUTE_PASSWORD", "DemoRecruteIA2026!")
DEMO_DIR = Path(__file__).parent.parent / "data" / "demo"
DEMO_DIR.mkdir(parents=True, exist_ok=True)
W, H = A4

DEFAULT_WEIGHTS = {
    "skills_match": 0.30, "experience_relevance": 0.22, "achievements": 0.15,
    "language_quality": 0.10, "language_match": 0.10, "education": 0.08, "location": 0.05,
}

JD_TEXT = (
    "Nous recherchons un Développeur Backend Python Senior (4+ ans d'expérience) pour rejoindre "
    "notre équipe à Casablanca. Missions : concevoir et déployer des APIs robustes avec FastAPI, "
    "modéliser et optimiser des bases de données PostgreSQL, écrire du code maintenable et testé, "
    "mettre en place des pipelines CI/CD et conteneuriser les services avec Docker. "
    "Compétences indispensables : Python, FastAPI, SQL/PostgreSQL, REST API, Git. "
    "Atouts : Docker, Redis, Linux, tests automatisés. "
    "Langues : Français courant, Anglais professionnel. Diplôme Bac+5 en informatique souhaité."
)


def _draw(path, lines):
    c = canvas.Canvas(str(path), pagesize=A4)
    y = 780
    for text, size, bold in lines:
        if y < 60:
            c.showPage(); y = 780
        if text.startswith("---"):
            c.setStrokeColorRGB(0.3, 0.3, 0.3); c.line(2 * cm, y + 2, W - 2 * cm, y + 2); y -= 8; continue
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(2 * cm, y, text); y -= size * 1.5
    c.save()
    print(f"  generated {path.name}")


NEW_CVS = {
    "cv_nadia_cherkaoui.pdf": [
        ("Nadia Cherkaoui", 18, True),
        ("Ingénieure Full-Stack Senior | 5 ans d'expérience", 11, False),
        ("nadia.cherkaoui@demo.recruteai.test  |  +212 6 XX XX XX XX  |  Casablanca", 9, False),
        ("---", 0, False), ("COMPÉTENCES", 11, True),
        ("Python, FastAPI, Django, React, Node.js, SQL, PostgreSQL, Redis, Docker, Git, CI/CD", 10, False),
        ("REST API, GitHub Actions, Linux, tests pytest, TypeScript", 10, False),
        ("Langues : Français (natif), Anglais (C1), Arabe (natif)", 10, False),
        ("---", 0, False), ("EXPÉRIENCE PROFESSIONNELLE", 11, True),
        ("Lead Développeuse Full-Stack — FinTech Casablanca (2021–2026)", 10, True),
        ("• Architecturé une plateforme FastAPI + React servant 50 000 utilisateurs", 9, False),
        ("• Réduit la latence API de 35% via optimisation PostgreSQL et cache Redis", 9, False),
        ("• Mis en place CI/CD Docker réduisant les déploiements de 2h à 10 min", 9, False),
        ("Développeuse Backend — SoftMaroc (2019–2021)", 10, True),
        ("• Construit 8 microservices REST en Python et migré une API Flask vers FastAPI", 9, False),
        ("---", 0, False), ("FORMATION", 11, True),
        ("Diplôme d'Ingénieur Informatique — ENSIAS, Rabat (2019)", 10, False),
        ("---", 0, False), ("PROJETS", 11, True),
        ("• Système de paiement temps réel (FastAPI + PostgreSQL + Redis) — 99.9% uptime", 9, False),
    ],
    "cv_yassine_elidrissi.pdf": [
        ("Yassine El Idrissi", 18, True),
        ("Data Scientist | 3 ans d'expérience", 11, False),
        ("yassine.elidrissi@demo.recruteai.test  |  Rabat, Maroc", 9, False),
        ("---", 0, False), ("COMPÉTENCES", 11, True),
        ("Python, Pandas, NumPy, Scikit-learn, Machine Learning, SQL, Jupyter, Matplotlib", 10, False),
        ("TensorFlow (bases), Git, statistiques, visualisation de données", 10, False),
        ("Langues : Français (natif), Anglais (B2), Arabe (natif)", 10, False),
        ("---", 0, False), ("EXPÉRIENCE", 11, True),
        ("Data Scientist — DataInsight Rabat (2023–2026)", 10, True),
        ("• Développé des modèles de prévision réduisant les ruptures de stock de 25%", 9, False),
        ("• Construit des pipelines de données Python traitant 1M+ lignes/jour", 9, False),
        ("Analyste Data Junior — TelecomMaroc (2022–2023)", 10, True),
        ("• Automatisé des rapports SQL hebdomadaires (gain de 10h/semaine)", 9, False),
        ("---", 0, False), ("FORMATION", 11, True),
        ("Master Data Science — FST Settat (2022)", 10, False),
        ("---", 0, False), ("PROJETS", 11, True),
        ("• Modèle de scoring crédit (Scikit-learn) — AUC 0.89", 9, False),
    ],
    "cv_khalid_berrada.pdf": [
        ("Khalid Berrada", 18, True),
        ("Ingénieur DevOps | 4 ans d'expérience", 11, False),
        ("khalid.berrada@demo.recruteai.test  |  Casablanca, Maroc", 9, False),
        ("---", 0, False), ("COMPÉTENCES", 11, True),
        ("Docker, Kubernetes, AWS, CI/CD, Terraform, Linux, Bash, Git, Jenkins, Nginx", 10, False),
        ("Python (scripting), SQL (bases), monitoring Prometheus/Grafana", 10, False),
        ("Langues : Français (natif), Anglais (C1), Arabe (natif)", 10, False),
        ("---", 0, False), ("EXPÉRIENCE", 11, True),
        ("Ingénieur DevOps — CloudOps Casablanca (2022–2026)", 10, True),
        ("• Géré des clusters Kubernetes en production (99.95% disponibilité)", 9, False),
        ("• Automatisé l'infrastructure AWS avec Terraform (déploiements 4× plus rapides)", 9, False),
        ("Administrateur Systèmes — HostMaroc (2021–2022)", 10, True),
        ("• Migré 30 serveurs vers des conteneurs Docker", 9, False),
        ("---", 0, False), ("FORMATION", 11, True),
        ("Licence Réseaux & Télécoms — EST Casablanca (2021)", 10, False),
    ],
    "cv_omar_tahiri.pdf": [
        ("Omar Tahiri", 18, True),
        ("Reconversion développement web | Débutant", 11, False),
        ("omar.tahiri@demo.recruteai.test  |  Fès, Maroc", 9, False),
        ("---", 0, False), ("COMPÉTENCES", 11, True),
        ("HTML, CSS, bases de JavaScript, WordPress, Excel, gestion de projet", 10, False),
        ("Langues : Français (natif), Anglais (A2), Arabe (natif)", 10, False),
        ("---", 0, False), ("EXPÉRIENCE", 11, True),
        ("Responsable Commercial — DistribFès (2018–2025)", 10, True),
        ("• Géré un portefeuille de 80 clients B2B", 9, False),
        ("• Suivi reconversion : bootcamp développement web (3 mois, 2025)", 9, False),
        ("---", 0, False), ("FORMATION", 11, True),
        ("Bootcamp Développement Web — Le Wagon (2025)", 10, False),
        ("Licence Commerce — Université Fès (2018)", 10, False),
        ("---", 0, False), ("PROJETS", 11, True),
        ("• Site vitrine WordPress pour une PME locale", 9, False),
    ],
}


def main():
    print(f"Seeding demo account on {BASE}")
    # 1. Generate the 4 new CVs
    print("\n[1/6] Generating 4 distinct synthetic CVs...")
    for fname, lines in NEW_CVS.items():
        _draw(DEMO_DIR / fname, lines)

    # 2. Login
    print("\n[2/6] Logging in...")
    r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=90)
    r.raise_for_status()
    token = r.json()["data"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    print("  ok")

    # 3. Upload the 4 new CVs
    print("\n[3/6] Uploading new CVs (extraction runs server-side)...")
    new_ids = []
    for fname in NEW_CVS:
        with open(DEMO_DIR / fname, "rb") as f:
            up = requests.post(f"{BASE}/cvs", headers=h,
                               files={"file": (fname, f, "application/pdf")}, timeout=120)
        d = up.json().get("data", {})
        cid, name = d.get("id"), d.get("candidate_name")
        if cid:
            new_ids.append(cid)
            print(f"  uploaded {fname} -> {name} ({d.get('extraction_status')})")
        else:
            print(f"  FAILED {fname}: {up.status_code} {up.text[:120]}")

    # 4. Pull existing distinct candidates (Amira / Mehdi / Sofia, first non-duplicate)
    print("\n[4/6] Selecting existing distinct candidates...")
    allcvs = requests.get(f"{BASE}/cvs", headers=h, timeout=90).json().get("data", [])
    wanted = ["Amira Benali", "Mehdi Zouaoui", "Sofia Alami"]
    existing_ids = []
    for name in wanted:
        match = next((c for c in allcvs if (c.get("candidate_name") or "").strip() == name
                      and not c.get("is_duplicate")), None) \
            or next((c for c in allcvs if (c.get("candidate_name") or "").strip() == name), None)
        if match:
            existing_ids.append(match["id"]); print(f"  + {name}")
    cv_ids = new_ids + existing_ids
    print(f"  showpiece session will rank {len(cv_ids)} candidates")

    # 5. Create the offer (extract -> save)
    print("\n[5/6] Creating offer 'Développeur Backend Python (Senior)'...")
    ext = requests.post(f"{BASE}/offers/extract", headers=h,
                        json={"text": JD_TEXT, "lang": "fr"}, timeout=120).json().get("data", {})
    payload = {**ext, "job_title": "Développeur Backend Python (Senior)",
               "title": "Développeur Backend Python (Senior)",
               "company_name": "TechRecruit Maroc", "company": "TechRecruit Maroc",
               "job_description": JD_TEXT}
    offer = requests.post(f"{BASE}/offers", headers=h, json=payload, timeout=90).json().get("data", {})
    offer_id = offer.get("id")
    print(f"  offer_id={offer_id}  critical_skills={ext.get('critical_skills')}")

    # 6. Create + score the showpiece session
    print("\n[6/6] Creating + scoring the showpiece session...")
    sess = requests.post(f"{BASE}/sessions", headers=h, json={
        "name": "Développeur Backend Python — Démo Jury",
        "offer_id": offer_id, "cv_ids": cv_ids, "weights": DEFAULT_WEIGHTS,
    }, timeout=90).json().get("data", {})
    sid = sess.get("id")
    requests.post(f"{BASE}/sessions/{sid}/score", headers=h, timeout=90)
    status = "processing"
    for _ in range(40):
        time.sleep(5)
        status = requests.get(f"{BASE}/sessions/{sid}", headers=h, timeout=90).json().get("data", {}).get("status")
        if status in ("completed", "failed"):
            break
    print(f"  session {sid} -> {status}")

    if status == "completed":
        rows = requests.get(f"{BASE}/sessions/{sid}/results", headers=h, timeout=90).json().get("data", [])
        print("\n  RANKING:")
        for row in rows:
            print(f"    #{row.get('rank')} {row.get('candidate_name'):<22} "
                  f"{row.get('final_score_pct')}%  {row.get('recommendation')}")

    stats = requests.get(f"{BASE}/stats/summary", headers=h, timeout=90).json().get("data", {})
    print(f"\nDONE. Account now: {stats}")
    print(f"Showpiece session URL path: /sessions/{sid}/results")


if __name__ == "__main__":
    main()

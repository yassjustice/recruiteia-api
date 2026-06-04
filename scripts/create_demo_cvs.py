"""
create_demo_cvs.py
Generate synthetic, fully anonymized demo CVs for RecruteIA demo day.
All names, emails, and data are purely fictional.

Usage: python scripts/create_demo_cvs.py
Output: brief/recruitment-ai/data/demo/cv_*.pdf
"""
import os
from pathlib import Path

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
except ImportError:
    print("ERROR: reportlab not installed. Run: pip install reportlab")
    raise

DEMO_DIR = Path(__file__).parent.parent / "data" / "demo"
DEMO_DIR.mkdir(parents=True, exist_ok=True)

W, H = A4  # 595 x 842 pts


def text_cv(c: canvas.Canvas, lines: list[tuple[str, int, bool]], y_start: float = 780) -> None:
    """Draw CV content onto canvas."""
    y = y_start
    c.setFont("Helvetica-Bold", 16)
    for text, size, bold in lines:
        if y < 60:
            c.showPage()
            y = 780
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        if text.startswith("---"):
            c.setStrokeColorRGB(0.3, 0.3, 0.3)
            c.line(2 * cm, y + 2, W - 2 * cm, y + 2)
            y -= 8
            continue
        c.drawString(2 * cm, y, text)
        y -= size * 1.5


# ── CV 1: Amira Benali — Strong Python/FastAPI developer ─────────────────
def cv_amira():
    path = DEMO_DIR / "cv_amira_benali.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    lines = [
        ("Amira Benali", 18, True),
        ("Développeuse Backend Python | 4 ans d'expérience", 11, False),
        ("amira.benali@demo.recruteai.test  |  +212 6 XX XX XX XX  |  Casablanca", 9, False),
        ("linkedin.com/in/amira-benali-demo  |  github.com/amira-benali-demo", 9, False),
        ("---", 0, False),
        ("COMPÉTENCES", 11, True),
        ("Python, FastAPI, Django REST, SQL, PostgreSQL, Redis, Docker, Git, Linux", 10, False),
        ("spaCy, Pandas, NumPy, Scikit-learn, REST APIs, CI/CD, GitHub Actions", 10, False),
        ("Langues : Français (natif), Anglais (C1), Arabe (natif)", 10, False),
        ("---", 0, False),
        ("EXPÉRIENCE PROFESSIONNELLE", 11, True),
        ("Développeuse Backend — TechRecruit Maroc (2022–2026)", 10, True),
        ("• Conçu et déployé 5 microservices FastAPI traitant 10 000 req/jour", 9, False),
        ("• Réduit le temps de réponse API de 40% via cache Redis et optimisation SQL", 9, False),
        ("• Mis en place un pipeline CI/CD réduisant les déploiements de 3h à 15 min", 9, False),
        ("• Encadré 2 développeurs juniors sur les bonnes pratiques REST", 9, False),
        ("Développeuse Junior — DataSoft (2021–2022)", 10, True),
        ("• Développé des scripts de scraping et d'analyse de données avec Pandas", 9, False),
        ("• Participé à la migration d'une API Flask vers FastAPI", 9, False),
        ("---", 0, False),
        ("FORMATION", 11, True),
        ("Master Informatique — FSSM, Marrakech (2021)", 10, False),
        ("Licence Informatique — Faculté des Sciences, Casablanca (2019)", 10, False),
        ("---", 0, False),
        ("PROJETS", 11, True),
        ("• API de recommandation de livres (FastAPI + PostgreSQL + Redis) — 500 utilisateurs actifs", 9, False),
        ("• Outil d'analyse de sentiment multilingue FR/AR/EN (spaCy + transformers)", 9, False),
    ]
    text_cv(c, lines)
    c.save()
    print(f"  Created: {path.name}")


# ── CV 2: Mehdi Zouaoui — Junior React/Node dev, medium profile ──────────
def cv_mehdi():
    path = DEMO_DIR / "cv_mehdi_zouaoui.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    lines = [
        ("Mehdi Zouaoui", 18, True),
        ("Développeur Full-Stack Junior | 1.5 ans d'expérience", 11, False),
        ("mehdi.zouaoui@demo.recruteai.test  |  Rabat, Maroc", 9, False),
        ("---", 0, False),
        ("COMPÉTENCES", 11, True),
        ("JavaScript, React, Node.js, Express, HTML5, CSS3, Git, REST APIs", 10, False),
        ("MongoDB (bases), SQL (bases), Docker (notions)", 10, False),
        ("Langues : Français (courant B2), Anglais (B1), Arabe (natif)", 10, False),
        ("---", 0, False),
        ("EXPÉRIENCE", 11, True),
        ("Développeur Frontend — AgenceWeb Rabat (2024–2026)", 10, True),
        ("• Intégré 3 interfaces React pour clients e-commerce (10% amélioration score Lighthouse)", 9, False),
        ("• Développé une API Node.js/Express pour la gestion de commandes", 9, False),
        ("Stage Développeur Web — StartupHub Casablanca (2023–2024)", 10, True),
        ("• Créé des composants React réutilisables pour le dashboard interne", 9, False),
        ("• Corrigé 15 bugs frontend identifiés lors des tests utilisateurs", 9, False),
        ("---", 0, False),
        ("FORMATION", 11, True),
        ("DUT Informatique — EST Salé (2023)", 10, False),
        ("---", 0, False),
        ("PROJETS", 11, True),
        ("• Blog personnel Next.js avec CMS headless — déployé sur Vercel", 9, False),
        ("• Application météo React avec API OpenWeatherMap", 9, False),
    ]
    text_cv(c, lines)
    c.save()
    print(f"  Created: {path.name}")


# ── CV 3: Sofia Alami — Marketing profile (weak match for dev role) ───────
def cv_sofia():
    path = DEMO_DIR / "cv_sofia_alami.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    lines = [
        ("Sofia Alami", 18, True),
        ("Responsable Marketing Digital | 3 ans d'expérience", 11, False),
        ("sofia.alami@demo.recruteai.test  |  Casablanca, Maroc", 9, False),
        ("---", 0, False),
        ("COMPÉTENCES", 11, True),
        ("Marketing digital, SEO/SEM, Google Analytics, Meta Ads, Canva, HubSpot", 10, False),
        ("WordPress, Notion, Excel avancé, PowerPoint", 10, False),
        ("Langues : Français (natif), Anglais (B1), Arabe (natif)", 10, False),
        ("---", 0, False),
        ("EXPÉRIENCE", 11, True),
        ("Responsable Marketing — E-commerce Casablanca (2023–2026)", 10, True),
        ("• Augmenté le trafic organique de 35% en 6 mois via stratégie SEO", 9, False),
        ("• Géré un budget Ads de 50K MAD/mois, ROAS moyen de 4.2×", 9, False),
        ("• Produit 50+ contenus/mois pour les réseaux sociaux", 9, False),
        ("Chargée Communication — ONG Casablanca (2022–2023)", 10, True),
        ("• Piloté la refonte du site WordPress (hausse de 20% des dons en ligne)", 9, False),
        ("---", 0, False),
        ("FORMATION", 11, True),
        ("Master Marketing & Communication — ENCG Casablanca (2022)", 10, False),
        ("---", 0, False),
        ("PROJETS", 11, True),
        ("• Lancement d'une boutique Shopify — 200 commandes en 3 mois", 9, False),
    ]
    text_cv(c, lines)
    c.save()
    print(f"  Created: {path.name}")


if __name__ == "__main__":
    print(f"Generating synthetic demo CVs in {DEMO_DIR}/")
    cv_amira()
    cv_mehdi()
    cv_sofia()
    print("Done.")

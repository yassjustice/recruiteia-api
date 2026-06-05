"""
CV Extraction Service
Converted from Brahim's resume_extractor.ipynb (pushed May 6, 2026)
Uses Groq API key from environment — never hardcoded.
"""
import re
import json
import pathlib
import warnings
import os
from typing import Optional
warnings.filterwarnings("default")

import pdfplumber
import spacy
import pandas as pd
from langdetect import detect as lang_detect, LangDetectException
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"
_groq_client: Optional[Groq] = None


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    return _groq_client

# ── Skill Taxonomy ─────────────────────────────────────────────────────────────
SKILL_TAXONOMY = {
    "Python": ["python", "python3", "python 3"],
    "JavaScript": ["javascript", "js", "ecmascript", "es6"],
    "Java": ["java", "java se", "java ee", "jdk"],
    "TypeScript": ["typescript", "ts"],
    "C++": ["c++", "cpp", "c plus plus"],
    "C#": ["c#", "csharp", "c sharp"],
    "PHP": ["php", "php7", "php8"],
    "Ruby": ["ruby", "ruby on rails", "ror"],
    "Go": ["go", "golang"],
    "Rust": ["rust"],
    "Swift": ["swift", "swiftui"],
    "Kotlin": ["kotlin"],
    "R": ["r language", "r programming", "rstudio"],
    "SQL": ["sql", "mysql", "postgresql", "postgres", "sqlite", "pl/sql", "t-sql"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3", "scss", "sass", "less"],
    "React": ["react", "reactjs", "react.js"],
    "Vue.js": ["vue", "vuejs", "vue.js"],
    "Angular": ["angular", "angularjs"],
    "Node.js": ["node", "nodejs", "node.js"],
    "Django": ["django"],
    "Flask": ["flask"],
    "FastAPI": ["fastapi"],
    "Spring": ["spring", "spring boot", "spring framework"],
    "Laravel": ["laravel"],
    "Docker": ["docker", "dockerfile"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure", "microsoft azure"],
    "GCP": ["gcp", "google cloud", "google cloud platform"],
    "Git": ["git", "github", "gitlab", "bitbucket"],
    "Linux": ["linux", "ubuntu", "debian", "centos"],
    "Machine Learning": ["machine learning", "ml", "apprentissage automatique"],
    "Deep Learning": ["deep learning", "dl", "apprentissage profond"],
    "TensorFlow": ["tensorflow", "tf"],
    "PyTorch": ["pytorch", "torch"],
    "Scikit-learn": ["scikit-learn", "sklearn"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    "Excel": ["excel", "microsoft excel", "ms excel"],
    "SAP": ["sap", "sap erp", "sap r3"],
    "Agile": ["agile", "scrum", "kanban"],
    "Jira": ["jira", "atlassian jira"],
}

ALIAS_TO_CANONICAL = {alias: canonical for canonical, aliases in SKILL_TAXONOMY.items() for alias in aliases}

# ── Section Patterns ───────────────────────────────────────────────────────────
SECTION_PATTERNS = {
    "profile": [r"(profil|profile|about\s*me|à\s*propos|summary|résumé\s*pro|professional\s*summary|objective|objectif|presentation|présentation)"],
    "experience": [r"(exp[eé]riences?\s*(professionnelles?)?|professional\s*experience|work\s*experience|employment|parcours\s*professionnel)"],
    "education": [r"(education|[eé]ducation|formation|[eé]tudes|diplômes?|dipl[o]mes?|scolarité|academic\s*background)"],
    "skills": [r"(comp[eé]tences?\s*(techniques?)?|technical\s*skills?|skills?|hard\s*skills?|savoir[\s-]faire)"],
    "soft_skills": [r"(soft\s*skills?|qualit[eé]s\s*personnelles?|interpersonal\s*skills?|savoir[\s-]être)"],
    "languages": [r"(langues?|languages?|language\s*proficiency|niveau\s*de\s*langue)"],
    "projects": [r"(projets?|projects?|personal\s*projects?|side\s*projects?)"],
    "certifications": [r"(certifications?|certificats?|habilitations?|licences?)"],
    "interests": [r"(int[eé]r[eê]ts?|hobbies?|loisirs?|activit[eé]s?\s*extra)"],
}

# ── Level mappings ─────────────────────────────────────────────────────────────
LEVEL_MAP = {
    "native": 100, "natif": 100, "langue maternelle": 100,
    "fluent": 90, "courant": 90, "bilingue": 95, "bilingual": 95,
    "c2": 88, "c1": 80,
    "advanced": 75, "avancé": 75, "professionnel": 75,
    "b2": 65, "b1": 50, "intermediate": 50, "intermédiaire": 50,
    "a2": 35, "a1": 20, "basic": 25, "notions": 20, "débutant": 20,
}

EDU_MAP = {
    "phd": 100, "doctorat": 100, "doctorate": 100,
    "master": 88, "msc": 88, "mba": 88, "master 2": 88, "m2": 88,
    "bachelor": 75, "licence": 75, "b.sc": 75, "b.eng": 75, "ingénieur": 85, "ingenieur": 85,
    "bts": 60, "dut": 60, "deug": 55, "bac+2": 60,
    "bac": 50, "baccalauréat": 50, "bac+3": 72,
}

# ── spaCy models (lazy load) ───────────────────────────────────────────────────
_nlp_en = None
_nlp_fr = None


def _get_nlp(lang: str):
    global _nlp_en, _nlp_fr
    if lang == "fr":
        if _nlp_fr is None:
            model = os.environ.get("SPACY_MODEL_FR", "fr_core_news_sm")
            _nlp_fr = spacy.load(model)
        return _nlp_fr
    else:
        if _nlp_en is None:
            model = os.environ.get("SPACY_MODEL_EN", "en_core_web_sm")
            _nlp_en = spacy.load(model)
        return _nlp_en


# ── Text extraction ────────────────────────────────────────────────────────────
def _get_image_bboxes(page) -> list:
    bboxes = []
    for img in page.images:
        bboxes.append((img["x0"], img["top"], img["x1"], img["bottom"]))
    return bboxes


def _word_in_image_region(word: dict, bboxes: list) -> bool:
    wx0, wy0, wx1, wy1 = word["x0"], word["top"], word["x1"], word["bottom"]
    for (bx0, by0, bx1, by1) in bboxes:
        if wx0 >= bx0 and wy0 >= by0 and wx1 <= bx1 and wy1 <= by1:
            return True
    return False


def extract_raw_text(filepath: str) -> str:
    path = pathlib.Path(filepath)
    if path.suffix.lower() in (".docx", ".doc"):
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""

    pages_text = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            image_bboxes = _get_image_bboxes(page)
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            if not words:
                continue

            # Detect two-column layout
            xs = [w["x0"] for w in words]
            midpoint = (min(xs) + max(xs)) / 2
            left_words = [w for w in words if w["x0"] < midpoint]
            right_words = [w for w in words if w["x0"] >= midpoint]

            if len(right_words) > len(left_words) * 0.3 and right_words:
                # Two-column: concatenate left then right
                def words_to_text(wlist):
                    wlist = [w for w in wlist if not _word_in_image_region(w, image_bboxes)]
                    wlist.sort(key=lambda w: (round(w["top"] / 5), w["x0"]))
                    return " ".join(w["text"] for w in wlist)
                pages_text.append(words_to_text(left_words) + "\n" + words_to_text(right_words))
            else:
                words = [w for w in words if not _word_in_image_region(w, image_bboxes)]
                words.sort(key=lambda w: (round(w["top"] / 5), w["x0"]))
                pages_text.append(" ".join(w["text"] for w in words))

    return "\n".join(pages_text)


def normalize_spaced_text(text: str) -> str:
    """Collapse spaced-out text: 'F O R M A T I O N S' → 'FORMATIONS'"""
    return re.sub(r"\b([A-ZÀÂÉÈÊËÎÏÔÙÛÜÇ]) (?=[A-ZÀÂÉÈÊËÎÏÔÙÛÜÇ] |\b)", r"\1", text)


# ── Language detection ─────────────────────────────────────────────────────────
def detect_language(text: str) -> str:
    try:
        sample = text[:800].strip()
        detected = lang_detect(sample)
        if detected in ("fr", "en"):
            return detected
        if detected in ("ar", "ca", "es", "pt"):
            return "fr"
        return "en"
    except LangDetectException:
        return "en"


# ── Groq section parser ────────────────────────────────────────────────────────
def parse_sections_groq(text: str, lang: str) -> dict:
    lang_hint = "The resume is in French." if lang == "fr" else "The resume is in English."
    prompt = f"""You are an expert ATS resume parser. {lang_hint}
The text was extracted from a PDF and MAY be jumbled or interleaved (two-column layouts mix the
sidebar with the main column). Reconstruct the candidate's information logically and carefully.

Return ONLY a valid JSON object (no markdown, no comments) with EXACTLY these keys:
{{
  "name": "candidate full name only (not a section header)",
  "phone": "the phone number as written (e.g. +212 6 05 61 68 55) — never a date",
  "location": "city/region only",
  "profile": "1-2 sentence professional summary. If none is written, synthesize one from the title and most recent experience.",
  "experience": ["one string per job, formatted EXACTLY: <job title> — <company/organization> (<date range>): <short description>"],
  "education": ["one string per diploma, formatted EXACTLY: <degree> — <institution> (<year or range>)"],
  "projects": ["personal/side projects only — do NOT duplicate work experience here"],
  "certifications": ["certifications only"],
  "skills": ["technical skills/tools only — split combined tokens, no section headers"],
  "soft_skills": ["soft skills only"],
  "languages_spoken": [{{"language": "Français", "level": "Professionnel"}}],
  "interests": ["hobbies/interests"],
  "experience_years": <number: total years of professional experience, estimated from the dates>,
  "education_level": "PhD|Master|Bachelor|BTS|Bac+2|Bac|None (highest obtained)",
  "industry": "main industry/domain in 1-3 words"
}}

CRITICAL RULES:
- Keep company and institution names COMPLETE and EXACT — do not drop or merge words, and never
  invent them. If a job has no clear company, use "" for the company part.
- Section headers (CONTACT, LANGUES, PROFIL, COMPÉTENCES, FORMATION, EXPÉRIENCE, "Outils de
  développement", etc.), portfolio URLs and template watermarks are NOT names/companies/skills — ignore them.
- Associate each bullet/description with the MOST RELEVANT job by its content; if unsure, keep the
  description short or empty rather than attaching it to the wrong job.
- "phone" must be a phone number, NEVER a date or year range.
- Fix obviously garbled accents (é, è, à, ç) in your output and use proper French language names.
- Do not duplicate the same entry across experience, education and projects.

Resume text:
\"\"\"
{text[:8000]}
\"\"\"
"""
    try:
        resp = _get_groq_client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception:
        return {}


# ── Contact extractors ─────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
# Moroccan mobile/landline (+212 / 0 prefix, 9 significant digits) and generic international
_PHONE_MA = re.compile(r"(?:(?:\+|00)\s?212|0)\s?\(?0?\)?[\s.\-]?[5-7](?:[\s.\-]?\d){8}")
_PHONE_INTL = re.compile(r"\+\d{1,3}(?:[\s.\-]?\d){7,12}")
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/(?:in/|pub/)?[\w\-%./]+", re.IGNORECASE)
_GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", re.IGNORECASE)


def _fix_mojibake(text: str) -> str:
    """Fix common PDF-template font mis-mappings where an uppercase accent appears
    inside a lowercase word (e.g. 'DÈveloppement' -> 'Développement', 'FranÁais' -> 'Français')."""
    if not text:
        return text
    # An uppercase accent touching a lowercase letter (before or after) is a font mis-map,
    # not a real all-caps header. Replace it; leave all-caps headers (e.g. LANGUES) untouched.
    text = re.sub(r"È(?=[a-zà-ÿ])|(?<=[a-zà-ÿ])È", "é", text)
    text = re.sub(r"Á(?=[a-zà-ÿ])|(?<=[a-zà-ÿ])Á", "ç", text)
    text = re.sub(r"Ë(?=[a-zà-ÿ])|(?<=[a-zà-ÿ])Ë", "è", text)
    return text


def _extract_phone(text: str) -> str:
    """Robustly pick a phone number, never a date/year range."""
    for rx in (_PHONE_MA, _PHONE_INTL):
        for m in rx.finditer(text):
            cand = m.group(0).strip()
            if "/" in cand:  # date like 03/2024
                continue
            digits = re.sub(r"\D", "", cand)
            if not (9 <= len(digits) <= 15):
                continue
            if len(set(digits)) <= 1:  # 0000000000
                continue
            # reject year-range-looking 8-digit blobs (e.g. 20172018)
            if len(digits) == 8 and digits[:2] in ("19", "20") and digits[4:6] in ("19", "20"):
                continue
            return re.sub(r"\s{2,}", " ", cand)
    return ""


_LANG_NAME_FIX = {
    "francais": "Français", "français": "Français", "franáais": "Français", "franглais": "Français",
    "anglais": "Anglais", "english": "Anglais", "arabe": "Arabe", "arabic": "Arabe",
    "espagnol": "Espagnol", "spanish": "Espagnol", "allemand": "Allemand", "german": "Allemand",
}


def _normalize_languages(langs: list) -> list:
    out = []
    for entry in langs or []:
        if not isinstance(entry, dict):
            continue
        name = _fix_mojibake(str(entry.get("language", "")).strip())
        fixed = _LANG_NAME_FIX.get(name.lower(), name)
        level = str(entry.get("level", "")).strip()
        if fixed:
            out.append({"language": fixed, "level": level})
    return out


def extract_contact_info(text: str, groq_data: dict) -> dict:
    email_m = _EMAIL_RE.search(text)
    linkedin_m = _LINKEDIN_RE.search(text)
    github_m = _GITHUB_RE.search(text)

    phone = _extract_phone(text)
    if not phone:
        llm_phone = str(groq_data.get("phone", "") or "").strip()
        if llm_phone and "/" not in llm_phone and 9 <= len(re.sub(r"\D", "", llm_phone)) <= 15:
            phone = llm_phone

    return {
        "name": _fix_mojibake(groq_data.get("name", "") or ""),
        "email": email_m.group(0) if email_m else "",
        "phone": phone,
        "location": _fix_mojibake(groq_data.get("location", "") or ""),
        "linkedin": linkedin_m.group(0) if linkedin_m else "",
        "github": github_m.group(0) if github_m else "",
    }


# ── Skill normalizer ───────────────────────────────────────────────────────────
def normalize_skill_token(token: str) -> str:
    return ALIAS_TO_CANONICAL.get(token.lower().strip(), token.strip())


def normalize_skills(groq_skills: list) -> list:
    if not groq_skills:
        return []
    normalized = set()
    for skill in groq_skills:
        skill = str(skill).strip()
        if not skill or len(skill) > 60:
            continue
        normalized.add(normalize_skill_token(skill))
    return sorted(normalized)


# ── Experience enrichment ──────────────────────────────────────────────────────
_ACHIEVEMENT_PATTERNS = [
    re.compile(r"\d+\s*%"),
    re.compile(r"\$\s*\d[\d,.]*[kKmMbB]?"),
    re.compile(r"\d+\s*(?:millions?|milliers?|users?|clients?|projets?|pays|countries)"),
    re.compile(r"réduit|augmenté|amélioré|optimisé|reduced|increased|improved|optimized", re.IGNORECASE),
]

_ACTION_VERBS = {
    "en": {"developed", "built", "led", "managed", "designed", "implemented", "deployed",
           "optimized", "created", "improved", "reduced", "increased", "delivered"},
    "fr": {"développé", "construit", "dirigé", "géré", "conçu", "implémenté", "déployé",
           "optimisé", "créé", "amélioré", "réduit", "augmenté", "livré"},
}

_BUZZWORDS = {
    "hardworking", "team player", "motivated", "passionate", "dynamic", "proactive",
    "travailleur", "motivé", "passionné", "dynamique", "proactif",
}


def enrich_experience(experience_list: list, skills: list, lang: str) -> dict:
    text = " ".join(str(e) for e in experience_list) if experience_list else ""
    achievements = []
    for pat in _ACHIEVEMENT_PATTERNS:
        for m in pat.finditer(text):
            achievements.append(m.group(0))

    action_hits = set()
    words_lower = set(re.findall(r"[a-zàâéèêëîïôùûü]+", text.lower()))
    for verb in _ACTION_VERBS.get(lang, _ACTION_VERBS["en"]):
        if verb in words_lower:
            action_hits.add(verb)

    buzzwords_found = [bw for bw in _BUZZWORDS if bw in words_lower]
    skills_in_exp = [s for s in skills if s.lower() in text.lower()]

    return {
        "quantified_achievements": achievements,
        "action_verb_scores": {"count": len(action_hits), "verbs": list(action_hits)},
        "buzzword_analysis": {"count": len(buzzwords_found), "words": buzzwords_found},
        "skills_in_experience": skills_in_exp,
    }


# ── Confidence + flags ─────────────────────────────────────────────────────────
def compute_confidence_score(sections: dict, contact: dict) -> dict:
    checks = {
        "name": bool(contact.get("name")),
        "email": bool(contact.get("email")),
        "skills": bool(sections.get("skills")),
        "experience": bool(sections.get("experience")),
        "education": bool(sections.get("education")),
        "location": bool(contact.get("location")),
    }
    score = round(sum(checks.values()) / len(checks) * 100)
    missing = [k for k, v in checks.items() if not v]
    flags = []
    if "email" in missing:
        flags.append("missing_email")
    if "name" in missing:
        flags.append("missing_name")
    if not sections.get("skills"):
        flags.append("no_skills_detected")
    if not sections.get("experience"):
        flags.append("no_experience_detected")
    return {"confidence_score": score, "flags": flags}


# ── Master extraction function ─────────────────────────────────────────────────
def extract_resume(filepath: str) -> dict:
    raw_text = extract_raw_text(filepath)
    raw_text = normalize_spaced_text(raw_text)
    raw_text = _fix_mojibake(raw_text)
    if not raw_text.strip():
        return {"file": filepath, "error": "no_text_extracted"}

    lang = detect_language(raw_text)
    groq_data = parse_sections_groq(raw_text, lang)
    contact = extract_contact_info(raw_text, groq_data)
    skills = normalize_skills(groq_data.get("skills", []))
    soft_skills = groq_data.get("soft_skills", [])
    experience_list = groq_data.get("experience", [])

    enrichment = enrich_experience(experience_list, skills, lang)
    confidence = compute_confidence_score(groq_data, contact)

    return {
        "file": filepath,
        **contact,
        "language": lang,
        "profile": _fix_mojibake(groq_data.get("profile", "") or ""),
        "experience": [_fix_mojibake(str(x)) for x in (experience_list or [])],
        "education": [_fix_mojibake(str(x)) for x in (groq_data.get("education", []) or [])],
        "projects": [_fix_mojibake(str(x)) for x in (groq_data.get("projects", []) or [])],
        "certifications": groq_data.get("certifications", []),
        "skills": skills,
        "soft_skills": soft_skills,
        "languages_spoken": _normalize_languages(groq_data.get("languages_spoken", [])),
        "interests": groq_data.get("interests", []),
        "experience_years": float(groq_data.get("experience_years", 0) or 0),
        "education_level": groq_data.get("education_level", ""),
        "industry": _fix_mojibake(groq_data.get("industry", "") or ""),
        **enrichment,
        **confidence,
    }


def process_resumes(filepaths: list) -> tuple:
    results = []
    for fp in filepaths:
        try:
            results.append(extract_resume(fp))
        except Exception as e:
            results.append({"file": fp, "error": str(e)})
    df = pd.DataFrame([{
        "file": r.get("file"),
        "name": r.get("name"),
        "email": r.get("email"),
        "skills_count": len(r.get("skills", [])),
        "experience_years": r.get("experience_years"),
        "confidence": r.get("confidence_score"),
        "flags": "; ".join(r.get("flags", [])),
    } for r in results])
    return results, df

"""
Job Description Parser
Notebook-parity extraction with backward-compatible response fields.
"""
import json
import os
import pathlib
import re
from typing import Any, Optional

from dotenv import load_dotenv
from groq import Groq
from langdetect import LangDetectException, detect as lang_detect

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"
_client: Optional[Groq] = None

SENIORITY_MAP = [
    (0, 0, "Internship"),
    (1, 2, "Junior"),
    (3, 5, "Mid-Level"),
    (6, 9, "Senior"),
    (10, 99, "Lead / Principal"),
]

BAC_MAP = {
    8: "Phd",
    7: "Phd",
    6: "Master+",
    5: "Master (M2)",
    4: "Master (M1)",
    3: "Bachelor",
    2: "Diploma",
    1: "Diploma",
}

KNOWN_TECH = {
    "PowerBI", "Power BI", "Tableau", "Qlik", "MicroStrategy", "Looker", "SSRS",
    "Talend", "Informatica", "SSIS", "DataStage", "Pentaho", "Matillion",
    "Hadoop", "Spark", "Hive", "HBase", "Kafka", "Flink", "Airflow", "Cloudera", "Hortonworks",
    "Teradata", "Oracle", "PostgreSQL", "MySQL", "SQLServer", "SQL Server", "MongoDB", "Cassandra", "Snowflake",
    "Redshift", "BigQuery", "AWS", "Azure", "GCP", "Python", "R", "Scala", "Java", "SQL", "dbt", "Dataiku",
}

SKILL_NORMALIZATION = {
    "modélisation de données décisionnelles": ("Data Modeling", "data_engineering"),
    "entrepôt de données": ("Data Warehousing", "data_engineering"),
    "bases de données sql": ("SQL", "data_engineering"),
    "gestion de projet": ("Project Management", "management"),
    "analyse de données": ("Data Analysis", "analytics"),
    "reporting": ("Reporting", "analytics"),
    "tableau de bord": ("Dashboard", "analytics"),
    "intelligence artificielle": ("Artificial Intelligence", "ml_ai"),
    "machine learning": ("Machine Learning", "ml_ai"),
}

PRIORITY_SKILLS = {
    "sql": 3,
    "python": 3,
    "power bi": 3,
    "powerbi": 3,
    "etl": 2,
    "elt": 2,
    "data warehousing": 2,
    "data modeling": 2,
    "spark": 2,
    "hadoop": 2,
    "reporting": 1,
    "tableau": 1,
    "kafka": 1,
    "airflow": 1,
}


def _get_groq_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    return _client


def _ensure_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [v.strip() for v in re.split(r"[,;\n•·|]+", value) if v.strip()]
    return []


def _extract_jd_text(source: str) -> str:
    if isinstance(source, str) and pathlib.Path(source).exists():
        path = pathlib.Path(source)
        if path.suffix.lower() == ".pdf":
            import pdfplumber

            chunks = []
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    chunks.append(page.extract_text() or "")
            return "\n".join(chunks).strip()
        if path.suffix.lower() in (".docx", ".doc"):
            from docx import Document as DocxDocument

            doc = DocxDocument(str(path))
            return "\n".join(p.text for p in doc.paragraphs).strip()
    return str(source or "").strip()


def detect_language(text: str) -> str:
    try:
        detected = lang_detect((text or "")[:1000])
        if detected in ("fr", "en"):
            return detected
        if detected in ("ar", "es", "pt", "ca"):
            return "fr"
        return "en"
    except LangDetectException:
        return "fr"


def infer_seniority(years: int) -> str:
    for lo, hi, label in SENIORITY_MAP:
        if lo <= years <= hi:
            return label
    return "Mid-Level"


def normalize_education(min_edu: str, edu_field: str | None, raw_text: str) -> dict:
    bac_match = re.search(r"[Bb]ac\s*\+\s*(\d)", raw_text or "")
    if bac_match:
        n = int(bac_match.group(1))
        degree_level = BAC_MAP.get(n, "Master")
        degree_raw = f"Bac+{n}"
    else:
        degree_level = (min_edu or "None").strip()
        degree_raw = (min_edu or "None").strip()

    fields = []
    if edu_field:
        fields = [f.strip() for f in re.split(r"[/,;]+", edu_field) if f.strip()]

    return {"degree_level": degree_level, "fields": fields, "degree_raw": degree_raw}


def split_skills(skills: list[str]) -> list[str]:
    result: list[str] = []
    known_lower = {tech.lower(): tech for tech in KNOWN_TECH}

    for skill in skills:
        raw = str(skill).strip()
        if not raw:
            continue
        if " / " in raw or " | " in raw:
            result.extend(part.strip() for part in re.split(r" [/|] ", raw) if part.strip())
            continue

        words = raw.split()
        if len(words) == 2:
            w1, w2 = words[0].lower(), words[1].lower()
            if w1 in known_lower and w2 in known_lower:
                result.append(known_lower[w1])
                result.append(known_lower[w2])
                continue
        result.append(raw)

    deduped = []
    seen = set()
    for item in result:
        low = item.lower()
        if low not in seen:
            seen.add(low)
            deduped.append(item)
    return deduped


def normalize_skill(skill: str) -> dict:
    key = skill.lower().strip()
    if key in SKILL_NORMALIZATION:
        norm, category = SKILL_NORMALIZATION[key]
        return {"raw": skill, "normalized": norm, "category": category}
    return {"raw": skill, "normalized": skill, "category": "other"}


def score_critical_skills(required_skills: list[str], raw_text: str) -> list[str]:
    text_lower = (raw_text or "").lower()
    scores = {}
    for skill in required_skills:
        key = skill.lower()
        freq = text_lower.count(key)
        boost = PRIORITY_SKILLS.get(key, 0)
        scores[skill] = freq + boost
    critical = [s for s, score in sorted(scores.items(), key=lambda x: -x[1]) if score >= 2]
    return critical[:10]


def parse_jd_groq(text: str, lang: str) -> dict:
    lang_hint = "The job description is in French." if lang == "fr" else "The job description is in English."
    prompt = f"""You are a job description parser. {lang_hint}
Extract structured information from the job description below.
Return ONLY a valid JSON object, no explanation, no markdown.

{{
  "job_title": "exact job title",
  "company_name": "company name or null",
  "location": "city or region or null",
  "remote_ok": false,
  "job_type": "CDI|CDD|Stage|Freelance|Permanent|Contract|Internship",
  "job_function": "one of: Data Analytics | BI | Data Engineering | Software Engineering | DevOps | Management | Sales | Marketing | Finance | HR | Other",
  "seniority": "one of: Internship | Junior | Mid-Level | Senior | Lead",
  "industry": "e.g. Insurance | Banking | Retail | Healthcare | Tech | Other",
  "department": "e.g. Data & AI | Engineering | Finance | Operations | Other",
  "domain": "industry domain in 1-2 words",
  "required_skills": ["skill1", "skill2"],
  "critical_skills": ["skill1"],
  "required_soft_skills": ["communication", "teamwork"],
  "required_languages": [
    {{"language": "French", "min_level": "Fluent", "weight": 0.5}},
    {{"language": "English", "min_level": "Intermediate", "weight": 0.5}}
  ],
  "experience_required_years": 0,
  "min_education": "PhD|Master|Master+|Bachelor|Diploma|None",
  "education_field": "Data / BI / Engineering",
  "description_summary": "2-3 sentence summary"
}}

RULES:
- Return [] for empty lists.
- Return null for unknown scalar fields.
- Keep critical_skills a subset of required_skills.
- Split concatenated skills like "Cloudera Teradata".

JOB DESCRIPTION:
\"\"\"
{text[:5000]}
\"\"\"
"""

    try:
        response = _get_groq_client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1800,
        )
        raw = (response.choices[0].message.content or "").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        parsed = json.loads(raw)
    except Exception:
        return {}

    parsed["required_skills"] = split_skills(_ensure_list(parsed.get("required_skills")))
    llm_critical = _ensure_list(parsed.get("critical_skills"))
    llm_critical = [
        s for s in llm_critical if s.lower() in {r.lower() for r in parsed.get("required_skills", [])}
    ]
    scored_critical = score_critical_skills(parsed.get("required_skills", []), text)
    parsed["critical_skills"] = list(dict.fromkeys(scored_critical + llm_critical))[:10]

    parsed["required_soft_skills"] = _ensure_list(parsed.get("required_soft_skills"))
    parsed["required_languages"] = _normalize_required_languages(parsed.get("required_languages"))
    return parsed


def _normalize_required_languages(raw_languages: Any) -> list[dict]:
    entries = _ensure_list(raw_languages)
    normalized = []
    for item in entries:
        if isinstance(item, dict):
            language = str(item.get("language", "")).strip()
            if not language:
                continue
            min_level = str(item.get("min_level") or item.get("level") or "").strip()
            weight = item.get("weight", 0)
            try:
                weight = float(weight)
            except (TypeError, ValueError):
                weight = 0.0
            normalized.append({"language": language, "min_level": min_level, "weight": weight})
        elif isinstance(item, str):
            val = item.strip()
            if val:
                normalized.append({"language": val, "min_level": "", "weight": 0.0})

    if not normalized:
        return []

    total = sum(entry["weight"] for entry in normalized)
    if total <= 0:
        equal = round(1.0 / len(normalized), 2)
        return [{**entry, "weight": equal} for entry in normalized]

    return [{**entry, "weight": round(entry["weight"] / total, 2)} for entry in normalized]


def _legacy_languages(required_languages: list[dict]) -> list[dict]:
    return [
        {"language": item.get("language", ""), "level": item.get("min_level", "")}
        for item in required_languages
        if item.get("language")
    ]


def _infer_job_type(job_type: str, text: str) -> str:
    normalized = (job_type or "").strip()
    if normalized:
        upper = normalized.upper()
        if upper in {"CDI", "CDD", "STAGE", "FREELANCE"}:
            return upper if upper != "STAGE" else "Stage"
        if upper in {"PERMANENT", "FULL-TIME"}:
            return "CDI"
        if upper in {"CONTRACT", "TEMPORARY"}:
            return "CDD"
        if upper in {"INTERNSHIP", "INTERN"}:
            return "Stage"
        return normalized

    text_lower = (text or "").lower()
    if any(token in text_lower for token in ("internship", "intern", "stage")):
        return "Stage"
    if any(token in text_lower for token in ("freelance", "contractor")):
        return "Freelance"
    if "cdd" in text_lower:
        return "CDD"
    return "CDI"


def build_jd_flags(job: dict) -> list:
    flags = []

    def flag(code: str, severity: str, message: str):
        flags.append({"code": code, "severity": severity, "message": message})

    if not job.get("job_title"):
        flag("missing_job_title", "critical", "Job title not found")
    if len(job.get("required_skills", [])) < 3:
        flag("few_skills", "warning", "Fewer than 3 skills extracted")
    if not job.get("critical_skills"):
        flag("no_critical_skills", "warning", "No critical skills identified")
    if not job.get("experience_required_years"):
        flag("no_experience_requirement", "info", "No explicit experience requirement")
    if not job.get("location"):
        flag("location_unspecified", "info", "Location not found or inferred")
    if not job.get("required_languages"):
        flag("no_language_requirement", "info", "No language requirement extracted")
    if not job.get("description_summary"):
        flag("no_summary", "warning", "No role summary extracted")
    return flags


def extract_jd(source: str, lang: Optional[str] = None) -> dict:
    raw_text = _extract_jd_text(source)
    if not raw_text.strip():
        return {"error": "no_text_extracted"}

    detected_lang = lang or detect_language(raw_text)
    parsed = parse_jd_groq(raw_text, detected_lang)
    if not parsed:
        return {
            "title": "",
            "domain": "",
            "job_type": "CDI",
            "location": "",
            "required_skills": [],
            "critical_skills": [],
            "soft_skills": [],
            "experience_required_years": 0,
            "education_required": "",
            "languages_required": [],
            "flags": [{"code": "parse_failed", "severity": "critical", "message": "JD parsing failed"}],
        }

    edu_struct = normalize_education(
        parsed.get("min_education") or "",
        parsed.get("education_field"),
        raw_text,
    )

    required_skills = _ensure_list(parsed.get("required_skills"))
    critical_skills = _ensure_list(parsed.get("critical_skills"))
    required_languages = _normalize_required_languages(parsed.get("required_languages"))
    experience_required_years = int(parsed.get("experience_required_years") or 0)
    seniority = parsed.get("seniority") or infer_seniority(experience_required_years)

    result = {
        # enriched notebook-style fields
        "language": detected_lang,
        "job_title": parsed.get("job_title") or parsed.get("title") or "",
        "company_name": parsed.get("company_name"),
        "location": parsed.get("location") or "",
        "remote_ok": bool(parsed.get("remote_ok", False)),
        "job_function": parsed.get("job_function") or "Other",
        "seniority": seniority,
        "industry": parsed.get("industry"),
        "department": parsed.get("department"),
        "domain": parsed.get("domain") or "",
        "required_skills": required_skills,
        "critical_skills": critical_skills,
        "normalized_skills": [normalize_skill(skill) for skill in required_skills],
        "required_soft_skills": _ensure_list(parsed.get("required_soft_skills")),
        "required_languages": required_languages,
        "experience_required_years": experience_required_years,
        "seniority_label": seniority,
        "education": {
            "degree_level": edu_struct["degree_level"],
            "fields": edu_struct["fields"],
            "degree_raw": edu_struct["degree_raw"],
        },
        "min_education": edu_struct["degree_level"],
        "education_field": parsed.get("education_field"),
        "description_summary": parsed.get("description_summary") or "",
        # backward-compatible fields used by current frontend/API docs
        "title": parsed.get("job_title") or parsed.get("title") or "",
        "job_type": _infer_job_type(parsed.get("job_type", ""), raw_text),
        "soft_skills": _ensure_list(parsed.get("required_soft_skills")),
        "education_required": edu_struct["degree_level"],
        "languages_required": _legacy_languages(required_languages),
    }
    result["flags"] = build_jd_flags(result)
    return result


def extract_job_offer(text: str, lang: str = "fr") -> dict:
    """
    Backward-compatible API entrypoint.
    Returns the legacy fields plus additional enriched metadata.
    """
    return extract_jd(text, lang=lang)

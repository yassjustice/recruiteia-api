"""
V2 scoring service aligned with schema_updated.sql.
Backward-compatible output fields are kept for existing clients.
"""
import hashlib
import json
import os
from difflib import SequenceMatcher
import re
from typing import Any
from groq import Groq

DEFAULT_WEIGHTS_V2 = {
    "skills_match": 0.30,
    "experience_relevance": 0.22,
    "achievements": 0.15,
    "language_quality": 0.10,
    "language_match": 0.10,
    "education": 0.08,
    "location": 0.05,
}

GROQ_MODEL = os.environ.get("SCORER_GROQ_MODEL", "llama-3.3-70b-versatile")
_groq_client: Groq | None = None
# Notebook-parity cache key: md5(experience text + JD summary/raw text)
_experience_cache: dict[str, tuple[float, str]] = {}
_EXPERIENCE_CACHE_MAX_SIZE = 5000

LEVEL_MAP = {
    "native": 100,
    "natif": 100,
    "langue maternelle": 100,
    "bilingual": 100,
    "bilingue": 100,
    "fluent": 85,
    "courant": 85,
    "c2": 88,
    "c1": 80,
    "advanced": 70,
    "avancé": 70,
    "avance": 70,
    "b2": 65,
    "intermediate": 50,
    "intermédiaire": 50,
    "intermediaire": 50,
    "b1": 50,
    "a2": 35,
    "basic": 20,
    "basique": 20,
    "a1": 20,
    "débutant": 20,
    "debutant": 20,
}

LANGUAGE_NAME_MAP = {
    "francais": "french",
    "français": "french",
    "anglais": "english",
    "arabe": "arabic",
    "espagnol": "spanish",
    "allemand": "german",
}

EDU_ORDER = {"phd": 5, "master": 4, "bachelor": 3, "diploma": 2, "none": 1}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _match(a: str, b: str, threshold: float = 0.88) -> bool:
    a_norm = a.lower().strip()
    b_norm = b.lower().strip()
    if not a_norm or not b_norm:
        return False
    return a_norm in b_norm or b_norm in a_norm or _similarity(a_norm, b_norm) >= threshold


def _ensure_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,;\n•·|]+", value) if item.strip()]
    return []


def _textify(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item is not None)
    if isinstance(value, dict):
        return " ".join(str(v) for v in value.values() if v is not None)
    return ""


def _normalize_language_level(level: str) -> int:
    if not level:
        return 0
    return LEVEL_MAP.get(level.lower().strip(), 40)


def _normalize_language_name(name: str) -> str:
    key = (name or "").lower().strip()
    return LANGUAGE_NAME_MAP.get(key, key)


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _required_languages(job: dict) -> list[dict]:
    required = _ensure_list(job.get("required_languages"))
    normalized = []
    for entry in required:
        if not isinstance(entry, dict):
            continue
        language = str(entry.get("language", "")).strip()
        if not language:
            continue
        min_level = str(entry.get("min_level") or entry.get("level") or "").strip()
        weight = entry.get("weight", 0)
        try:
            weight = float(weight)
        except (TypeError, ValueError):
            weight = 0.0
        normalized.append({"language": language, "min_level": min_level, "weight": weight})

    if not normalized:
        legacy = _ensure_list(job.get("languages_required"))
        if not legacy:
            return []
        equal = 1.0 / len(legacy)
        for entry in legacy:
            if isinstance(entry, dict) and entry.get("language"):
                normalized.append(
                    {
                        "language": str(entry.get("language")).strip(),
                        "min_level": str(entry.get("level", "")).strip(),
                        "weight": equal,
                    }
                )

    total = sum(item["weight"] for item in normalized)
    if normalized and total <= 0:
        equal = round(1.0 / len(normalized), 2)
        return [{**item, "weight": equal} for item in normalized]
    if normalized and total > 0:
        return [{**item, "weight": item["weight"] / total} for item in normalized]
    return []


def _normalize_weights(weights: dict | None) -> dict:
    incoming = weights or {}
    mapped = {
        "skills_match": incoming.get("skills_match", incoming.get("skills", DEFAULT_WEIGHTS_V2["skills_match"])),
        "experience_relevance": incoming.get(
            "experience_relevance", incoming.get("experience", DEFAULT_WEIGHTS_V2["experience_relevance"])
        ),
        "achievements": incoming.get("achievements", DEFAULT_WEIGHTS_V2["achievements"]),
        "language_quality": incoming.get("language_quality", DEFAULT_WEIGHTS_V2["language_quality"]),
        "language_match": incoming.get("language_match", incoming.get("language", DEFAULT_WEIGHTS_V2["language_match"])),
        "education": incoming.get("education", DEFAULT_WEIGHTS_V2["education"]),
        "location": incoming.get("location", DEFAULT_WEIGHTS_V2["location"]),
    }
    normalized = {}
    for key, value in mapped.items():
        try:
            normalized[key] = float(value)
        except (TypeError, ValueError):
            normalized[key] = DEFAULT_WEIGHTS_V2[key]
    total = sum(normalized.values())
    if total <= 0:
        return DEFAULT_WEIGHTS_V2.copy()
    return {k: v / total for k, v in normalized.items()}


def _edu_rank(level: str) -> int:
    lvl = (level or "").lower().strip()
    if not lvl:
        return 0
    if "phd" in lvl or "doctorat" in lvl or "doctorate" in lvl:
        return EDU_ORDER["phd"]
    if "master" in lvl or "msc" in lvl or "bac+5" in lvl or "bac +5" in lvl:
        return EDU_ORDER["master"]
    if "bachelor" in lvl or "licence" in lvl or "bac+3" in lvl or "bac +3" in lvl:
        return EDU_ORDER["bachelor"]
    if "diploma" in lvl or "dut" in lvl or "bts" in lvl or "bac+2" in lvl:
        return EDU_ORDER["diploma"]
    if "none" in lvl or "any" in lvl:
        return EDU_ORDER["none"]
    return 0


def _achievements_score(candidate: dict) -> float:
    qa = candidate.get("quantified_achievements")
    if isinstance(qa, dict):
        count = int(qa.get("count") or len(_ensure_list(qa.get("examples"))))
    elif isinstance(qa, list):
        count = len(qa)
    else:
        count = 0

    if count <= 0:
        return 0.0
    if count == 1:
        return 0.35
    if count == 2:
        return 0.55
    if count == 3:
        return 0.70
    return min(1.0, 0.85 + (count - 4) * 0.05)


def _confidence_value(candidate: dict) -> float:
    raw = candidate.get("confidence_score", 100)
    if isinstance(raw, dict):
        raw = raw.get("confidence", 100)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 100.0
    return value * 100.0 if value <= 1.0 else value


def score_skills(candidate: dict, job: dict) -> dict:
    required = [str(s).strip() for s in _ensure_list(job.get("required_skills")) if str(s).strip()]
    critical = [str(s).strip() for s in _ensure_list(job.get("critical_skills")) if str(s).strip()]
    cand_skills = [str(s).strip() for s in _ensure_list(candidate.get("skills")) if str(s).strip()]
    backed = [str(s).strip() for s in _ensure_list(candidate.get("skills_in_experience")) if str(s).strip()]

    if not required:
        return {"score": 0.5, "matched": [], "missing_skills": [], "critical_missing": []}

    matched = []
    missing = []
    total_weight = 0.0
    earned = 0.0
    critical_set = {s.lower() for s in critical}

    for job_skill in required:
        j_low = job_skill.lower()
        weight = 2.0 if j_low in critical_set else 1.0
        total_weight += weight

        skill_matched = any(_match(c_skill, job_skill) for c_skill in cand_skills)
        if skill_matched:
            matched.append(job_skill)
            pts = weight
            if any(_match(back_skill, job_skill) for back_skill in backed):
                pts += 0.10 * weight
            earned += pts
        else:
            missing.append(job_skill)

    critical_missing = [crit for crit in critical if not any(_match(c_skill, crit) for c_skill in cand_skills)]
    score = earned / total_weight if total_weight else 0.0
    return {
        "score": round(min(score, 1.0), 4),
        "matched": matched,
        "missing_skills": missing,
        "critical_missing": critical_missing,
    }


def _score_experience_relevance_rule_based(candidate: dict, job: dict) -> tuple[float, str]:
    candidate_years = float(candidate.get("experience_years") or 0)
    required_years = float(job.get("experience_required_years") or 0)
    years_score = 1.0 if required_years <= 0 else (min(1.0, candidate_years / required_years) if candidate_years > 0 else 0.10)

    experience_text = " ".join(
        filter(
            None,
            [
                _textify(candidate.get("experience")),
                _textify(candidate.get("projects")),
                _textify(candidate.get("profile")),
            ],
        )
    ).lower()
    required_skills = [str(s).lower() for s in _ensure_list(job.get("required_skills"))]
    if required_skills and experience_text:
        matched = sum(
            1
            for skill in required_skills
            if skill and (skill in experience_text or any(_match(skill, token) for token in experience_text.split()))
        )
        relevance_score = matched / len(required_skills)
    else:
        relevance_score = 0.20 if not experience_text else 0.50

    combined = (0.65 * years_score) + (0.35 * relevance_score)
    reason = (
        f"{round(candidate_years, 1)} years vs required {round(required_years, 1)} years; "
        f"relevant skills coverage {round(relevance_score * 100, 1)}%"
    )
    return round(max(0.0, min(1.0, combined)), 4), reason


def score_experience_relevance(candidate: dict, job: dict) -> tuple[float, str]:
    """
    Notebook-parity behavior:
    - Ask Groq for 0-100 experience relevance
    - Cache by md5(experience/projects/profile + JD summary/raw_text)
    - Normalize to 0-1 for API scoring contract
    """
    experience_text = " ".join(
        filter(
            None,
            [
                _textify(candidate.get("experience")),
                _textify(candidate.get("projects")),
                _textify(candidate.get("profile")),
            ],
        )
    ).strip()
    if not experience_text:
        return 0.20, "No experience/projects/profile text found; baseline relevance 20.0%"

    jd_summary = _textify(job.get("description_summary")).strip()
    if not jd_summary:
        jd_summary = _textify(job.get("raw_text")).strip()
    if not jd_summary:
        return _score_experience_relevance_rule_based(candidate, job)

    raw_key = f"{experience_text[:3000]}||{jd_summary[:1500]}"
    cache_key = hashlib.md5(raw_key.encode("utf-8")).hexdigest()
    cached = _experience_cache.get(cache_key)
    if cached is not None:
        return cached

    prompt = f"""You are an ATS relevance scorer.
Rate from 0 to 100 how relevant the candidate experience/projects are to the job description.

JOB DESCRIPTION SUMMARY:
{jd_summary[:1500]}

CANDIDATE EXPERIENCE / PROJECTS:
{experience_text[:2000]}

Reply with ONLY valid JSON in this exact format (no markdown, no extra text):
{{"score": <integer 0-100>, "reason": "<one concise sentence>"}}"""

    try:
        response = _get_groq_client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=120,
        )
        raw = (response.choices[0].message.content or "").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        parsed = json.loads(raw)
        score_int = int(parsed["score"])
        score_int = max(0, min(100, score_int))
        score = round(score_int / 100.0, 4)
        reason = str(parsed.get("reason") or "").strip() or f"Groq relevance score {score_int}/100"
    except Exception:
        score, fallback_reason = _score_experience_relevance_rule_based(candidate, job)
        reason = f"Groq unavailable; heuristic fallback. {fallback_reason}"

    result = (score, reason)
    if len(_experience_cache) >= _EXPERIENCE_CACHE_MAX_SIZE:
        _experience_cache.clear()
    _experience_cache[cache_key] = result
    return result


def score_education(candidate: dict, job: dict) -> float:
    required_label = (job.get("min_education") or job.get("education_required") or "").strip()
    candidate_label = (candidate.get("education_level") or "").strip()
    req_rank = _edu_rank(required_label)
    cand_rank = _edu_rank(candidate_label)

    if req_rank == 0:
        return 1.0
    if cand_rank == 0:
        return 0.5
    if cand_rank > req_rank:
        return 1.0
    if cand_rank == req_rank:
        return 0.8
    return 0.3


def score_language_match(candidate: dict, job: dict) -> tuple[float, list[dict]]:
    required = _required_languages(job)
    if not required:
        return 1.0, []

    spoken_levels = {}
    for entry in _ensure_list(candidate.get("languages_spoken")):
        if not isinstance(entry, dict):
            continue
        name = _normalize_language_name(str(entry.get("language", "")))
        if not name:
            continue
        level_score = _normalize_language_level(str(entry.get("level", "")))
        spoken_levels[name] = max(spoken_levels.get(name, 0), level_score)

    total_weight = sum(item.get("weight", 0.0) for item in required)
    if total_weight <= 0:
        total_weight = float(len(required))
        for item in required:
            item["weight"] = 1.0

    earned = 0.0
    details = []
    for req in required:
        req_name = _normalize_language_name(str(req.get("language", "")))
        req_min_level = _normalize_language_level(str(req.get("min_level", "")))
        weight = float(req.get("weight", 1.0))
        candidate_level = spoken_levels.get(req_name, 0)

        if req_min_level <= 0:
            component = weight if candidate_level > 0 else 0.6 * weight
        elif candidate_level >= req_min_level:
            component = weight
        elif candidate_level > 0:
            component = weight * (candidate_level / req_min_level)
        else:
            component = 0.0

        earned += component
        details.append(
            {
                "language": req.get("language"),
                "required_level": req.get("min_level", ""),
                "candidate_level_score": candidate_level,
                "required_level_score": req_min_level,
                "match": component >= (0.8 * weight if weight > 0 else 0),
            }
        )

    return round(max(0.0, min(1.0, earned / total_weight)), 4), details


def score_language_quality(candidate: dict) -> float:
    action = candidate.get("action_verb_scores") or {}
    buzz = candidate.get("buzzword_analysis") or {}

    if isinstance(action, dict) and "verb_score" in action:
        try:
            base = float(action.get("verb_score", 0)) / 100.0
        except (TypeError, ValueError):
            base = 0.5
    else:
        count = 0
        if isinstance(action, dict):
            count = int(action.get("count", action.get("strong_count", 0)) or 0)
        base = min(1.0, 0.45 + (0.06 * count))

    buzz_count = 0
    if isinstance(buzz, dict):
        buzz_count = int(buzz.get("count", 0) or 0)
    penalty = min(0.20, buzz_count * 0.03)
    return round(max(0.0, min(1.0, base - penalty)), 4)


def score_location(candidate: dict, job: dict) -> float:
    if bool(job.get("remote_ok", False)):
        return 1.0

    candidate_loc = (candidate.get("location") or candidate.get("city") or "").strip().lower()
    job_loc = (job.get("location") or "").strip().lower()
    if not job_loc or job_loc in {"remote", "télétravail", "distanciel"}:
        return 1.0
    if not candidate_loc:
        return 0.5
    return 1.0 if _similarity(candidate_loc, job_loc) >= 0.75 else 0.3


def get_recommendation(score: float) -> str:
    if score >= 0.75:
        return "Strong Match"
    if score >= 0.55:
        return "Potential Match"
    if score >= 0.35:
        return "Weak Match"
    return "Not Recommended"


def score_candidate(candidate: dict, job: dict, weights: dict) -> dict:
    w = _normalize_weights(weights)
    skills_result = score_skills(candidate, job)
    experience_score, experience_reason = score_experience_relevance(candidate, job)
    achievements_score = _achievements_score(candidate)
    language_quality_score = score_language_quality(candidate)
    language_match_score, language_details = score_language_match(candidate, job)
    education_score = score_education(candidate, job)
    location_score = score_location(candidate, job)

    total = (
        (w["skills_match"] * skills_result["score"])
        + (w["experience_relevance"] * experience_score)
        + (w["achievements"] * achievements_score)
        + (w["language_quality"] * language_quality_score)
        + (w["language_match"] * language_match_score)
        + (w["education"] * education_score)
        + (w["location"] * location_score)
    )

    critical_missing = skills_result["critical_missing"]
    if critical_missing:
        total *= 0.90 ** len(critical_missing)

    confidence_multiplier_applied = False
    if _confidence_value(candidate) < 60.0:
        total *= 0.85
        confidence_multiplier_applied = True

    total = round(max(0.0, min(1.0, total)), 4)
    flags = candidate.get("flags") if isinstance(candidate.get("flags"), list) else []
    student_profile_detected = candidate.get("experience_years", 0) in (0, 0.0) and bool(candidate.get("projects"))

    row = {
        "cv_id": candidate.get("cv_id"),
        "total_score": total,
        "final_score": total,  # backward compatibility
        "skills_score": round(skills_result["score"], 4),
        "experience_score": round(experience_score, 4),
        "achievements_score": round(achievements_score, 4),
        "language_quality_score": round(language_quality_score, 4),
        "language_match_score": round(language_match_score, 4),
        "education_score": round(education_score, 4),
        "location_score": round(location_score, 4),
        "matched_skills": skills_result["matched"],
        "missing_skills": skills_result["missing_skills"],
        "critical_missing": critical_missing,
        "missing_critical": critical_missing,  # backward compatibility
        "language_details": language_details,
        "experience_relevance_reason": experience_reason,
        "flags": flags,
        "confidence_multiplier_applied": confidence_multiplier_applied,
        "student_profile_detected": student_profile_detected,
        "missing_critical_count": len(critical_missing),
        "semantic_score": None,
        "recommendation": get_recommendation(total),
        # backward compatibility field for old clients
        "language_score": round((language_quality_score + language_match_score) / 2.0, 4),
    }
    return row


def rank_candidates(candidates: list, job: dict, weights: dict) -> list:
    scored = [score_candidate(candidate, job, weights) for candidate in candidates]
    scored.sort(key=lambda row: row["total_score"], reverse=True)
    for idx, row in enumerate(scored, start=1):
        row["rank"] = idx
    return scored

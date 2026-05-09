"""
CV Scoring Service
Notebook-parity scoring with stable backend API outputs.
"""
from difflib import SequenceMatcher
import re
from typing import Any


DEFAULT_WEIGHTS = {
    "skills": 0.35,
    "experience": 0.25,
    "education": 0.15,
    "language": 0.15,
    "location": 0.10,
}

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


def _required_languages(job: dict) -> list[dict]:
    required = _ensure_list(job.get("required_languages"))
    if required:
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
        total = sum(item["weight"] for item in normalized)
        if normalized and total <= 0:
            equal = round(1.0 / len(normalized), 2)
            return [{**item, "weight": equal} for item in normalized]
        if normalized and total > 0:
            return [{**item, "weight": item["weight"] / total} for item in normalized]
        return []

    legacy = _ensure_list(job.get("languages_required"))
    if not legacy:
        return []
    normalized = []
    equal = 1.0 / len(legacy)
    for entry in legacy:
        if not isinstance(entry, dict):
            continue
        language = str(entry.get("language", "")).strip()
        if not language:
            continue
        normalized.append(
            {
                "language": language,
                "min_level": str(entry.get("level", "")).strip(),
                "weight": equal,
            }
        )
    return normalized


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
        count = int(qa.get("count") or 0)
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
        return {"score": 0.5, "matched": [], "missing_skills": [], "missing_critical": []}

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

    missing_critical = [crit for crit in critical if not any(_match(c_skill, crit) for c_skill in cand_skills)]
    score = earned / total_weight if total_weight else 0.0
    return {
        "score": round(min(score, 1.0), 4),
        "matched": matched,
        "missing_skills": missing,
        "missing_critical": missing_critical,
    }


def score_experience(candidate: dict, job: dict) -> float:
    candidate_years = float(candidate.get("experience_years") or 0)
    required_years = float(job.get("experience_required_years") or 0)

    years_score = 1.0
    if required_years > 0:
        years_score = min(1.0, candidate_years / required_years) if candidate_years > 0 else 0.10

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
        matched = sum(1 for skill in required_skills if skill and (skill in experience_text or any(_match(skill, token) for token in experience_text.split())))
        relevance_score = matched / len(required_skills)
    else:
        relevance_score = 0.20 if not experience_text else 0.50

    achievements_score = _achievements_score(candidate)
    combined = (0.55 * years_score) + (0.30 * relevance_score) + (0.15 * achievements_score)
    return round(max(0.0, min(1.0, combined)), 4)


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


def score_language(candidate: dict, job: dict) -> float:
    required = _required_languages(job)
    if not required:
        return 1.0

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
    for req in required:
        req_name = _normalize_language_name(str(req.get("language", "")))
        req_min_level = _normalize_language_level(str(req.get("min_level", "")))
        weight = float(req.get("weight", 1.0))
        candidate_level = spoken_levels.get(req_name, 0)

        if req_min_level <= 0:
            earned += weight if candidate_level > 0 else 0.6 * weight
        elif candidate_level >= req_min_level:
            earned += weight
        elif candidate_level > 0:
            earned += weight * (candidate_level / req_min_level)

    return round(max(0.0, min(1.0, earned / total_weight)), 4)


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
    w = {**DEFAULT_WEIGHTS, **(weights or {})}

    skills_result = score_skills(candidate, job)
    s_skills = skills_result["score"]
    s_exp = score_experience(candidate, job)
    s_edu = score_education(candidate, job)
    s_lang = score_language(candidate, job)
    s_loc = score_location(candidate, job)

    final = (
        (w["skills"] * s_skills)
        + (w["experience"] * s_exp)
        + (w["education"] * s_edu)
        + (w["language"] * s_lang)
        + (w["location"] * s_loc)
    )

    n_missing_critical = len(skills_result["missing_critical"])
    if n_missing_critical > 0:
        final *= 0.90 ** n_missing_critical

    if _confidence_value(candidate) < 60.0:
        final *= 0.85

    final = round(max(0.0, min(1.0, final)), 4)

    return {
        "cv_id": candidate.get("cv_id"),
        "final_score": final,
        "skills_score": round(s_skills, 4),
        "experience_score": round(s_exp, 4),
        "education_score": round(s_edu, 4),
        "language_score": round(s_lang, 4),
        "location_score": round(s_loc, 4),
        "matched_skills": skills_result["matched"],
        "missing_skills": skills_result["missing_skills"],
        "missing_critical": skills_result["missing_critical"],
        "recommendation": get_recommendation(final),
    }


def rank_candidates(candidates: list, job: dict, weights: dict) -> list:
    scored = [score_candidate(candidate, job, weights) for candidate in candidates]
    scored.sort(key=lambda row: row["final_score"], reverse=True)
    for idx, row in enumerate(scored, start=1):
        row["rank"] = idx
    return scored

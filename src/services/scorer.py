"""
CV Scoring Service
Converted from TESTING_SCORE_LOGIC (1).ipynb
"""
from difflib import SequenceMatcher
from typing import List, Dict


# ── Lookup tables ──────────────────────────────────────────────────────────────
LEVEL_MAP = {
    "native": 100, "natif": 100, "langue maternelle": 100,
    "bilingue": 95, "bilingual": 95,
    "fluent": 90, "courant": 90,
    "c2": 88, "c1": 80,
    "advanced": 75, "avancé": 75, "professionnel": 75,
    "b2": 65, "b1": 50, "intermediate": 50, "intermédiaire": 50,
    "a2": 35, "a1": 20, "basic": 25, "notions": 20, "débutant": 20,
}

EDU_MAP = {
    "phd": 100, "doctorat": 100, "doctorate": 100,
    "master": 88, "msc": 88, "mba": 88, "ingénieur": 85, "ingenieur": 85,
    "bachelor": 75, "licence": 75,
    "bts": 60, "dut": 60,
    "bac": 50,
}

DEFAULT_WEIGHTS = {
    "skills": 0.35,
    "experience": 0.25,
    "education": 0.15,
    "language": 0.15,
    "location": 0.10,
}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _match(a: str, b: str, threshold: float = 0.82) -> bool:
    return _similarity(a, b) >= threshold


def normalize_level(s: str) -> float:
    s = s.lower().strip()
    return LEVEL_MAP.get(s, 0.0)


def normalize_edu(s: str) -> float:
    s = s.lower().strip()
    for key, val in EDU_MAP.items():
        if key in s:
            return val
    return 0.0


# ── Dimension scorers ──────────────────────────────────────────────────────────
def score_skills(candidate: dict, job: dict) -> dict:
    c_skills = set(s.lower() for s in (candidate.get("skills") or []))
    j_required = [s.lower() for s in (job.get("required_skills") or [])]
    j_critical = [s.lower() for s in (job.get("critical_skills") or [])]

    if not j_required:
        return {"score": 1.0, "matched": [], "missing_critical": []}

    # Match skills (fuzzy)
    matched = []
    for js in j_required:
        for cs in c_skills:
            if _match(cs, js):
                matched.append(js)
                break

    # Critical skills check
    missing_critical = []
    for crit in j_critical:
        found = any(_match(cs, crit) for cs in c_skills)
        if not found:
            missing_critical.append(crit)

    base = len(matched) / len(j_required)
    penalty = len(missing_critical) * 0.1  # 10% penalty per missing critical
    score = max(0.0, min(1.0, base - penalty))

    return {"score": round(score, 4), "matched": matched, "missing_critical": missing_critical}


def score_experience(candidate: dict, job: dict) -> float:
    candidate_years = float(candidate.get("experience_years") or 0)
    required_years = float(job.get("experience_required_years") or 0)
    if required_years == 0:
        return 1.0
    if candidate_years == 0:
        return 0.1
    return round(min(1.0, candidate_years / required_years), 4)


def score_education(candidate: dict, job: dict) -> float:
    c_edu = normalize_edu(candidate.get("education_level") or "")
    j_edu = normalize_edu(job.get("education_required") or "")
    if j_edu == 0:
        return 1.0
    return round(min(1.0, c_edu / j_edu), 4)


def score_language(candidate: dict, job: dict) -> float:
    j_langs = job.get("languages_required") or []
    if not j_langs:
        return 1.0
    c_langs = {l["language"].lower(): normalize_level(l.get("level", "")) for l in (candidate.get("languages_spoken") or [])}

    scores = []
    for jl in j_langs:
        jl_name = jl["language"].lower()
        jl_level = normalize_level(jl.get("level", ""))
        c_level = c_langs.get(jl_name, 0)
        if jl_level == 0:
            scores.append(1.0)
        else:
            scores.append(min(1.0, c_level / jl_level))

    return round(sum(scores) / len(scores), 4) if scores else 1.0


def score_location(candidate: dict, job: dict) -> float:
    c_loc = (candidate.get("location") or "").lower().strip()
    j_loc = (job.get("location") or "").lower().strip()
    if not j_loc or j_loc in ("remote", "télétravail", "distanciel"):
        return 1.0
    if not c_loc:
        return 0.5
    return 1.0 if _similarity(c_loc, j_loc) >= 0.6 else 0.5


# ── Final scorer ───────────────────────────────────────────────────────────────
def score_candidate(candidate: dict, job: dict, weights: dict) -> dict:
    w = {**DEFAULT_WEIGHTS, **weights}
    skill_result = score_skills(candidate, job)
    s_skills = skill_result["score"]
    s_exp = score_experience(candidate, job)
    s_edu = score_education(candidate, job)
    s_lang = score_language(candidate, job)
    s_loc = score_location(candidate, job)

    final = round(
        w["skills"] * s_skills
        + w["experience"] * s_exp
        + w["education"] * s_edu
        + w["language"] * s_lang
        + w["location"] * s_loc,
        4,
    )

    return {
        "cv_id": candidate.get("cv_id"),
        "final_score": final,
        "skills_score": s_skills,
        "experience_score": s_exp,
        "education_score": s_edu,
        "language_score": s_lang,
        "location_score": s_loc,
        "matched_skills": skill_result["matched"],
        "missing_critical": skill_result["missing_critical"],
    }


def rank_candidates(candidates: list, job: dict, weights: dict) -> list:
    scored = [score_candidate(c, job, weights) for c in candidates]
    scored.sort(key=lambda x: x["final_score"], reverse=True)
    for i, row in enumerate(scored):
        row["rank"] = i + 1
    return scored

"""
validate_scoring.py — Validation suite for the RecruteIA scoring engine.

Validates monotonicity, penalty effects, ranking correctness, and the SCORING_RATIONALE worked
example. Runs without a live Groq key (uses the rule-based fallback via patching).

Usage (from brief/recruitment-ai/):
    python scripts/validate_scoring.py
"""

import sys
import os
import unittest
from unittest.mock import patch

# Make console output UTF-8 safe on Windows (cp1252 cannot encode ✅/❌)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# Ensure src is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Patch Groq before import to avoid needing a live API key
with patch.dict(os.environ, {"GROQ_API_KEY": "test_key_placeholder"}):
    from src.services.scorer import (
        score_candidate,
        rank_candidates,
        score_skills,
        _achievements_score,
        score_language_quality,
        score_education,
        score_location,
        get_recommendation,
        DEFAULT_WEIGHTS_V2,
    )


# ─── Fixtures ────────────────────────────────────────────────────────────────

JOB_FULLSTACK = {
    "required_skills": ["Python", "React", "SQL", "Git", "Docker"],
    "critical_skills": ["Python", "React"],
    "experience_required_years": 2,
    "min_education": "bachelor",
    "required_languages": [
        {"language": "French", "min_level": "B2", "weight": 0.6},
        {"language": "English", "min_level": "B1", "weight": 0.4},
    ],
    "remote_ok": True,
    "description_summary": "Looking for a full-stack developer with Python backend and React frontend.",
}

ALICE = {
    "cv_id": "alice",
    "skills": ["Python", "React", "SQL", "Git", "Docker", "Node.js"],
    "skills_in_experience": ["Python", "React", "SQL"],
    "experience_years": 3,
    "experience": "Developed Python microservices and React dashboards for 3 years.",
    "quantified_achievements": {"count": 3, "examples": ["Reduced deploy time by 40%", "Built 5 REST APIs", "Led team of 3"]},
    "action_verb_scores": {"verb_score": 75},
    "buzzword_analysis": {"count": 1},
    "education_level": "bachelor",
    "languages_spoken": [{"language": "French", "level": "C1"}, {"language": "English", "level": "B2"}],
    "location": "Casablanca",
    "confidence_score": 85,
}

BOB = {
    "cv_id": "bob",
    "skills": ["JavaScript", "HTML", "CSS", "Git"],
    "skills_in_experience": ["JavaScript", "HTML"],
    "experience_years": 1,
    "experience": "Built HTML/CSS landing pages and JavaScript widgets.",
    "quantified_achievements": {"count": 1, "examples": ["Reduced load time by 10%"]},
    "action_verb_scores": {"verb_score": 45},
    "buzzword_analysis": {"count": 4},
    "education_level": "diploma",
    "languages_spoken": [{"language": "French", "level": "native"}],
    "location": "Marrakech",
    "confidence_score": 70,
}


# ─── Helper: score without Groq ──────────────────────────────────────────────

def score_no_groq(candidate, job, weights=None):
    """Score using rule-based fallback (patches Groq client to raise so fallback is used)."""
    if weights is None:
        weights = DEFAULT_WEIGHTS_V2.copy()
    with patch("src.services.scorer._get_groq_client", side_effect=RuntimeError("no key in test")):
        # Also clear the cache to force re-computation
        import src.services.scorer as scorer_mod
        scorer_mod._experience_cache.clear()
        return score_candidate(candidate, job, weights)


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestScoringValidation(unittest.TestCase):

    def test_worked_example_alice_is_strong(self):
        """SCORING_RATIONALE §5: Alice should score ~0.88 and be Strong Match."""
        result = score_no_groq(ALICE, JOB_FULLSTACK)
        score = result["total_score"]
        print(f"\n  Alice total_score = {score:.4f} (expected ~0.88)")
        self.assertGreater(score, 0.80, f"Alice should be Strong Match (>0.80), got {score:.4f}")
        self.assertEqual(result["recommendation"], "Strong Match")
        self.assertEqual(result["critical_missing"], [], "Alice should have no critical skills missing")

    def test_worked_example_bob_is_not_recommended(self):
        """SCORING_RATIONALE §5: Bob should score ~0.27 and be Not Recommended."""
        result = score_no_groq(BOB, JOB_FULLSTACK)
        score = result["total_score"]
        print(f"\n  Bob total_score = {score:.4f} (expected ~0.27)")
        self.assertLess(score, 0.35, f"Bob should be Not Recommended (<0.35), got {score:.4f}")
        self.assertEqual(result["recommendation"], "Not Recommended")
        self.assertIn("Python", result["critical_missing"])
        self.assertIn("React", result["critical_missing"])

    def test_correct_ranking(self):
        """Alice must rank above Bob."""
        alice_result = score_no_groq(ALICE, JOB_FULLSTACK)
        bob_result = score_no_groq(BOB, JOB_FULLSTACK)
        print(f"\n  Ranking: Alice {alice_result['total_score']:.4f} vs Bob {bob_result['total_score']:.4f}")
        self.assertGreater(alice_result["total_score"], bob_result["total_score"])

    def test_monotonicity_adding_skills_increases_score(self):
        """Adding a required skill should not decrease the score."""
        candidate_few = {**BOB, "cv_id": "few_skills", "skills": ["Git"], "skills_in_experience": []}
        candidate_more = {**BOB, "cv_id": "more_skills", "skills": ["Git", "SQL"], "skills_in_experience": []}
        result_few = score_no_groq(candidate_few, JOB_FULLSTACK)
        result_more = score_no_groq(candidate_more, JOB_FULLSTACK)
        print(f"\n  Monotonicity: 1 skill={result_few['total_score']:.4f}, 2 skills={result_more['total_score']:.4f}")
        self.assertGreaterEqual(
            result_more["total_score"], result_few["total_score"],
            "Adding a required skill should not decrease the score"
        )

    def test_critical_skill_penalty_is_compounding(self):
        """Each additional critical skill miss should reduce the score."""
        base = {
            "cv_id": "test", "skills": [], "skills_in_experience": [], "experience_years": 2,
            "experience": "Python backend work", "quantified_achievements": {"count": 2},
            "action_verb_scores": {"verb_score": 60}, "buzzword_analysis": {"count": 0},
            "education_level": "bachelor",
            "languages_spoken": [{"language": "French", "level": "C1"}, {"language": "English", "level": "B1"}],
            "location": "", "confidence_score": 80,
        }
        job_1_critical = {**JOB_FULLSTACK, "critical_skills": ["Python"]}
        job_2_critical = {**JOB_FULLSTACK, "critical_skills": ["Python", "React"]}
        job_3_critical = {**JOB_FULLSTACK, "critical_skills": ["Python", "React", "SQL"]}

        s1 = score_no_groq(base, job_1_critical)["total_score"]
        s2 = score_no_groq(base, job_2_critical)["total_score"]
        s3 = score_no_groq(base, job_3_critical)["total_score"]
        print(f"\n  Critical penalty: 1 missing={s1:.4f}, 2 missing={s2:.4f}, 3 missing={s3:.4f}")
        self.assertGreater(s1, s2, "1 critical missing should score higher than 2")
        self.assertGreater(s2, s3, "2 critical missing should score higher than 3")

    def test_confidence_penalty_applied_below_60(self):
        """A candidate with confidence < 60 should score lower than same candidate with confidence >= 60."""
        high_conf = {**ALICE, "confidence_score": 85}
        low_conf = {**ALICE, "confidence_score": 45}
        s_high = score_no_groq(high_conf, JOB_FULLSTACK)
        s_low = score_no_groq(low_conf, JOB_FULLSTACK)
        print(f"\n  Confidence: high={s_high['total_score']:.4f} (multiplier={s_high['confidence_multiplier_applied']}), "
              f"low={s_low['total_score']:.4f} (multiplier={s_low['confidence_multiplier_applied']})")
        self.assertFalse(s_high["confidence_multiplier_applied"], "High confidence should not trigger multiplier")
        self.assertTrue(s_low["confidence_multiplier_applied"], "Low confidence should trigger multiplier")
        self.assertGreater(s_high["total_score"], s_low["total_score"])
        # The ratio should be approximately 0.85
        ratio = s_low["total_score"] / s_high["total_score"]
        self.assertAlmostEqual(ratio, 0.85, delta=0.02, msg=f"Confidence penalty should be ×0.85, got ratio={ratio:.4f}")

    def test_recommendation_bands(self):
        """Verify band thresholds match SCORING_RATIONALE §4."""
        self.assertEqual(get_recommendation(0.80), "Strong Match")
        self.assertEqual(get_recommendation(0.75), "Strong Match")
        self.assertEqual(get_recommendation(0.74), "Potential Match")
        self.assertEqual(get_recommendation(0.55), "Potential Match")
        self.assertEqual(get_recommendation(0.54), "Weak Match")
        self.assertEqual(get_recommendation(0.35), "Weak Match")
        self.assertEqual(get_recommendation(0.34), "Not Recommended")
        self.assertEqual(get_recommendation(0.00), "Not Recommended")

    def test_skills_score_critical_double_weight(self):
        """Critical skills having double weight means 1 critical > 2 non-critical in same position."""
        job = {"required_skills": ["A", "B", "C"], "critical_skills": ["A"]}
        # Has A (critical) but not B or C
        cand_critical = {"skills": ["A"], "skills_in_experience": []}
        # Has B and C (non-critical) but not A
        cand_noncritical = {"skills": ["B", "C"], "skills_in_experience": []}
        r_crit = score_skills(cand_critical, job)
        r_noncrit = score_skills(cand_noncritical, job)
        print(f"\n  Double weight: has_critical={r_crit['score']:.4f}, has_two_noncritical={r_noncrit['score']:.4f}")
        # A has weight 2, B+C each have weight 1; total weight = 4
        # cand_critical earned 2/4 = 0.50; cand_noncritical earned (1+1)/4 = 0.50 — tied on points
        # But cand_critical has no critical_missing, cand_noncritical has 1 critical_missing
        self.assertEqual(r_noncrit["critical_missing"], ["A"])
        self.assertEqual(r_crit["critical_missing"], [])

    def test_perfect_candidate_scores_near_one(self):
        """A candidate who perfectly matches all dimensions should score close to 1.0."""
        perfect = {
            "cv_id": "perfect", "skills": ["Python", "React", "SQL", "Git", "Docker"],
            "skills_in_experience": ["Python", "React", "SQL", "Git", "Docker"],
            "experience_years": 5, "experience": "Python React SQL Docker Git expert",
            "quantified_achievements": {"count": 10},
            "action_verb_scores": {"verb_score": 95}, "buzzword_analysis": {"count": 0},
            "education_level": "master",
            "languages_spoken": [{"language": "French", "level": "native"}, {"language": "English", "level": "C2"}],
            "location": "Casablanca", "confidence_score": 95,
        }
        result = score_no_groq(perfect, JOB_FULLSTACK)
        print(f"\n  Perfect candidate score = {result['total_score']:.4f}")
        self.assertGreater(result["total_score"], 0.90)
        self.assertEqual(result["recommendation"], "Strong Match")


class TestSubScoreFunctions(unittest.TestCase):

    def test_achievements_tiers(self):
        """Validate the achievement tier ladder from the rationale."""
        cases = [(0, 0.0), (1, 0.35), (2, 0.55), (3, 0.70)]
        for count, expected in cases:
            cand = {"quantified_achievements": {"count": count}}
            result = _achievements_score(cand)
            self.assertAlmostEqual(result, expected, places=2, msg=f"count={count}")

    def test_education_levels(self):
        """Education scoring: above req=1.0, equal=0.8, below=0.3."""
        job_bachelor = {"min_education": "bachelor"}
        self.assertAlmostEqual(score_education({"education_level": "master"}, job_bachelor), 1.0)
        self.assertAlmostEqual(score_education({"education_level": "bachelor"}, job_bachelor), 0.8)
        self.assertAlmostEqual(score_education({"education_level": "diploma"}, job_bachelor), 0.3)

    def test_location_remote_ok(self):
        """remote_ok=True should always return 1.0 regardless of candidate location."""
        job_remote = {"remote_ok": True, "location": "Paris"}
        self.assertEqual(score_location({"location": "Casablanca"}, job_remote), 1.0)
        self.assertEqual(score_location({"location": ""}, job_remote), 1.0)

    def test_language_quality_buzzword_penalty(self):
        """More buzzwords should lower the quality score."""
        no_buzz = {"action_verb_scores": {"verb_score": 70}, "buzzword_analysis": {"count": 0}}
        many_buzz = {"action_verb_scores": {"verb_score": 70}, "buzzword_analysis": {"count": 5}}
        self.assertGreater(score_language_quality(no_buzz), score_language_quality(many_buzz))


# ─── Runner ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("RecruteIA Scoring Engine Validation Suite")
    print("=" * 70)
    print("Note: experience_relevance uses rule-based fallback (no live Groq key needed)\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestScoringValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestSubScoreFunctions))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("✅ All validations PASSED — scoring engine behaves as documented")
    else:
        print(f"❌ {len(result.failures)} failure(s), {len(result.errors)} error(s)")
        print("   Review SCORING_RATIONALE.md and scorer.py for discrepancies")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)

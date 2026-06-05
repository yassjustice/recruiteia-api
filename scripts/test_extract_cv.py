"""
test_extract_cv.py — iterate on CV extraction quality for a hard two-column CV.
Runs the real extractor functions on a saved text sample (no PDF needed).
Usage (from brief/recruitment-ai/):  python scripts/test_extract_cv.py [path_to_txt]
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.services.extractor import (
    detect_language, extract_contact_info, parse_sections_groq,
    normalize_skills, normalize_spaced_text, _fix_mojibake, _normalize_languages,
)

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "data", "test", "yassir_cv.txt")
with open(path, encoding="utf-8") as _f:
    text = _fix_mojibake(normalize_spaced_text(_f.read()))

lang = detect_language(text)
groq = parse_sections_groq(text, lang)
contact = extract_contact_info(text, groq)

print("=" * 70)
print("LANG:", lang)
print("NAME:", contact.get("name") or groq.get("name"))
print("EMAIL:", contact.get("email"))
print("PHONE:", contact.get("phone"), "   <-- expected +212605616855")
print("LOCATION:", contact.get("location"))
print("LINKEDIN:", contact.get("linkedin"))
print("TITLE/PROFILE:", _fix_mojibake(groq.get("profile") or "")[:140])
print("EXP_YEARS:", groq.get("experience_years"), " EDU_LEVEL:", groq.get("education_level"))
print("\nEXPERIENCE:")
for e in groq.get("experience", []):
    print("  •", _fix_mojibake(str(e)))
print("\nEDUCATION:")
for e in groq.get("education", []):
    print("  •", _fix_mojibake(str(e)))
print("\nPROJECTS:")
for e in groq.get("projects", []):
    print("  •", _fix_mojibake(str(e)))
print("\nSKILLS:", normalize_skills(groq.get("skills", [])))
print("LANGUAGES:", _normalize_languages(groq.get("languages_spoken", [])))
print("=" * 70)

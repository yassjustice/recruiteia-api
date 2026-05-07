"""
Job Description Parser
Extracts structured fields from raw JD text using Groq.
"""
import re
import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
GROQ_MODEL = "llama-3.3-70b-versatile"


def extract_job_offer(text: str, lang: str = "fr") -> dict:
    lang_hint = "The job description is in French." if lang == "fr" else "The job description is in English."
    prompt = f"""You are a job description parser. {lang_hint}
Return ONLY a valid JSON object, no explanation, no markdown.

{{
  "title": "job title",
  "domain": "industry/domain (e.g. IT, Finance, Marketing)",
  "job_type": "CDI|CDD|Stage|Freelance",
  "location": "city or remote",
  "required_skills": ["list of required technical skills"],
  "critical_skills": ["must-have skills — missing these is disqualifying"],
  "soft_skills": ["interpersonal skills required"],
  "experience_required_years": 0,
  "education_required": "Bachelor|Master|PhD|BTS|Bac|Any",
  "languages_required": [{{"language": "French", "level": "Fluent"}}]
}}

Job description:
\"\"\"
{text[:4000]}
\"\"\"
"""
    try:
        resp = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}

import json
from agents import Runner
from core.ai_agents import resume_master_agent
import asyncio

def safe_json_load(text: str, default: dict):
    try:
        return json.loads(text)
    except Exception:
        return default

def normalize_skill(skill: str) -> str:
    if not skill or not isinstance(skill, str):
        return ""
    return (
        skill.strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
    )

def normalize_skill_list(skills):
    if not skills:
        return []
    return sorted(list({normalize_skill(s) for s in skills if normalize_skill(s)}))



REQUIREMENT_PARSER_INSTRUCTIONS = """
You are a recruiter requirement parser.

Extract structured hiring requirements from the text.

Return ONLY valid JSON in this format:
{
  "role": string or null,
  "required_skills": [string],
  "min_experience": number or null,
  "nice_to_have": [string],
  "seniority": "junior" | "mid" | "senior" | null
}

Rules:
- Skills must be concise (e.g. "python", not "expert in python")
- Infer seniority if words like junior, mid, senior, lead appear
- min_experience should be a number (e.g. 3, 5)
- If something is not mentioned, return null or empty list
- Do NOT add explanations
"""


async def parse_requirement(requirement_text: str) -> dict:
    """
    Parse recruiter requirement into structured, normalized format.
    """

    prompt = f"""
Recruiter requirement:
{requirement_text}

{REQUIREMENT_PARSER_INSTRUCTIONS}
"""

    result = await Runner.run(resume_master_agent, prompt)

    try:
        raw = json.loads(result.final_output)
    except Exception:
        # fallback (very important for stability)
        raw = {
            "role": None,
            "required_skills": [],
            "min_experience": None,
            "nice_to_have": [],
            "seniority": None
        }

    parsed = {
        "role": raw.get("role"),
        "required_skills": normalize_skill_list(raw.get("required_skills", [])),
        "min_experience": raw.get("min_experience"),
        "nice_to_have": normalize_skill_list(raw.get("nice_to_have", [])),
        "seniority": raw.get("seniority")
    }

    return parsed




# core/profile_builder.py
import profile
import re
from datetime import datetime
import json
from agents import Runner
from core.ai_agents import (
    personal_info_agent,
    skills_agent,
    experience_agent,
    education_agent,
    projects_agent,
    programming_language_agent
)

def parse_duration_to_years(duration: str) -> float:
    if not duration:
        return 0.0

    duration = duration.lower()
    end_date = datetime.now()

    try:
        # Match patterns like "Jan 2021 – Mar 2023"
        parts = re.split(r"–|-", duration)
        start_part = parts[0].strip()
        end_part = parts[1].strip() if len(parts) > 1 else "present"

        start_date = datetime.strptime(start_part[:7], "%b %Y")

        if "present" in end_part:
            final_date = end_date
        else:
            final_date = datetime.strptime(end_part[:7], "%b %Y")

        months = (final_date.year - start_date.year) * 12 + (final_date.month - start_date.month)
        return round(months / 12, 1)

    except Exception:
        # fallback to year-only logic
        years = re.findall(r"\b(19|20)\d{2}\b", duration)
        if len(years) >= 2:
            return max(int(years[-1]) - int(years[0]), 0)
        return 0.0


# def parse_duration_to_years(duration: str) -> float:
#     """
#     Converts duration text like:
#     - 'Jan 2021 – Mar 2023'
#     - '2020 - Present'
#     - 'Jun 2019 – 2021'
#     into total years (float)
#     """
#     if not duration:
#         return 0.0

#     duration = duration.lower()

#     # Handle 'present'
#     end_year = datetime.now().year

#     years = re.findall(r"\b(19|20)\d{2}\b", duration)

#     if not years:
#         return 0.0

#     try:
#         start_year = int(years[0])
#         final_year = int(years[-1]) if "present" not in duration else end_year
#         return max(final_year - start_year, 0)
#     except Exception:
#         return 0.0

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
    normalized = [normalize_skill(s) for s in skills]
    # remove empties + deduplicate
    return sorted(list({s for s in normalized if s}))


def safe_json_load(text: str, default):
    try:
        return json.loads(text)
    except Exception:
        return default


def extract_fallback_name(resume_text: str) -> str:
    for line in resume_text.splitlines():
        clean = line.strip()
        if len(clean) >= 3 and clean.isupper():
            return clean.title()
        if len(clean.split()) >= 2 and clean[0].isalpha():
            return clean.title()
    return None


async def build_candidate_profile(resume_text: str) -> dict:
    profile = {}

    # 1️⃣ Name
    try:
        name_result = await Runner.run(personal_info_agent, resume_text)
        name_data = safe_json_load(name_result.final_output, {})
        profile["name"] = name_data.get("name")
    except Exception:
        profile["name"] = None

    if not name_data:
        name_data = extract_fallback_name(resume_text)

    profile["name"] = name_data or "Candidate"


    # Skills
    skills_result = await Runner.run(skills_agent, resume_text)
    skills_data = safe_json_load(
        skills_result.final_output,
        {"technical_skills": [], "soft_skills": []}
    )

    profile["skills"] = {
        "technical_skills": normalize_skill_list(
            skills_data.get("technical_skills", [])
        ),
        "soft_skills": normalize_skill_list(
            skills_data.get("soft_skills", [])
        )
    }
    print(profile["skills"]["technical_skills"])
    print(profile["skills"]["soft_skills"])



    # 3️⃣ Experience (UPDATED)
    exp_result = await Runner.run(experience_agent, resume_text)
    exp_data = safe_json_load(exp_result.final_output, {"experience": []})

    experience_entries = exp_data.get("experience", [])
    total_years = 0.0

    for exp in experience_entries:
        duration = exp.get("duration", "")
        total_years += parse_duration_to_years(duration)

    profile["experience"] = {
        "entries": experience_entries,
        "years": round(total_years, 1)
    }

    # 4️⃣ Education
    edu_result = await Runner.run(education_agent, resume_text)
    profile["education"] = safe_json_load(
        edu_result.final_output,
        {"education": []}
    )

    # 5️⃣ Projects
    proj_result = await Runner.run(projects_agent, resume_text)
    profile["projects"] = safe_json_load(
        proj_result.final_output,
        {"projects": []}
    )

    # 6️⃣ Languages
    lang_result = await Runner.run(programming_language_agent, resume_text)
    profile["languages"] = safe_json_load(
        lang_result.final_output,
        {"programming_languages": []}
    )

    return profile


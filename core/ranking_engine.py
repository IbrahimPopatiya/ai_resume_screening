# core/ranking_engine.py

WEIGHTS = {
    "skills": 35,
    "experience": 25,
    "projects": 15,
    "languages": 10,
    "domain": 15
}


def normalize_skills(skills):
    return set(
        s.strip().lower().replace(" ", "")
        for s in skills
        if isinstance(s, str)
    )




def score_candidate(profile: dict, requirement: dict) -> dict:
    """
    Deterministic scoring engine.
    Returns score + breakdown + explanation.
    """

    # Fixed system weights (v1)
    WEIGHTS = {
        "skills": 35,
        "experience": 25,
        "projects": 15,
        "languages": 10,
        "domain": 15
    }

    breakdown = {}
    strong_points = []
    weak_points = []
    reasoning_parts = []

    # ---------------- SKILLS ----------------

    required = normalize_skills(requirement.get("required_skills", []))
    nice = normalize_skills(requirement.get("nice_to_have", []))
    candidate = normalize_skills(
        profile.get("skills", {}).get("technical_skills", [])
    )

    matched_required = required & candidate
    matched_nice = nice & candidate

    # Required skills score (dominant)
    if required:
        required_ratio = len(matched_required) / len(required)
    else:
        required_ratio = 1.0

    # Nice-to-have bonus (max +30%)
    nice_bonus = min(len(matched_nice) * 0.1, 0.3)

    skill_score = min(required_ratio + nice_bonus, 1.0) * 100
    breakdown["skills"] = round(skill_score * WEIGHTS["skills"] /100,1)

    # Explainability
    if matched_required:
        strong_points.append(
            f"Matches required skills: {', '.join(sorted(matched_required))}"
        )
        reasoning_parts.append(
            f"Strong skill match ({len(matched_required)}/{len(required)})"
        )

    if matched_nice:
        strong_points.append(
            f"Nice-to-have skills: {', '.join(sorted(matched_nice))}"
        )

    missing = required - matched_required
    if missing:
        weak_points .append(
            f"Missing required skills: {', '.join(sorted(missing))}"
        )


    # ---------------- EXPERIENCE ----------------
    min_exp = requirement.get("min_experience")
    candidate_exp = profile.get("experience", {}).get("years", 0)

    if min_exp:
        exp_ratio = min(candidate_exp / min_exp, 1.0)
    else:
        exp_ratio = 1.0

    experience_score = round(exp_ratio * WEIGHTS["experience"], 1)
    breakdown["experience"] = experience_score

    if exp_ratio >= 0.6:
        strong_points.append(f"{candidate_exp} years relevant experience")
        reasoning_parts.append(f"{candidate_exp} years of experience vs required {min_exp}")
    else:
        weak_points.append("Experience below requirement")

    # ---------------- PROJECT RELEVANCE ----------------
    projects = profile.get("projects", {}).get("projects", [])
    project_score = 0

    if projects and required:
        max_relevance = 0

        for proj in projects:
            proj_skills = set(
                s.lower() for s in proj.get("skills", [])
            )
            matched = proj_skills & required
            relevance = len(matched) / len(required)
            max_relevance = max(max_relevance, relevance)

        project_score = max_relevance * 100
    else:
        project_score = 0

    breakdown["projects"] = round(project_score * WEIGHTS["projects"] /100,1)

    if project_score >= 60:
        strong_points.append("Relevant project experience")
    else:
        weak_points.append("Limited relevant project work")

    # ---------------- LANGUAGES ----------------
    languages = profile.get("languages", {}).get("programming_languages", [])

    if languages:
        lang_ratio = 1.0
        strong_points.append("Programming languages known")
    else:
        lang_ratio = 0.0
        weak_points.append("No programming languages mentioned")
        reasoning_parts.append("Missing programming language details")

    languages_score = round(lang_ratio * WEIGHTS["languages"], 1)
    breakdown["languages"] = languages_score

    # ---------------- DOMAIN (v1 placeholder) ----------------
    domain_keywords = set(requirement.get("required_skills", []))
    candidate_domain_terms = set()

    candidate_domain_terms |= set(
        profile.get("skills", {}).get("technical_skills", [])
    )

    for proj in profile.get("projects", {}).get("projects", []):
        candidate_domain_terms |= set(proj.get("skills", []))

    matched_domain = domain_keywords & candidate_domain_terms

    domain_score = (len(matched_domain) / len(domain_keywords)) * 100 if domain_keywords else 100
    breakdown["domain"] = round(domain_score * WEIGHTS["domain"] / 100,1)

    if domain_score >= 60:
        strong_points.append("Good domain alignment")
    else:
        weak_points.append("Weak domain relevance")


    # ---------------- FINAL SCORE ----------------
    final_score = int(sum(breakdown.values()))

    reasoning = "; ".join(reasoning_parts) or "Average overall fit"

    return {
        "final_score": final_score,
        "breakdown": breakdown,
        "strong_points": strong_points,
        "weak_points": weak_points,
        "reasoning": reasoning
    }



# def score_candidate(profile: dict, requirement: dict) -> dict:
#     """
#     Deterministic scoring engine.
#     Returns score + explanation.
#     """

#     # Fixed system weights (v1)
#     WEIGHTS = {
#         "skills": 0.35,
#         "experience": 0.25,
#         "projects": 0.15,
#         "domain": 0.15,
#         "languages": 0.10
#     }

#     score_breakdown = {}
#     strong = []
#     weak = []

#     # ---------------- SKILLS ----------------
#     required_skills = set(requirement.get("required_skills", []))
#     candidate_skills = set(
#         profile.get("skills", {}).get("technical_skills", [])
#     )

#     if required_skills:
#         matched = required_skills & candidate_skills
#         skill_score = (len(matched) / len(required_skills)) * 100
#     else:
#         skill_score = 100

#     score_breakdown["skills"] = skill_score * WEIGHTS["skills"]

#     if skill_score >= 70:
#         strong.append(f"Matches required skills: {', '.join(matched)}")
#     else:
#         weak.append("Missing some required skills")

#     # ---------------- EXPERIENCE ----------------
#     min_exp = requirement.get("min_experience")
#     candidate_exp = profile.get("experience", {}).get("years", 0)

#     if min_exp:
#         exp_score = min(candidate_exp / min_exp, 1.0) * 100
#     else:
#         exp_score = 100

#     score_breakdown["experience"] = exp_score * WEIGHTS["experience"]

#     if exp_score >= 70:
#         strong.append(f"{candidate_exp} years relevant experience")
#     else:
#         weak.append("Experience below requirement")

#     # ---------------- PROJECTS ----------------
#     projects = profile.get("projects", [])
#     project_score = min(len(projects) * 20, 100)
#     score_breakdown["projects"] = project_score * WEIGHTS["projects"]

#     if project_score >= 60:
#         strong.append("Relevant projects available")
#     else:
#         weak.append("Limited project experience")

#     # ---------------- LANGUAGES ----------------
#     languages = profile.get("languages", {}).get("programming_languages", [])
#     lang_score = 100 if languages else 50
#     score_breakdown["languages"] = lang_score * WEIGHTS["languages"]

#     if languages:
#         strong.append("Programming languages known")
#     else:
#         weak.append("No programming languages mentioned")

#     # ---------------- FINAL SCORE ----------------
#     final_score = int(sum(score_breakdown.values()))

#     return {
#         "final_score": final_score,
#         "breakdown": {
#             "skills": skills_score,
#             "experience": experience_score,
#             "projects": projects_score,
#             "languages": languages_score,
#             "domain": domain_score
#         },
#         "strong_points": strong_points,
#         "weak_points": weak_points,
#         "reasoning": reasoning
# }

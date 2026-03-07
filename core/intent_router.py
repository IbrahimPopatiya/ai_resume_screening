from core.utility import normalize_message

def detect_intent(message: str) -> str:
    msg = normalize_message(message).lower()

    if any(x in msg for x in ["rank", "best candidate", "top candidate", "compare"]):
        return "ranking"

    if any(x in msg for x in ["skill", "skills", "technology", "tech stack"]):
        return "skills"

    if any(x in msg for x in ["experience", "worked", "company", "job"]):
        return "experience"

    if any(x in msg for x in ["education", "degree", "college", "university"]):
        return "education"

    if any(x in msg for x in ["project", "projects", "built"]):
        return "projects"

    if any(x in msg for x in ["achievement", "award", "certification"]):
        return "achievements"
    
    if any(x in msg for x in ["email", "phone", "contact"]):
        return "personal"
    
    if any(x in msg for x in ["language", "programming language", "spoken"]):
        return "programming_languages"
    return "general"

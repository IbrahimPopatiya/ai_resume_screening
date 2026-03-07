from agents import Runner
from core.intent_router import detect_intent
from core.utility import normalize_message
from core.ai_agents import (
    personal_info_agent,
    skills_agent,
    experience_agent,
    education_agent,
    projects_agent,
    achievements_agent,
    programming_language_agent,
    resume_master_agent
)



def detect_candidate_from_message(message: str, resumes_state: dict):
    msg = normalize_message(message).lower()
    for name, data in resumes_state.items():
        if name in msg:
            return name, data
    return None, None


from agents import Runner
from core.intent_router import detect_intent

async def resume_chat(
    message,
    history,
    resumes_state,
    recruiter_req,
):
    if not resumes_state:
        return "⚠️ No resumes found. Please upload resumes first."

    intent = detect_intent(message)

    # 🧠 Step 4.1 — Candidate detection
    candidate_name, candidate_data = detect_candidate_from_message(
        message, resumes_state
    )

    # 🧠 Step 4.2 — Build resume context
    if candidate_data:
        resumes_block = (
            f"--- Resume ({candidate_name}) ---\n"
            f"{candidate_data['resume_text']}"
        )
    else:
        # fallback: use all resumes
        resumes_block = "\n\n".join(
            f"--- Resume (doc_id: {doc_id}) ---\n{text}"
            for doc_id, text in resumes_state.items()
        )

    # 🧠 Step 4.3 — Requirement block
    requirement_block = ""
    if recruiter_req:
        requirement_block = f"\n\nRecruiter Requirement:\n{recruiter_req}"

    # 🧠 Step 4.4 — Agent routing
    if intent == "skills":
        agent = skills_agent
        merged_input = resumes_block

    elif intent == "experience":
        agent = experience_agent
        merged_input = resumes_block

    elif intent == "education":
        agent = education_agent
        merged_input = resumes_block

    elif intent == "projects":
        agent = projects_agent
        merged_input = resumes_block

    elif intent == "achievements":
        agent = achievements_agent
        merged_input = resumes_block

    elif intent == "ranking":
        agent = resume_master_agent
        merged_input = (
            f"{requirement_block}\n\n"
            f"Candidate Resumes:\n{resumes_block}\n\n"
            f"Task: Rank the best candidates and explain why."
        )

    else:
        agent = resume_master_agent
        merged_input = (
            f"Candidate Resumes:\n{resumes_block}"
            f"{requirement_block}\n\n"
            f"Recruiter Question:\n{message}"
        )

    result = await Runner.run(agent, merged_input)
    return result.final_output

# async def resume_chat(
#     message,
#     history,
#     resumes_state,        # dict: {doc_id: resume_text}
#     requirement_state     # string
# ):
#     # 1️⃣ Safety check
#     if not resumes_state:
#         return "⚠️ No resumes found. Please upload resumes first."

#     intent = detect_intent(message)

#     # 2️⃣ Build resume block
#     combined_resumes = []
#     for doc_id, text in resumes_state.items():
#         combined_resumes.append(
#             f"--- Resume (doc_id: {doc_id}) ---\n{text}"
#         )

#     resumes_block = "\n\n".join(combined_resumes)

#     # 3️⃣ Recruiter requirement block
#     requirement_block = ""
#     if requirement_state:
#         requirement_block = f"\n\nRecruiter Requirement:\n{requirement_state}"

#     # 4️⃣ INTENT ROUTING (STEP 3)
#     if intent == "skills":
#         agent = skills_agent
#         merged_input = resumes_block

#     elif intent == "personal":
#         agent = personal_info_agent
#         merged_input = resumes_block

#     elif intent == "programming_languages":
#         agent = programming_language_agent
#         merged_input = resumes_block

        
#     elif intent == "experience":
#         agent = experience_agent
#         merged_input = resumes_block

#     elif intent == "education":
#         agent = education_agent
#         merged_input = resumes_block

#     elif intent == "projects":
#         agent = projects_agent
#         merged_input = resumes_block

#     elif intent == "achievements":
#         agent = achievements_agent
#         merged_input = resumes_block

#     elif intent == "ranking":
#         agent = resume_master_agent
#         merged_input = (
#             f"{requirement_block}\n\n"
#             f"Candidate Resumes:\n{resumes_block}\n\n"
#             f"Task: Rank the best candidates and explain why."
#         )

#     else:
#         # General / complex / multi-step questions
#         agent = resume_master_agent
#         merged_input = (
#             f"Candidate Resumes:\n{resumes_block}"
#             f"{requirement_block}\n\n"
#             f"Recruiter Question:\n{message}"
#         )

#     # 5️⃣ Run agent
#     result = await Runner.run(agent, merged_input)
#     return result.final_output



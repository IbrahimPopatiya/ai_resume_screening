from ast import keyword
import os
import uuid
import shutil
from datetime import datetime
import gradio as gr
import json
from agents import Runner
from core.ai_agents import  personal_info_agent, resume_master_agent
import asyncio
from core.extractor import extract_text_from_file
from core.chat_engine import resume_chat as chat_engine_resume_chat
from db.postgres import PostgresDB
from core.intent_router import detect_intent
from core.profile_builder import build_candidate_profile
from core.parser import parse_requirement
from core.ranking_engine import score_candidate
from core.utility import normalize_message

from core.ai_agents import (
    personal_info_agent,
    skills_agent,
    experience_agent,
    education_agent,
    projects_agent,
    achievements_agent,
    programming_language_agent
)



# ---------------- CONFIG ----------------

UPLOAD_FOLDER = "data"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = PostgresDB()

# ALL_RESUME = {} 
TABLE_CACHE = []
# RECRUITER_REQ = None  
RECRUITER_REQUIREMENT = ""
# CURRENT_RESUME_TEXT = None
# CURRENT_DOC_ID = None
# CANDIDATE_INDEX = {}


# ---------------- RESUME HANDLERS ----------------


def save_resume(file):
    """
    Saves uploaded resume to disk with timestamped filename.
    """
    original_name = os.path.basename(file.name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{original_name}"

    save_path = os.path.join(UPLOAD_FOLDER, filename)
    shutil.copy(file.name, save_path)

    return filename, save_path


async def extract_candidate_name(resume_text: str) -> str:
    """
    Uses personal_info_agent to extract candidate name.
    Returns lowercase name or 'unknown_<uuid>'.
    """
    try:
        result = await Runner.run(
            personal_info_agent,
            f"Extract personal info from this resume:\n{resume_text}"
        )

        data = json.loads(result.final_output)
        name = data.get("name")

        if isinstance(name, str) and name.strip():
            return name

    except Exception as e:
        print("Name extraction failed:", e)

    return None


def process_uploaded_file(file, resume_state):
    """
    Handles full flow:
    save file → extract text → db insert → memory register
    """

    # 1️⃣ Save file
    filename, save_path = save_resume(file)

    # 2️⃣ Extract text
    try:
        resume_text = extract_text_from_file(save_path)
    except Exception as e:
        return None, f"Text extraction failed: {str(e)}"

    # 3️⃣ Assign doc id
    doc_id = str(uuid.uuid4())

    # 4️⃣ Save in DB
    db.insert_metadata(doc_id, filename, save_path)

    # 5️⃣ Keep in memory
    resume_state[doc_id] = resume_text

    return doc_id, resume_text


def upload_multiple(files):
    """
    Accepts multiple resumes → processes them sequentially
    """

    if not files:
        return "⚠️ No files selected."

    output_log = []

    for f in files:
        doc_id, _text = process_uploaded_file(f)
        if not _text:
            output_log.append(f"{f.name} → ❌ FAILED")
        else:
            output_log.append(f"{f.name} → Saved as doc_id: {doc_id}")

    return "\n".join(output_log)


def load_by_doc_id(doc_ids_text, resume_state):
    """
    Loads saved resumes from DB using doc IDs
    """

    if not doc_ids_text:
        return resume_state,"⚠️ Enter at least one doc_id."

    doc_ids = [x.strip() for x in doc_ids_text.split(",")]

    result_log = []

    for doc_id in doc_ids:

        file_path = db.get_file_path(doc_id)

        if not file_path:
            result_log.append(f"{doc_id} → ❌ Not found in DB")
            continue

        try:
            resume_text = extract_text_from_file(file_path)
            profile = asyncio.run(build_candidate_profile(resume_text))

            raw_name = profile.get("name")

            if isinstance(raw_name, dict):
                candidate_name = " ".join(
                    str(v) for v in raw_name.values() if isinstance(v, str)
                ).lower()
            elif isinstance(raw_name, str):
                candidate_name = raw_name.lower()
            else:
                candidate_name = None

            resume_state[doc_id] = {
                "text": resume_text,
                "candidate_name":  candidate_name,
                "profile": profile,
                "score": None
            }

            result_log.append(f"{doc_id} → Loaded successfully")

        except Exception as e:
            result_log.append(f"{doc_id} → ❌ Error: {str(e)}")

    return resume_state,"\n".join(result_log)



def upload_extract_save(files, resume_state):
    if not files:
        return "⚠️ No resumes selected."

    results = []

    for file in files:
        try:
            # 1️⃣ Save file
            safe = os.path.basename(file.name)
            name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe}"
            path = os.path.join("data", name)
            shutil.copy(file.name, path)

            # 2️⃣ Extract resume text
            resume_text = extract_text_from_file(path)

            # 3️⃣ Store in DB
            doc_id = str(uuid.uuid4())
            db.insert_metadata(doc_id, name, path)

            # 4️⃣ Extract candidate name (ONE time)
            raw_name = asyncio.run(
                extract_candidate_name(resume_text)
            )

            candidate_name = None
            if isinstance(raw_name, str):
                candidate_name = raw_name.strip().lower()

            profile = asyncio.run(build_candidate_profile(resume_text))


            # 5️⃣ Store in gr.State (SINGLE SOURCE OF TRUTH)
            resume_state[doc_id] = {
                "text": resume_text,
                "candidate_name": candidate_name,
                "profile": profile,
                "score": None
            }

            results.append(
                f"✔ {safe} → saved → doc_id: {doc_id}"
                + (f" → candidate: {candidate_name}" if candidate_name else "")
            )

        except Exception as e:
            results.append(f"❌ {file.name} → error: {str(e)}")

    return resume_state,"\n".join(results)


def load_resume_by_doc_id(doc_id):
    global CURRENT_RESUME_TEXT, CURRENT_DOC_ID

    file_path = db.get_file_path(doc_id)
    if not file_path:
        return False, "⚠️ Document not found."

    CURRENT_RESUME_TEXT = extract_text_from_file(file_path)
    CURRENT_DOC_ID = doc_id
    return True, f"✅ Loaded resume (doc_id={doc_id})"


def refresh_resume_list():
        global TABLE_CACHE
        rows = db.fetch_all()
        TABLE_CACHE = [[d[0], d[1], str(d[3])] for d in rows]
        return TABLE_CACHE

def search_resumes(keyword):
        global TABLE_CACHE
        rows = db.search(keyword)
        TABLE_CACHE = [[d[0], d[1], str(d[3])] for d in rows]
        return TABLE_CACHE



def sort_resumes(order):
        global TABLE_CACHE
        rows = db.sort_by(order)
        TABLE_CACHE = [[d[0], d[1], str(d[3])] for d in rows]
        return TABLE_CACHE
    
# def view_resume(evt: gr.SelectData):
#         try:
#             row_index = evt.index
#             doc_id = TABLE_CACHE[row_index][0]
#             path = db.get_file_path(doc_id)
#             text = extract_text_from_file(path)
#             return text
#         except Exception as e:
#             return f"⚠️ Error: {str(e)}"

def view_resume(evt: gr.SelectData):
    try:
        if isinstance(evt.index, (list, tuple)):
            row_index = evt.index[0]
        else:
            row_index = evt.index

        doc_id = TABLE_CACHE[row_index][0]
        path = db.get_file_path(doc_id)
        text = extract_text_from_file(path)
        return text

    except Exception as e:
        return f"⚠️ Error: {str(e)}"



def score_all_resumes(requirement_text: str, resume_state: dict):
    """
    Smart ranking entry point (NO AI scoring here).
    """

    if not requirement_text or not isinstance(requirement_text,str):
        return resume_state, "⚠️ Please enter recruiter requirement."

    if not requirement_text.strip():
        return resume_state, "⚠️ Please enter recruiter requirement."

    # 1️⃣ Parse requirement ONCE (Step 3)
    requirement = asyncio.run(parse_requirement(requirement_text))

    ranked = []

    # 2️⃣ Score each candidate deterministically (Step 4)
    for doc_id, data in resume_state.items():
        profile = data.get("profile")

        if not profile:
            continue  # skip if profile missing

        score_result = score_candidate(profile, requirement)

        # cache score
        resume_state[doc_id]["score"] = score_result

        ranked.append({
            "doc_id": doc_id,
            "name": profile.get("name") or "Unknown",
            "score": score_result["final_score"],
            "strong": score_result["strong_points"],
            "weak": score_result["weak_points"],
            "reason": score_result["reasoning"]
        })

    # 3️⃣ Sort by score
    ranked.sort(key=lambda x: x["score"], reverse=True)

    # 4️⃣ Build display text
    display = ["🏆 Ranked Candidates:\n"]
    for i, c in enumerate(ranked, 1):
        display.append(
            f"{i}. {c['name']} (Score: {c['score']}/100)\n"
            f"   ✔ Strengths: {', '.join(c['strong']) or 'None'}\n"
            f"   ✖ Weaknesses: {', '.join(c['weak']) or 'None'}\n"
            f"   💡 Reason: {c['reason']}\n"
        )

    return resume_state, "\n".join(display)




# def score_all_resumes(requirement_text: str,resume_state):
#     global TABLE_CACHE

#     if not requirement_text.strip():
#         return "⚠️ Please enter recruiter requirement."

#     ranked_scores = []

#     for doc_id, resume_text in resume_state.items():
#         try:
#             raw_json = asyncio.run(
#                 async_score_resume(score_experience_candidate_agent, resume_text, requirement_text)
#             )

            
#             score_json = json.loads(raw_json)

#             ranked_scores.append({
#                 "doc_id": doc_id,
#                 "name": score_json.get("candidate_name", "Unknown"),
#                 "score": score_json.get("score", 0),
#                 "strong": score_json.get("strong_points", []),
#                 "weak": score_json.get("weak_points", []),
#                 "reason": score_json.get("reasoning", "")
#             })

#         except Exception as e:
#             ranked_scores.append({
#                 "doc_id": doc_id,
#                 "name": "Unknown",
#                 "score": 0,
#                 "strong": [],
#                 "weak": [f"Error: {str(e)}"],
#                 "reason": "Scoring failed"
#             })

#     # sort descending
#     ranked = sorted(ranked_scores, key=lambda x: x["score"], reverse=True)

#     display = ["🏆 Ranked Candidates:\n"]
#     for i, c in enumerate(ranked, 1):
#         display.append(
#             f"{i}. {c['name']} (Score: {c['score']}/100)\n"
#             f"   ✔ Strengths: {', '.join(c['strong']) or 'None'}\n"
#             f"   ✖ Weaknesses: {', '.join(c['weak']) or 'None'}\n"
#             f"   💡 Reason: {c['reason']}\n"
#         )

#     return "\n".join(display)

def find_candidate_in_message(message: str, resumes_state: dict):
    """
    Detect candidate name from user message using gr.State resumes.
    Returns (doc_id, candidate_data) or (None, None)
    """
    msg = normalize_message(message).lower()

    for doc_id, data in resumes_state.items():
        name = data.get("candidate_name")
        if isinstance(name, str) and name.lower() in msg:
            return doc_id, data

    return None, None



async def resume_chat(message, history, resumes_state, requirement_state):
    return await chat_engine_resume_chat(
        message=message,
        history=history,
        resumes_state=resumes_state,
        recruiter_req=requirement_state,
    )




def save_recruiter_requirement(text,requirment_state):
    requirment_state = (text or "").strip()
    if not requirment_state:
        return "⚠️ Requirement cleared"
    return requirment_state,"✅ Requirement saved"

def handle_doc_id_input(doc_id):
    global CURRENT_RESUME_TEXT, CURRENT_DOC_ID

    file_path = db.get_file_path(doc_id)
    if not file_path:
        return f"⚠️ No resume found for doc_id={doc_id}"

    CURRENT_RESUME_TEXT = extract_text_from_file(file_path)
    CURRENT_DOC_ID = doc_id

    return f"✅ Resume loaded (doc_id={doc_id}). You can now chat."

 

# ---------------- GRADIO UI ----------------

with gr.Blocks() as demo:

    state_resumes = gr.State({})       # {doc_id: resume_text}
    state_requirement = gr.State("")  # recruiter requirement


    gr.Markdown("# 📄 Resume Extraction System")
    gr.Markdown(
        "Upload resumes → store them → retrieve later using doc_id.\n\n"
        "**✔ Supports PDF, DOCX, TXT**"
    )

    state_files = gr.State([])

    with gr.Tabs():

        # ---------------- TAB 1 ----------------
        with gr.Tab("Upload Resumes"):

            with gr.Row():
                file_input = gr.File(
                    label="Upload Resume Files",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".txt"]
                )
                add_btn = gr.Button("Add To List")
                clear_btn = gr.Button("Clear Selection")

            selected_textbox = gr.Textbox(
                label="Selected Files",
                lines=4
            )

            upload_btn = gr.Button("Upload → Extract → Save")

            upload_status = gr.Textbox(
                label="Upload Status",
                lines=6
            )
        

        with gr.Tab("Chat Assistant"):

            gr.Markdown("### 🎯 Add Recruiter Requirement")

            with gr.Row():
                recruiter_box = gr.Textbox(
                    label="Enter recruiter requirement",
                    placeholder="Example: Python Developer with 3+ years, Django, SQL, AWS",
                    lines=3
                )
                recruiter_btn = gr.Button("Save Requirement")

            recruiter_status = gr.Textbox(label="Requirement Status", lines=4, interactive=False)

            chat = gr.ChatInterface(
                fn=resume_chat,
                additional_inputs=[state_resumes, state_requirement],
                title="🧠 Resume Chat Assistant",
                description="Ask anything about the candidate (skills, experience, education, etc.)"
            )



        # ---------------- TAB 2 ----------------
        with gr.Tab("Stored Resumes"):


            # 2️⃣ Scoring button
            score_all_btn = gr.Button("Score All Resumes")
            score_output = gr.Textbox(label="Scoring Results", lines=10, interactive=False)


            refresh_btn = gr.Button("🔄 Refresh Resume List")

            with gr.Row():
                search_box = gr.Textbox(
                    label="Search by filename or doc_id",
                    placeholder="e.g. python developer"
                )
                search_btn = gr.Button("Search")

            with gr.Row():
                sort_dropdown = gr.Dropdown(
                    choices=["Newest First", "Oldest First"],
                    value="Newest First",
                    label="Sort by upload time"
                )
                sort_btn = gr.Button("Sort")

            with gr.Row():
                resume_table = gr.DataFrame(
                    headers=["Doc ID", "Filename", "Uploaded At"],
                    datatype=["str", "str", "str"],
                    interactive=False,
                    label="Saved Resume Records"
                )

                resume_viewer = gr.Textbox(
                    label="Resume Preview",
                    lines=28,
                    interactive=False
                )

            

        # ---------------- TAB 3 ----------------
        with gr.Tab("Load by Doc ID"):

            load_box = gr.Textbox(
                label="Enter doc_id(s), comma separated"
            )
            load_btn = gr.Button("Load Resumes")
            load_status = gr.Textbox(
                label="Status",
                lines=4
            )


    # ============= FUNCTIONS =============

    def add_files(new_files, current):
        current = current or []
        if new_files:
            current.extend(new_files)
        names = [f.name for f in current]
        return current, "\n".join(names)

    
    

    

    
    resume_table.select(
        fn=view_resume,
        inputs=None,
        outputs=resume_viewer
    )

    add_btn.click(
        fn=add_files,
        inputs=[file_input, state_files],
        outputs=[state_files, selected_textbox]
    )
    recruiter_btn.click(
        fn=save_recruiter_requirement,
        inputs=[recruiter_box, state_requirement],
        outputs=[state_requirement,recruiter_status]
    )
    

    score_all_btn.click(
        fn=score_all_resumes,
        inputs=[recruiter_box, state_resumes],
        outputs=[state_resumes, score_output]
    )



    refresh_btn.click(
        fn=refresh_resume_list,
        outputs=[resume_table]
    )
    search_btn.click(
        fn=search_resumes,
        inputs=[search_box],
        outputs=[resume_table]
    )

    sort_btn.click(
        fn=sort_resumes,
        inputs=[sort_dropdown],
        outputs=[resume_table]
    )


    resume_table.select(
        fn=view_resume,
        outputs=[resume_viewer]
    )

    # recruiter_box.change(
    #     fn=save_recruiter_requirement,
    #     inputs=recruiter_box,
    #     outputs=recruiter_status
    # )

    def clear_list():
        return [], ""

    refresh_btn.click(
    fn=refresh_resume_list,
    outputs=[resume_table]
    )

    search_btn.click(
        fn=search_resumes,
        inputs=[search_box],
        outputs=[resume_table]
    )

    sort_btn.click(
        fn=sort_resumes,
        inputs=[sort_dropdown],
        outputs=[resume_table]
    )


    clear_btn.click(
        fn=clear_list,
        outputs=[state_files, selected_textbox]
    )


    upload_btn.click(
        fn=upload_extract_save,
        inputs=[state_files, state_resumes],
        outputs=[state_resumes,upload_status]
    )


    load_btn.click(
        fn=load_by_doc_id,
        inputs=[load_box,state_resumes],
        outputs=[state_resumes,load_status]
    )



# ---------------- MAIN ----------------
if __name__ == "__main__":
    demo.launch()





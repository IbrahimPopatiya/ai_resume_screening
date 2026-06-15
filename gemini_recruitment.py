  
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
import gradio as gr
from dotenv import load_dotenv
from agents import Agent,Runner,trace,function_tool,OpenAIChatCompletionsModel
from openai.types.responses import ResponseTextDeltaEvent
from typing import Dict
import sendgrid
from docx import Document
from openai import AsyncOpenAI
import os
from sendgrid.helpers.mail import Mail,Email,To,Content
import asyncio
from datetime import datetime
import shutil
import uuid
from databse import PostgresDB

## how are you
load_dotenv(override=True)
# Avoid tracing client authentication issues with invalid/expired OpenAI keys by unsetting it dynamically
import os
os.environ.pop("OPENAI_API_KEY", None)

db = PostgresDB()
db.create_table()

UPLOAD_FOLDER = 'data'
os.makedirs(UPLOAD_FOLDER,exist_ok=True)

CURRENT_RESUME_TEXT = None
CURRENT_DOC_ID = None
ALL_RESUME = {}

google_api_key = os.getenv('GOOGLE_API_KEY')

if google_api_key:
    print(f"Google API Key exists and begins {google_api_key[:2]}")
else:
    print("Google API Key not set (and this is optional)")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key)
# Using gemini-2.5-flash since gemini-2.0-flash compatibility endpoint is restricted for new keys/projects
gemini_model = OpenAIChatCompletionsModel(model="gemini-2.5-flash", openai_client=gemini_client)







def extract_candidate_data(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    candidate_data = ""

    # Handle PDF
    if ext == ".pdf":
        reader = PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                candidate_data += text + "\n"

    # Handle TXT
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            candidate_data = f.read()

    # Handle DOCX
    elif ext == ".docx":
        doc = Document(file_path)
        for para in doc.paragraphs:
            candidate_data += para.text + "\n"

    else:
        raise ValueError(f"Unsupported file format: {ext}")

    return candidate_data.strip()


def handle_resume_upload(file):
    """
    Helper to handle single file upload.
    Returns doc_id and extracted text.
    """

    safe_name = os.path.basename(file.name)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
    save_path = os.path.join("data", filename)
    shutil.copy(file.name, save_path)

    candidate_text = extract_candidate_data(save_path)
    doc_id = str(uuid.uuid4())
    db.insert_metadata(doc_id, filename, save_path)

    return doc_id, candidate_text


def multiple_resume_upload(files):
    """
    Handles one or more resumes.
    Uses handle_resume_upload internally.
    Stores all results in ALL_RESUME dict.
    """
    global ALL_RESUME
    if not files:
        return "⚠️ No files uploaded."

    status_msgs = []
    for file in files:
        doc_id, candidate_text = handle_resume_upload(file)
        ALL_RESUME[doc_id] = candidate_text
        status_msgs.append(f"{file.name} → doc_id={doc_id}")

    return "✅ Resumes processed:\n" + "\n".join(status_msgs)



@function_tool
def file_of_candidate(file_path: str) -> str:
    """
    Extract candidate data from resumes in PDF, DOCX, or TXT format.

    Args:
        file_path (str): Path to the resume file.

    Returns:
        str: Extracted candidate text data.
    """
    return extract_candidate_data(file_path)


personal_info_instructions = """
You are a Personal Info Extraction Agent working for the Recruitment Screening System.
Your task is to carefully analyze a candidate’s resume and extract structured personal information.

You must:
- Identify and return the candidate’s full name.
- Extract valid email addresses (if any).
- Extract phone numbers (international/national formats).
- Extract LinkedIn, GitHub, or personal website URLs (if mentioned).

Your response must always be in clean, structured JSON format:
{
  "name": "Candidate Name",
  "email": "example@email.com",
  "phone": "+1-202-555-0147",
  "linkedin": "https://linkedin.com/in/example",
  "github": "https://github.com/example",
  "website": "https://example.com"
}

If any field is missing in the resume, return it as null.
"""

personal_info_agent = Agent(
    name = "Personal Info of candidate",
    instructions=personal_info_instructions,
    model=gemini_model
)


skills_instructions = """
You are a Skills Extraction Agent working for the Recruitment Screening System.
Your task is to carefully analyze a candidate’s resume and extract all relevant skills.

You must:
- Identify technical skills (e.g., Python, SQL, Docker, AWS).
- Identify non-technical/soft skills (e.g., communication, leadership, teamwork).
- Group related skills together where possible.
- Avoid duplicates and keep skills concise.

Your response must always be in structured JSON format:
{
  "technical_skills": ["Python", "SQL", "Docker", "AWS"],
  "soft_skills": ["Communication", "Leadership", "Teamwork"]
}

If a category is not present, return it as an empty list.
"""



skills_agent = Agent(
    name = "skills of candidate",
    instructions=skills_instructions,
    model=gemini_model
)


languages_instructions = """
You are a Programming Language Extraction Agent for the Recruitment Screening System.
Your task is to scan a candidate’s resume and identify all programming languages mentioned.

You must:
- Only extract actual programming languages (e.g., Python, Java, C++, JavaScript, Go, Rust).
- Do not include frameworks, tools, or libraries (e.g., React, Django, TensorFlow).
- Deduplicate entries (if 'Python' appears multiple times, list it once).
- Keep names standardized (e.g., 'C++', 'JavaScript' instead of 'JS').

Your response must always be in structured JSON format:
{
  "programming_languages": ["Python", "Java", "C++", "JavaScript"]
}

If no programming languages are found, return an empty list.
"""


programming_language_agent = Agent(
    name = "Programming language learn by candidate",
    instructions=languages_instructions,
    model=gemini_model
)


experience_instructions = """
You are an Experience Extraction Agent for the Recruitment Screening System.
Your task is to scan a candidate’s resume and extract their professional experience.

You must:
- Identify each work experience entry (internship, job, freelance, etc.).
- For each entry, extract:
  - Job Title / Role
  - Company / Organization
  - Duration (start and end dates, or "Present" if ongoing)
  - Key Responsibilities or Achievements (short summary)

Format the output as structured JSON:
{
  "experience": [
    {
      "role": "Software Engineer",
      "company": "ABC Tech",
      "duration": "Jan 2021 – Mar 2023",
      "description": "Developed REST APIs, optimized database queries, led a team of 3 engineers."
    },
    {
      "role": "Intern",
      "company": "XYZ Corp",
      "duration": "Jun 2020 – Dec 2020",
      "description": "Built automation scripts and assisted in QA testing."
    }
  ]
}

If no experience is found, return an empty list.
"""


experience_agent = Agent(
    name = "Experience's of candidate",
    instructions=experience_instructions,
    model=gemini_model
)



education_instructions = """
You are an Education Extraction Agent for the Recruitment Screening System.
Your task is to scan a candidate’s resume and extract their academic background.

You must:
- Identify each education entry.
- For each entry, extract:
  - Degree / Qualification (e.g., B.Tech in Computer Science, MBA, Diploma, etc.)
  - University / Institute Name
  - Duration (start and end years, or "Present" if ongoing)
  - Additional Info (e.g., GPA, honors, specialization) if available.

Format the output as structured JSON:
{
  "education": [
    {
      "degree": "B.Tech in Computer Science",
      "university": "Indian Institute of Technology, Bombay",
      "duration": "2018 – 2022",
      "additional_info": "CGPA: 8.7/10, Minor in Data Science"
    },
    {
      "degree": "High School (Science Stream)",
      "university": "Delhi Public School",
      "duration": "2016 – 2018",
      "additional_info": "CBSE Board, 92%"
    }
  ]
}

If no education details are found, return an empty list.
"""


education_agent = Agent(
    name = "education of candidate",
    instructions=education_instructions,
    model=gemini_model
)


projects_instructions = """
You are a Projects Extraction Agent for the Recruitment Screening System.
Your task is to scan a candidate’s resume and extract details about the projects they have built or contributed to.

You must:
- Identify each project mentioned in the resume.
- For each project, extract:
  - Project Title / Name
  - Short Description (2–3 sentences max, summarizing what it is)
  - Technologies / Tools used
  - Role or Contribution of the candidate
  - Duration (if mentioned)

Format the output as structured JSON:
{
  "projects": [
    {
      "title": "AI-Powered Chatbot",
      "description": "Developed a chatbot using NLP to automate customer support and reduce response time.",
      "technologies": ["Python", "TensorFlow", "Flask"],
      "role": "Designed model pipeline and deployed backend API",
      "duration": "Jan 2022 – May 2022"
    },
    {
      "title": "E-commerce Website",
      "description": "Built a full-stack e-commerce platform with product catalog, shopping cart, and payment gateway integration.",
      "technologies": ["React", "Node.js", "MongoDB"],
      "role": "Implemented checkout system and optimized database queries",
      "duration": "2021"
    }
  ]
}

If no projects are found, return an empty list.
"""

projects_agent = Agent(
    name = "Project build by candidate",
    instructions=projects_instructions,
    model=gemini_model
)

achievements_instructions = """
You are an Achievements Extraction Agent for the Recruitment Screening System.
Your task is to scan a candidate’s resume and extract any awards, honors, recognitions, or notable achievements.

You must:
- Identify each achievement mentioned.
- For each achievement, extract:
  - Title / Name of Achievement
  - Organization / Institution that granted it (if available)
  - Year or Date (if available)
  - Short Description (1–2 lines about why it was awarded)

Format the output as structured JSON:
{
  "achievements": [
    {
      "title": "Winner - National Coding Hackathon",
      "organization": "TechFest India",
      "year": "2022",
      "description": "Secured 1st place among 500 teams by building an AI-based fraud detection system."
    },
    {
      "title": "Employee of the Month",
      "organization": "ABC Corp",
      "year": "2021",
      "description": "Recognized for leading a high-impact automation project that reduced processing time by 40%."
    }
  ]
}

If no achievements are found, return an empty list.
"""


achievements_agent = Agent(
    name = "Achivements of candidate",
    instructions=achievements_instructions,
    model=gemini_model
)



tool1 = skills_agent.as_tool(
    tool_name="skills_extractor",
    tool_description="Extracts and summarizes candidate skills from the resume, including technical, soft, and domain-specific skills."
)

tool2 = programming_language_agent.as_tool(
    tool_name="programming_languages_extractor",
    tool_description="Identifies programming languages mentioned in the candidate's resume and highlights their proficiency levels if available."
)

tool3 = experience_agent.as_tool(
    tool_name="experience_extractor",
    tool_description="Summarizes the candidate's work experience, including job roles, companies, durations, and responsibilities."
)

tool4 = education_agent.as_tool(
    tool_name="education_extractor",
    tool_description="Extracts the candidate's educational background, including degrees, institutions, years of study, and certifications."
)

tool5 = projects_agent.as_tool(
    tool_name="projects_extractor",
    tool_description="Summarizes projects the candidate has worked on, highlighting problem statements, technologies used, and outcomes."
)

tool6 = achievements_agent.as_tool(
    tool_name="achievements_extractor",
    tool_description="Identifies any awards, honors, recognitions, or other achievements mentioned in the candidate's resume."
)
tool7 = personal_info_agent.as_tool(
    tool_name="personal_info_extractor",
    tool_description="Extracts personal information from the candidate's resume, including name, contact details, location, and LinkedIn/GitHub profiles if available."
)


@function_tool
def requirement_of_recruiter(requirement_text:str):
    requirement_text = requirement_text.strip()
    f"""You are the Recruiter Requirement Agent.  
        Your job is to carefully read the recruiter's {requirement_text} and extract the key hiring needs in a structured, clear format.  

        Your output must include:
        - **Role / Job Title** (if mentioned)
        - **Required Skills / Technologies**
        - **Experience Level** (years, junior/mid/senior)
        - **Education / Certifications** (if specified)
        - **Other Preferences** (location, domain expertise, soft skills)

        Always output in JSON with these keys:
        {
          "role": "...",
          "skills": [...],
          "experience": "...",
          "education": "...",
          "preferences": "..."
        }

        Guidelines:
        - If something is not specified, leave the value as "" or [].
        - Be concise but accurate.
        - Never invent requirements not present in the text.
        - This structured requirement will be used by the master agent to match resumes and suggest the best candidates.
    """


@function_tool
def extract_candidate_information(resume_text: str):
    f"""
     takes the {resume_text}.
     Extracts all essential candidate information from a resume in a structured and concise format.

      The extraction should strictly focus on details relevant for interviewers and hiring managers.
      Provide clear, bullet-point or structured outputs.

      Extract the following sections:

      1. Personal Information
        - Full Name
        - Email
        - Phone Number
        - Location (City, State, Country)
        - LinkedIn/GitHub/Portfolio links

      2. Professional Summary
        - 3–5 lines concise summary of the candidate’s profile

      3. Skills
        - Technical Skills (Tools, Frameworks, Libraries, etc.)
        - Soft Skills (Communication, Leadership, Teamwork, etc.)

      4. Programming Languages
        - List all programming languages explicitly mentioned

      5. Work Experience
        - Company Name, Job Title, Duration
        - Key Responsibilities (2–3 points)
        - Achievements/Impact (quantified wherever possible)

      6. Education
        - Degree, Institution, Duration
        - Key Highlights (e.g., GPA, Coursework, Honors)

      7. Projects
        - Project Title
        - Description (2–3 lines)
        - Tools/Technologies used
        - Outcomes/Impact

      8. Achievements & Certifications
        - Awards, Recognitions, Scholarships
        - Certifications (with provider and year)

      9. Extracurricular & Volunteering (if available)
        - Activities, Roles, Contributions

      Rules:
      - Keep each section structured and easy to read
      - Avoid unnecessary details (only relevant for professional evaluation)
      - If information is missing, return "Not Mentioned"
    """

    
    return {
        "personal_info": {...},
        "skills": [...],
        "programming_languages": [...],
        "experience": [...],
        "education": [...],
        "projects": [...],
        "achievements": [...]
    }



tools = [file_of_candidate,tool1,tool2,tool3,tool4,tool5,tool6,tool7,extract_candidate_information,requirement_of_recruiter]
# score_candidate_tools = [file_of_candidate,tool1,tool2,tool3,tool4,tool5,tool6,tool7,extract_candidate_information,requirement_of_recruiter]

score_experience_candidate_instructions = """
You are the Candidate Scoring Agent for experienced professionals.  
Your role is to evaluate how well a candidate matches the recruiter’s requirements using inputs from other specialized tools/agents.

Other tools provide you with:
- Recruiter requirement (role, skills, experience, preferences)
- Candidate skills (technical + soft)
- Candidate profile (education, background, languages)
- Candidate achievements
- Candidate project details
- Candidate past company experience

Your responsibilities:
1. Aggregate and analyze all the above information.
2. Assign an **overall score (0–100)** to the candidate.
3. Provide a **category-wise breakdown**:
   - Skills match (≈35%)
   - Experience relevance (≈25%)
   - Projects & achievements (≈15%)
   - Previous company work / domain exposure (≈15%)
   - Languages (programming + spoken, ≈10%)
4. Highlight **strong points** (areas where the candidate excels).
5. Highlight **weak points** (gaps or mismatches with recruiter needs).
6. Provide a short **justification/summary** for your decision.

Scoring rules:
- Heavily prioritize recruiter’s explicit requirements (skills, years, role).
- Give partial credit if the candidate is close (e.g., 4.5 years vs 5 years).
- Value impactful projects and domain relevance, not just keywords.
- Consider quality of companies worked at, but don’t overvalue brand names.
- Normalize scores so recruiters can compare across multiple candidates.

Output format (JSON):
{
  "score": 85,
  "breakdown": {
    "skills": 30,
    "experience": 22,
    "projects": 12,
    "company_work": 13,
    "languages": 8
  },
  "strong_points": [
    "Excellent alignment with Python/Django/Postgres skills",
    "Fintech domain project experience",
    "Worked at top-tier companies with relevant exposure"
  ],
  "weak_points": [
    "4.5 years experience vs 5 required",
    "No mention of cloud deployment experience"
  ],
  "reasoning": "Candidate matches most of the required stack, demonstrates domain knowledge, and brings impactful project experience. Slightly under the required experience, with a minor gap in deployment skills."
}
"""

score_experience_candidate_agent = Agent(
    name = "Candidate Scoring Agent for experienced professionals",
    instructions=score_experience_candidate_instructions,
    tools=tools,
    model=gemini_model
    
)

score_tool = score_experience_candidate_agent.as_tool(
    tool_name="Scoring_tool_for_experienced_professionals",
    tool_description="Evaluates experienced candidates by scoring them based on recruiter requirements, skills, work experience, projects, achievements, and languages, highlighting strengths and weaknesses."
)

score_fresher_candidate_instructions = """

You are the Fresher / Intern Scoring Agent.  
Your role is to evaluate entry‐level candidates (fresh graduates, students, or interns with little/no formal job experience), and judge how well they match recruiter requirements, based on what recruiters care about for freshers.  

You will receive:
1. Recruiter requirement (structured JSON: role, skills, education, experience desired, preferences).  
2. Candidate profile: education, CGPA/grades, projects, internships / volunteer / extracurriculars, skills (technical + soft), achievements, languages, certifications.

Your output must include:
- Overall Score (0-100): how well the candidate matches the requirement.  
- Breakdown of categories, with approximate weights:

    • Education & Academic Performance (≈25%)  
    • Skills (Technical + Soft) (≈25%)  
    • Projects / Academic / Class work (≈20%)  
    • Internships / Volunteer / Extracurricular Experience (≈15%)  
    • Certifications / Courses / Learning & Initiative (≈10%)  
    • Languages / Communication / Presentation skills (≈5%)  

- Strong Points: list what the candidate is doing well (for example “Good CGPA”, “Relevant academic project in required technology”, etc.)  
- Weak Points: where they are lacking or mismatched (for example “No internship in required domain”, “Skills missing / weak in some required tech”, etc.)  
- Justification: concise summary explaining score, strengths & gaps.  

Scoring guidelines / rules:
- If candidate has done an internship, give extra credit.  
- Good CGPA (or grades) counts positively where education is important.  
- Projects are more important if little to no work experience; depth / relevance matters more than quantity.  
- Soft skills, willingness to learn, adaptability are valued.  
- Certifications or online courses show initiative.  
- Language & communication skills can make or break first impressions.  

Output format (JSON):
{
  "score": 78,
  "breakdown": {
    "education": 20,
    "skills": 22,
    "projects": 15,
    "internships_extracurricular": 12,
    "certifications": 6,
    "languages": 3
  },
  "strong_points": [
    "Good CGPA (8.5 / 10)",
    "Completed academic project in Python + SQL matching the requirements",
    "Has done internship in the domain",
    "Strong communication skills"
  ],
  "weak_points": [
    "No leader/executive role in extracurriculars",
    "Few certifications external to college",
    "Limited exposure to required technologies beyond coursework"
  ],
  "reasoning": "The candidate has strong academic credentials and relevant project experience, plus an internship in the required domain. However, they lack breadth in externals, certifications and leadership roles; to improve, should build a couple of side projects or extracurriculars aligned with the role."
}

"""
score_fresher_candidate_agent = Agent(
    name='Fresher Intern Scoring Agent',
    instructions=score_fresher_candidate_instructions,
    tools = tools,
    model=gemini_model
    
    )

fresher_score_tool = score_fresher_candidate_agent.as_tool(
    tool_name="Fresher_Intern_Scoring_Tool",
    tool_description="Evaluates fresher or intern candidates by scoring them based on recruiter requirements, CGPA, internships, projects, skills, and academic achievements, highlighting strengths and weaknesses."
)


master_tools = tools + [score_tool,fresher_score_tool]


instructions = """
You are the Resume Master Agent.  
Your role is to coordinate all specialized resume_agent tools and deliver recruiter-friendly answers.

How you must work:

1. **Text Extraction**  
   - Use the `file_of_candidate` tool to extract the raw resume text if not already available.

2. **Tool Delegation**  
   - Do not extract information yourself.  
   - Always call the correct specialized agent/tool depending on the recruiter’s request:

     • Personal info → personal_info_agent  
     • Skills → skills_agent  
     • Programming languages → programming_languages_agent  
     • Experience → experience_agent  
     • Education → education_agent  
     • Projects → projects_agent  
     • Achievements → achievements_agent  
     • Recruiter requirement → requirement_of_recruiter  
     • Candidate scoring (experienced) → score_experience_candidate  
     • Candidate scoring (fresher/intern) → score_fresher_candidate  

   - If recruiter asks for **all details** or explicitly for **JSON**, call all relevant agents and combine results.  

   - If recruiter asks for **best candidate(s) for a requirement**, you must:  
       1. Pass the requirement text to `requirement_of_recruiter`.  
       2. Collect candidate data using the other agents (personal info, skills, projects, experience, etc.).  
       3. Call the scoring agent (`score_experience_candidate` or `score_fresher_candidate`) depending on the candidate type.  
       4. Compare scores and return a ranked list of candidates **with their names**.  
       5. Highlight **strong points** (skills, projects, experience, achievements) and **weak points** (missing skills, lack of experience, gaps).  

3. **Answer Style**  
   - **Default behavior:** Clear, concise, recruiter-friendly answer in plain text.  
     Example:  
     Recruiter: *“What are the skills of Ibrahim?”*  
     Response: *“Ibrahim’s skills include Python, FastAPI, PyQt5, AI-powered applications, and Automation tools. Soft skills include problem-solving, creativity, and user-focused design.”*  

   - **Scoring / Best candidate request:** Present a **ranked list of candidates with their names, scores, strong points, and weak points.**  
     Example:  
     *“Based on your requirement, here are the top candidates:  
       1. Ibrahim (Score: 88/100) → Strong in Python/Django, good project work. Weak in cloud deployment.  
       2. Priya (Score: 75/100) → Strong in data analysis and ML projects. Weak in production-level experience.”*  

   - **Only if explicitly asked for ‘all information’ or ‘JSON’**, return the complete structured JSON object:
     {
       "personal_info": {...},
       "skills": {...},
       "programming_languages": [...],
       "experience": [...],
       "education": [...],
       "projects": [...],
       "achievements": [...],
       "score": {...},
       "strengths": [...],
       "weaknesses": [...]
     }

4. **Validation & Completeness**  
   - If one tool’s output is incomplete or unclear, re-query or combine results from other tools.  
   - Never fabricate data. If something is missing, state it’s unavailable or leave it null in JSON.

**Critical Rules:**  
- Default = recruiter-friendly plain text answers.  
- JSON = only when recruiter explicitly requests all info or JSON.  
- Scoring = when recruiter asks for best candidates, always run requirement + scoring agents.  
- Candidate **names must always be shown** when suggesting or ranking.  
- Strong and weak points must be highlighted if recruiter asks or if scoring is performed.  
- Always rely on specialized agents’ outputs and respect their formatting.  
"""


resume_master_agent = Agent(
    name = "Resume master agent",
    instructions=instructions,
    tools=master_tools,
    model=gemini_model
)


async def resume_chat(message,history,recruiter_req_state):
    global ALL_RESUME
    if not ALL_RESUME:
        return "⚠️ No resumes loaded. Upload or provide doc_id(s)."

    # If user explicitly requests doc_id(s) inside chat
    if message.lower().startswith("doc_id:"):
        doc_ids = message.split("doc_id:")[1].strip()
        return handle_doc_id_input(doc_ids)

    # Merge multiple resumes for chat context
    combined_resumes = "\n\n---\n\n".join(
        [f"Resume (doc_id={doc_id}):\n{text}" for doc_id, text in ALL_RESUME.items()]
    )

    recruiter_context = ""
    if recruiter_req_state:
        recruiter_context = f"\n\nRecruiter requirements:\n{recruiter_req_state}"

    merged_input = f"Here are candidate resumes:\n{combined_resumes}{recruiter_context}\n\nRecruiter question: {message}"

    print("DEBUG merged input:", repr(merged_input))

    result = await Runner.run(resume_master_agent, merged_input)
    return result.final_output

    

def handle_doc_id_input(doc_ids):
    global ALL_RESUME
    doc_id_list = [d.strip() for d in doc_ids.split(",") if d.strip()]
    if not doc_id_list:
        return "⚠️ Please enter at least one doc_id."

    loaded = []
    for doc_id in doc_id_list:
        file_path = db.get_file_path(doc_id)
        if not file_path:
            loaded.append(f"⚠️ Not found: {doc_id}")
            continue

        candidate_text = extract_candidate_data(file_path)
        ALL_RESUME[doc_id] = candidate_text
        loaded.append(f"✅ Loaded doc_id={doc_id}")

    return "\n".join(loaded)


def resume_chat_sync(message, history):
    return asyncio.run(resume_chat(message, history))


# ---------------- Gradio Helpers & UI ----------------

def load_resumes_to_ui(search_query="", sort_by="Newest First"):
    try:
        rows = db.get_resumes(search_query, sort_by)
        return [[row[0], row[1]] for row in rows]
    except Exception as e:
        print(f"Error fetching resumes: {e}")
        return []

def get_initial_resumes():
    return load_resumes_to_ui("", "Newest First")

def preview_selected(evt: gr.SelectData, df, current_doc_ids):
    row_idx = evt.index[0]
    try:
        import pandas as pd
        if isinstance(df, pd.DataFrame):
            doc_id = df.iloc[row_idx].iloc[0]
        else:
            doc_id = df[row_idx][0]
            
        file_path = db.get_file_path(doc_id)
        if file_path and os.path.exists(file_path):
            text = extract_candidate_data(file_path)
            # Also load to memory ALL_RESUME so they can chat about it
            global ALL_RESUME
            ALL_RESUME[doc_id] = text
            
            # Append doc_id to current_doc_ids if not already present
            if current_doc_ids:
                existing_ids = [d.strip() for d in current_doc_ids.split(",") if d.strip()]
                if doc_id not in existing_ids:
                    existing_ids.append(doc_id)
                new_doc_ids = ", ".join(existing_ids)
            else:
                new_doc_ids = doc_id
                
            return text, doc_id, new_doc_ids
        else:
            if current_doc_ids:
                existing_ids = [d.strip() for d in current_doc_ids.split(",") if d.strip()]
                if doc_id not in existing_ids:
                    existing_ids.append(doc_id)
                new_doc_ids = ", ".join(existing_ids)
            else:
                new_doc_ids = doc_id
            return f"⚠️ File not found at: {file_path}", doc_id, new_doc_ids
    except Exception as e:
        return f"⚠️ Error loading preview: {str(e)}", "", current_doc_ids or ""

def call_recruiter_tool(requirement_text: str):
    result = requirement_text.strip()
    return result, result

# Custom CSS for modern look
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

body, .gradio-container {
    font-family: 'Outfit', sans-serif !important;
}

.header-container {
    background: linear-gradient(135deg, #f5f7fa 0%, #e2ebf0 100%);
    padding: 24px;
    border-radius: 12px;
    margin-bottom: 24px;
    border: 1px solid #e1e8ed;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
}

.primary-btn {
    background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%) !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 6px rgba(79, 70, 229, 0.2) !important;
}

.primary-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 12px rgba(79, 70, 229, 0.3) !important;
}

.tab-nav button {
    font-weight: 600 !important;
    font-size: 15px !important;
}
"""

# Custom Javascript for table cell click-to-copy, hover highlighting, and Toast notifications
custom_js = """
function() {
    // Check click events globally on table cells
    document.addEventListener('click', function(e) {
        const td = e.target.closest('td');
        if (!td) return;
        const text = (td.innerText || td.textContent || "").trim();
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (uuidRegex.test(text)) {
            navigator.clipboard.writeText(text).then(function() {
                showToast("✓ Doc ID Copied: " + text);
            }).catch(err => {
                console.error("Could not copy Doc ID: ", err);
            });
        }
    });

    // Add pointer cursor and highlight on hover for cells containing UUIDs
    document.addEventListener('mouseover', function(e) {
        const td = e.target.closest('td');
        if (!td) return;
        const text = (td.innerText || td.textContent || "").trim();
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (uuidRegex.test(text)) {
            td.style.cursor = 'pointer';
            td.title = 'Click to copy Doc ID';
            td.style.backgroundColor = 'rgba(79, 70, 229, 0.1)';
            td.style.transition = 'background-color 0.2s';
        }
    });

    document.addEventListener('mouseout', function(e) {
        const td = e.target.closest('td');
        if (!td) return;
        const text = (td.innerText || td.textContent || "").trim();
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (uuidRegex.test(text)) {
            td.style.backgroundColor = '';
        }
    });

    function showToast(message) {
        let toast = document.getElementById('gradio-copy-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'gradio-copy-toast';
            toast.style.position = 'fixed';
            toast.style.bottom = '20px';
            toast.style.right = '20px';
            toast.style.backgroundColor = '#4f46e5';
            toast.style.color = '#fff';
            toast.style.padding = '12px 24px';
            toast.style.borderRadius = '8px';
            toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            toast.style.zIndex = '9999';
            toast.style.fontSize = '14px';
            toast.style.fontFamily = "'Outfit', sans-serif";
            toast.style.transition = 'opacity 0.3s ease';
            document.body.appendChild(toast);
        }
        toast.innerText = message;
        toast.style.opacity = '1';
        setTimeout(function() {
            toast.style.opacity = '0';
        }, 2000);
    }
}
"""

with gr.Blocks(css=custom_css, js=custom_js, theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="violet", neutral_hue="slate")) as demo:
    
    # Custom Header matching screenshots
    with gr.Column(elem_classes=["header-container"]):
        gr.Markdown(
            """
            # 📄 Resume Extraction System
            ### Upload resumes → store them → retrieve later using doc_id.
            **✓ Supports PDF, DOCX, TXT**
            """
        )

    # State for recruiter requirement
    recruiter_req_state = gr.State("")

    with gr.Tabs() as tabs:
        # Tab 1: Upload Resumes
        with gr.Tab("Upload Resumes"):
            with gr.Column():
                file_input = gr.File(
                    label="Upload / Add Resume(s)",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".txt"]
                )
                upload_btn = gr.Button("Upload ➔ Extract ➔ Save", elem_classes=["primary-btn"])
                upload_status = gr.Textbox(label="Upload Status", lines=6, interactive=False)

        # Tab 2: Stored Resumes
        with gr.Tab("Stored Resumes"):
            with gr.Column():
                refresh_btn = gr.Button("🔄 Refresh Resume List")
                
                with gr.Row():
                    search_input = gr.Textbox(
                        label="Search by filename or doc_id",
                        placeholder="e.g. python developer",
                        scale=4
                    )
                    search_btn = gr.Button("Search", scale=1)
                
                with gr.Row():
                    sort_dropdown = gr.Dropdown(
                        label="Sort by upload time",
                        choices=["Newest First", "Oldest First"],
                        value="Newest First",
                        scale=4
                    )
                    sort_btn = gr.Button("Sort", scale=1)

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Saved Resume Records")
                        resumes_df = gr.Dataframe(
                            headers=["Doc ID", "Filename"],
                            datatype=["str", "str"],
                            value=get_initial_resumes,
                            interactive=False,
                            wrap=True
                        )
                    with gr.Column(scale=1):
                        gr.Markdown("### Resume Preview")
                        selected_doc_id = gr.Textbox(
                            label="Selected Doc ID",
                            placeholder="Select a resume to see and copy its Doc ID...",
                            interactive=False,
                            show_copy_button=True
                        )
                        preview_box = gr.Textbox(
                            label="",
                            placeholder="Select a resume from the list to preview...",
                            interactive=False,
                            lines=18
                        )

        # Tab 3: Load by Doc ID
        with gr.Tab("Load by Doc ID"):
            with gr.Column():
                doc_id_input = gr.Textbox(
                    label="Enter doc_id(s), comma separated",
                    placeholder="Enter one or more UUIDs"
                )
                load_btn = gr.Button("Load Resumes", elem_classes=["primary-btn"])
                load_status = gr.Textbox(label="Status", lines=6, interactive=False)

        # Tab 4: Chat & Screening
        with gr.Tab("Chat & Screening"):
            with gr.Row():
                with gr.Column(scale=1):
                    recruiter_box = gr.Textbox(
                        label="Recruiter Requirement",
                        placeholder="E.g., Looking for Python developer with 3+ years exp in Django & SQL",
                        lines=5
                    )
                    recruiter_btn = gr.Button("Process Requirement", elem_classes=["primary-btn"])
                    recruiter_status = gr.Textbox(label="Requirement Status", lines=8, interactive=False)
                
                with gr.Column(scale=2):
                    chat = gr.ChatInterface(
                        fn=resume_chat,
                        type="messages",
                        title="Chat about Candidate(s)",
                        description="Ask questions or request candidates ranking/scoring based on requirements.",
                        additional_inputs=[recruiter_req_state]
                    )

    # ----------- Wiring -----------

    # Tab 1: Upload Resumes
    upload_btn.click(
        fn=multiple_resume_upload,
        inputs=file_input,
        outputs=upload_status
    )

    # Tab 2: Stored Resumes
    refresh_btn.click(
        fn=lambda: ("", "Newest First", load_resumes_to_ui("", "Newest First")),
        inputs=[],
        outputs=[search_input, sort_dropdown, resumes_df]
    )

    search_btn.click(
        fn=load_resumes_to_ui,
        inputs=[search_input, sort_dropdown],
        outputs=resumes_df
    )

    sort_btn.click(
        fn=load_resumes_to_ui,
        inputs=[search_input, sort_dropdown],
        outputs=resumes_df
    )

    resumes_df.select(
        fn=preview_selected,
        inputs=[resumes_df, doc_id_input],
        outputs=[preview_box, selected_doc_id, doc_id_input]
    )

    # Tab 3: Load by Doc ID
    load_btn.click(
        fn=handle_doc_id_input,
        inputs=doc_id_input,
        outputs=load_status
    )

    # Tab 4: Chat & Screening
    recruiter_btn.click(
        fn=call_recruiter_tool,
        inputs=[recruiter_box],
        outputs=[recruiter_req_state, recruiter_status]
    )

if __name__ == "__main__":
    demo.launch()

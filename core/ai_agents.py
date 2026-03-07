import os
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI
from typing import Dict
from agents import OpenAIChatCompletionsModel,Agent

load_dotenv(override=True)

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# google_api_key = os.getenv('GOOGLE_API_KEY')
# GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
# gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key)
# gemini_model = OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=gemini_client)


# ---------------- PERSONAL INFO AGENT ----------------


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
    model="gpt-4o-mini"
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
    model="gpt-4o-mini"
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
    model="gpt-4o-mini"
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
    model="gpt-4o-mini"
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
    model="gpt-4o-mini"
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
    model="gpt-4o-mini"
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
    model="gpt-4o-mini"
)




resume_master_instructions = """
You are a Resume Assistant for recruiters.

You will receive:
- One or more candidate resumes
- A recruiter question

Your responsibilities:
- Answer clearly and professionally
- Base answers strictly on the resume content
- Do NOT invent information
- If something is missing, say "Not mentioned in the resume"
- Keep responses concise and recruiter-friendly

Rules:
- Default output is plain text
- Only return JSON if the recruiter explicitly asks for JSON
"""

resume_master_agent = Agent(
    name="Resume Master Agent",
    instructions=resume_master_instructions,
    model="gpt-4o-mini"
)





# class ResumeAgent:
#     def __init__(self):
#         self.model = "gpt-4o-mini"


#     def score_resume(self, resume_text: str, requirement: str) -> Dict:
#         prompt = f"""
#         You are a resume scoring expert.
#         Recruiter requirement:
#         {requirement}

#         Candidate resume:
#         {resume_text}

#         Give a score from 0–100 and explain:
#         - Strong points
#         - Weak points
#         - One short summary reason
#         Return JSON like:
#         {{
#           "name": "Not extracted",
#           "score": 0,
#           "strong_points": [],
#           "weak_points": [],
#           "reason": ""
#         }}
#         """

#         result = openai_client.responses.create(
#             model=self.model,
#             input=prompt,
#         )

#         try:
#             return json.loads(result.output_text)
#         except:
#             return {
#                 "name": "Unknown",
#                 "score": 0,
#                 "strong_points": [],
#                 "weak_points": ["Scoring output parse failed"],
#                 "reason": ""
#             }

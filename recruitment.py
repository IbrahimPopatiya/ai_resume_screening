  
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
import gradio as gr
from dotenv import load_dotenv
from agents import Agent,Runner,trace,function_tool
from openai.types.responses import ResponseTextDeltaEvent
from typing import Dict
import sendgrid
from docx import Document
import os
from sendgrid.helpers.mail import Mail,Email,To,Content
import google.generativeai as genai
import asyncio



load_dotenv(override=True)

function_tool
def file_of_candidate(file_path: str) -> str:
    """
    Extract candidate data from resumes in PDF, DOCX, or TXT format.

    Args:
        file_path (str): Path to the resume file.

    Returns:
        str: Extracted candidate text data.
    """
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
def extract_candidate_information(resume_text: str):
    """
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



tools = [file_of_candidate,tool1,tool2,tool3,tool4,tool5,tool6,tool7,extract_candidate_information]




instructions = """
You are a Resume Master Agent. Your goal is to extract the most accurate and complete candidate information using the resume_agent tools.

Follow these steps carefully:
 Use the `file_of_candidate` tool FIRST to extract text content from the given file. 
   - Input: the file path
   - Output: candidate_data (resume text)

1. Extraction: Use the resume_agent tools to extract candidate information from the provided candidate_data. Ensure the following categories are always covered:
   - Personal Information (name, contact, email, address if available)
   - Skills (technical and soft)
   - Programming Languages
   - Experience (job title, company, duration, responsibilities)
   - Education (degree, university, year)
   - Projects (title, description, technologies used)
   - Achievements (awards, certifications, notable accomplishments)

2. Validation & Refinement: If extracted data is incomplete, unclear, or inconsistent, re-run the extraction tool or cross-check with alternate parsing tools until the output is precise and well-structured.

3. Output Formatting: Return the final extracted data in clean, structured JSON format with clear keys for each category. Example:
{
  "personal_info": {...},
  "skills": [...],
  "programming_languages": [...],
  "experience": [...],
  "education": [...],
  "projects": [...],
  "achievements": [...]
}

Crucial Rules:
- Always use the resume_agent tools for extraction, never write content manually.
- Ensure no category is left blank. If information is missing, return an empty array or null value instead of skipping.
- Final output must be in a single JSON object, well-formatted and complete.
"""

resume_master_agent = Agent(
    name = "Resume master agent",
    instructions=instructions,
    tools=tools,
    model="gpt-4o-mini"
)

message = "I want the projects that is build by candidate. there is file of the candidate 'ibrahim.txt' "

# with trace("Resume master agent"):
    # result = await Runner.run(resume_master_agent,message)



class ResumeChat:
    def __init__(self, agent):
        self.agent = agent
        self.history = []

    async def chat(self, message, history):
        # Keep track of conversation
        messages = [{"role": "system", "content": self.agent.instructions}]
        for user_msg,assistant_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})

        messages.append({"role": "user", "content": message})

        # Run the agent with the given message
        async with trace("Resume master agent chat"):
            result = await Runner.run(self.agent, message)

        return str(result)  # convert JSON/dict to string for 
    

# Create chat interface
resume_chat = ResumeChat(resume_master_agent)

demo = gr.ChatInterface(
    fn=resume_chat.chat,
    type="messages",
    title="Resume Screening Assistant",
    description="Upload a resume and ask questions about candidate info."
)

if __name__ == "__main__":
    demo.launch()

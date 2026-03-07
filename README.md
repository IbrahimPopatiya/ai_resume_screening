# AI Resume Screening & Feedback Agent

AI-powered recruitment assistant that automatically analyzes resumes, evaluates candidate suitability, answers recruiter questions, and generates feedback emails.

This project helps automate the **manual resume screening process** by using an AI agent capable of extracting information, evaluating candidate profiles, and assisting recruiters in decision-making.

---

# Project Overview

Traditional resume screening requires recruiters to manually read and evaluate hundreds of resumes.
This AI agent simplifies the process by:

* Reading resumes automatically
* Extracting candidate information
* Evaluating candidate fit for roles
* Answering recruiter questions
* Generating feedback emails

The system acts as an **AI recruitment assistant** that can significantly reduce screening time.

---

# Features

* Resume parsing and information extraction
* Candidate profile building
* AI-powered ranking and evaluation
* Recruiter question answering
* Automated feedback email generation
* Modular AI agent architecture

---

# Tech Stack

* Python
* FastAPI
* OpenAI API
* Gradio
* SendGrid
* PostgreSQL
* uv (Python package manager)

---

# Prerequisites

Before running the project, install the following:

* Python **3.10 or higher**
* Git
* uv package manager

Install uv if you do not have it installed:

```
pip install uv
```

---

# Clone the Repository

Clone the repository and navigate to the project folder.

```
git clone  https://github.com/IbrahimPopatiya/ai_resume_screening.git

cd YOUR_R
```

---

# Create Virtual Environment

Create a virtual environment using **uv**.

```
uv venv
```

This will create a `.venv` folder inside the project.

---

# Activate Virtual Environment

### Windows

```
.venv\Scripts\activate
```

### Linux / macOS

```
source .venv/bin/activate
```

---

# Install Dependencies

Install all project dependencies using the lock file.

```
uv sync
```

This will install packages defined in:

* `pyproject.toml`
* `uv.lock`

---

# Alternative Installation (Using pip)

If you prefer using pip:

```
pip install -r requirements.txt
```

---

# Running the Application

Start the FastAPI server.

```
python main.py
```

or

```
uvicorn main:app --reload
```

Once the server starts, open:

API Docs

```
http://127.0.0.1:8000/docs
```

---

# Project Structure

```
project-root
│
├── core
│   ├── __init__.py
│   ├── ai_agents.py
│   ├── chat_engine.py
│   ├── extractor.py
│   ├── intent_router.py
│   ├── parser.py
│   ├── profile_builder.py
│   ├── ranking_engine.py
│   └── utility.py
│
├── data
│
├── db
│   ├── __init__.py
│   ├── postgres.py
│   └── postgres.zip
│
├── utils
│
├── main.py
├── pyproject.toml
├── uv.lock
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Core Components

### Resume Parser

Extracts structured information from resumes.

### Profile Builder

Creates candidate profiles based on extracted data.

### Ranking Engine

Evaluates candidates and ranks them based on job fit.

### Chat Engine

Allows recruiters to ask questions about candidates.

Example:

* "Which candidate has the best Python experience?"
* "Show top candidates for backend role."

### Intent Router

Routes recruiter queries to the correct AI module.

---

# Database

The system uses **PostgreSQL** for storing candidate data and analysis results.

Database connection logic is handled in:

```
db/postgres.py
```

---

# Development Notes

* Dependencies are managed using **pyproject.toml**
* Exact package versions are locked in **uv.lock**
* Virtual environment is created using **uv venv**
* Always activate `.venv` before running the project

---

# Future Improvements

* Resume PDF upload interface
* Candidate dashboard
* Recruiter analytics
* AI interview question generator
* Docker deployment

---

# License

This project is open source and available under the MIT License.

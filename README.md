# GoFindAJob

GoFindAJob is a full-stack job search assistant that helps users:
- analyze resumes against job posts,
- generate answers to company questions,
- track applied jobs,
- and automate LinkedIn Easy Apply form filling.

---

## Main Functionalities

1. **User Authentication**
	 - Sign up, log in, log out, and get current session user.
	 - Session-based auth with secure cookie settings.

2. **Resume Analysis (AI-powered)**
	 - Upload a PDF resume + job posting text.
	 - Extract resume text with `PyPDF2`.
	 - Run Gemini agent analysis and return:
		 - match score (`1-10`),
		 - actionable advice.
	 - Save analysis history per user.

3. **Job Q&A (AI-powered)**
	 - Upload PDF resume + job posting + company question.
	 - Generate tailored response using Gemini agent.
	 - Save Q&A history per user.

4. **Applied Jobs Tracker**
	 - CRUD workflow for job applications:
		 - add,
		 - list,
		 - update,
		 - delete.

5. **LinkedIn Easy Apply Autofill**
	 - Launches browser automation to fill LinkedIn Easy Apply steps.
	 - Handles personal info fields and multi-step navigation.
	 - Attempts resume upload flow and reports detailed status.
	 - Runs as background task with task ID and polling endpoint.

---

## Tech Stack and Design Decisions (Concise)

- **Backend: Flask + SQLAlchemy + SQLite**
	- Chosen for fast API development and lightweight local persistence.

- **Frontend: Vanilla HTML/CSS/JavaScript**
	- Chosen for simplicity and fast iteration without framework overhead.

- **AI: Google ADK (`gemini-2.5-flash-lite`)**
	- Used for resume analysis and company-question answering.
	- Structured JSON output via Pydantic schemas for predictable parsing.

- **Automation: `nodriver` + Chrome**
	- Used for LinkedIn Easy Apply automation.
	- Decision: async control flow + selector fallback strategy for brittle UI.

- **Task Tracking: in-memory status store**
	- `UUID` task IDs + thread-safe dict for real-time autofill progress polling.
	- Decision: simple and fast for local/single-instance usage.

- **Background Execution**
	- Autofill runs in a background thread with its own event loop.
	- Decision: keep API responsive (`202 Accepted`) while long task executes.

---

## Installation and Run

### 1) Prerequisites

- Python 3.10+
- macOS/Windows/Linux
- Google Chrome installed (needed for autofill)

### 2) Clone and create environment

```bash
git clone <your-repo-url>
cd GoFindAJob
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

### 3) Environment variables

Create a `.env` file in project root (or export in shell):

```env
SECRET_KEY=your_secret_key
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key
```

Notes:
- `OPENAI_API_KEY` is used by LinkedIn autofill answer generation.
- Google ADK/Gemini features require Google credentials/API access.

### 4) Run project

#### Option A (recommended): run both frontend + backend

```bash
python run.py
```

- Frontend: `http://localhost:8000`
- Backend API: `http://localhost:5001`

#### Option B: backend only

```bash
python backend/run.py
```

---

## API List

### Auth

- `POST /api/signup` — create account
- `POST /api/login` — login
- `POST /api/logout` — logout
- `GET /api/me` — current user
- `GET /api/users/<user_id>` — get user by ID

### Health

- `GET /api/health` — health check

### Resume Analysis

- `POST /api/analyze-resume`
	- form-data: `resume` (PDF), `job_post`
	- returns analysis object with score/advice
- `GET /api/analyses`
	- list current user’s analysis history

### Job Q&A

- `POST /api/job-qa`
	- form-data: `resume` (PDF), `job_post`, `question`
	- returns generated answer
- `GET /api/job-qa-history`
	- list current user’s Q&A history

### Applied Jobs

- `GET /api/applied-jobs` — list jobs
- `POST /api/applied-jobs` — add job
- `PUT /api/applied-jobs/<job_id>` — update job
- `DELETE /api/applied-jobs/<job_id>` — delete job

### LinkedIn Autofill

- `POST /api/autofill-application`
	- form-data: `job_link`, `resume` (PDF), optional `first_name`, `last_name`, `email`, `phone`
	- starts background autofill task, returns `task_id`
- `GET /api/autofill-status/<task_id>`
	- poll task progress/status

---

## Project Notes

- Database: SQLite (`gofindajob.db`)
- CORS is enabled for local frontend/backend ports.
- Resume uploads for autofill are persisted in `resumes/` under project root.

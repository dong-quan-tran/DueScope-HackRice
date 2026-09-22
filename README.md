# DueScope

[Live demo](https://due-scope-hack-rice.vercel.app/demo) · Built for **HackRice 16 — Work & Productivity**

DueScope is an evidence-first deadline and opportunity manager for students. It turns fragmented academic and job-search information into a review-first workflow: identify potential deadlines, preserve the original evidence, validate dates and time zones, detect conflicts, retain history, and require explicit user approval before a Calendar event is created or updated.

## Live demo

Open the public app:

- [DueScope live demo](https://due-scope-hack-rice.vercel.app/demo)

The live demo supports this Google workflow:

1. Select **Sign in with Google** to create a DueScope session.
2. Select **Connect Google Calendar** to grant the optional Google data permissions used by DueScope.
3. Review a verified or updated deadline and its source evidence.
4. Select **Approve for export and sync**.
5. Select **Sync this deadline to Google**.
6. DueScope creates or updates the approved event in the connected user's Google Calendar.

DueScope never creates Calendar events merely because it found a deadline. Calendar writes require an explicit user approval and a separate explicit sync action.

## Privacy and integrations

### Google account and Calendar

- Google identity sign-in establishes a DueScope session; it is separate from optional Gmail and Calendar data authorization.
- Gmail access is read-only. DueScope does not send, archive, label, delete, or otherwise modify Gmail messages.
- Google Calendar is used only for approved academic deadlines and approved job-reminder proposals.
- DueScope requests the smallest practical permissions for its workflow:
  - `openid`, `email`, and `profile` for identity.
  - `https://www.googleapis.com/auth/gmail.readonly` for read-only Gmail scanning.
  - `https://www.googleapis.com/auth/calendar.events` for approved Calendar-event creation or updates.
- Google credentials are stored server-side and are not exposed to browser JavaScript.
- Browser privacy settings that block third-party cookies can prevent sessions between the Vercel frontend and Render backend. For the most reliable demo experience, use a standard browser profile with third-party cookies enabled.

### Canvas

Canvas access is institution-dependent. DueScope can import courses and upcoming assignments for configured Canvas accounts, but it does not yet offer universal Canvas OAuth for every Canvas institution in the public demo.

Do not paste Canvas tokens into URLs, GitHub issues, or chat. A future version will add a per-user Canvas OAuth and/or securely stored personal-access-token connection flow.

### Review-first rules

- A candidate must retain source evidence and include a usable title and valid time information when a date/time is required.
- A conflicting academic date becomes a review proposal; it never silently overwrites the saved deadline.
- Accepting a proposal preserves prior deadline history, marks the event `updated`, and resets Calendar approval.
- Rejecting a proposal leaves the canonical event unchanged.
- Gmail-derived job reminders are proposed only for explicit assessment deadlines, interview-scheduling deadlines, or confirmed interview times.
- Google Calendar changes occur only after the user approves an eligible academic event or a specific job-reminder proposal.

## How it works

```text
Canvas import, pasted course update, or read-only Gmail job message
                              |
                              v
Structured extraction and normalization
                              |
                              v
Validation: title, date/time, timezone, and retained source evidence
                              |
                              v
Reconciliation against saved academic events or job records
                              |
                              +-- New academic event: create canonical event
                              |
                              +-- Same academic deadline: leave event unchanged
                              |
                              +-- Different academic deadline: create review proposal
                              |                                  |
                              |                                  v
                              |                    User accepts or keeps saved date
                              |
                              +-- Explicit job date: create pending reminder proposal
                                                                 |
                                                                 v
                                                User approves or dismisses proposal
                                                                 |
                                                                 v
                                        Export approved ICS events or create/update
                                      one Google Calendar event after explicit sync
```

## Features

### Academic deadline workflow

- Source-backed academic deadlines with evidence excerpts and history
- Canvas course lookup and import of upcoming assignments for configured Canvas accounts
- Pasted Canvas announcements, instructor emails, syllabus excerpts, and other course notices
- Structured local AI extraction with Ollama (`gemma3:4b`)
- Optional Gemini extraction when configured
- Candidate validation for titles, evidence, ISO-8601 dates, and time zones
- Reconciliation that distinguishes new, unchanged, and conflicting deadlines
- Reviewable deadline-change proposals
- Event statuses including `verified`, `updated`, `needs_review`, and `canceled`
- Deadline filters for the next 7, 14, or 30 days, or the full semester
- High-workload alert display
- Approval-gated `.ics` export
- Approval-gated Google Calendar create/update sync for connected Google users

### Job-application workflow

- Read-only Gmail search and parsing for recruiting-system messages
- Job application records with inferred company, role, status, next action, source metadata, and history
- Review/edit controls for inferred job information
- Pending reminder proposals for explicit online-assessment and interview-scheduling deadlines
- Exact evidence excerpts and Gmail search links
- Explicit approve/dismiss controls
- Approval-gated Google Calendar create/update behavior for job reminders

## Example: approved deadline to Calendar

A student reviews **Midterm Exam** and the retained course evidence:

```text
Midterm Exam — Wednesday, September 23, 7:00 PM
```

The student selects:

```text
Approve for export and sync
```

DueScope marks the event approved but still does not write to Google Calendar. The student then selects:

```text
Sync this deadline to Google
```

DueScope creates or updates the corresponding Google Calendar event and returns a Calendar link when available.

## Tech stack

| Area | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Icons | Lucide React |
| Backend | Python, FastAPI, Pydantic |
| Database | PostgreSQL in deployed environments; SQLite for local development/tests where configured |
| Testing | pytest |
| Calendar export | icalendar |
| Google identity and data connection | OAuth 2.0 with PKCE |
| Google Calendar | Google Calendar API |
| Gmail ingestion | Gmail API with read-only search and message parsing |
| Course ingestion | Canvas REST API |
| Local AI extraction | Ollama with Gemma 3 |
| Optional cloud AI | Google Gemini API |

## Local setup

### Prerequisites

Install:

- Git
- Python 3.11 or newer
- Node.js 20 or newer
- npm
- Ollama for local AI extraction

Check versions:

```powershell
python --version
node --version
npm --version
git --version
ollama --version
```

Install Ollama from [ollama.com](https://ollama.com/) if needed.

### 1. Clone

```powershell
git clone [https://github.com/dong-quan-tran/DueScope-HackRice.git](https://github.com/dong-quan-tran/DueScope-HackRice.git)
cd DueScope-HackRice
```

### 2. Create the Python environment

```powershell
python -m venv backend\.venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\backend\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt

cd frontend
npm install
cd ..
```

Do not commit `frontend\node_modules`.

### 4. Configure local environment variables

Create a local `.env` from the example:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`, credentials, access/refresh tokens, Canvas tokens, database URLs, or encryption keys.

Typical local configuration:

```text
APP_ENV=development
API_PUBLIC_URL=http://127.0.0.1:8001
PUBLIC_APP_URL=http://localhost:3000
FRONTEND_ORIGINS=http://localhost:3000
DATABASE_URL=sqlite:///./duescope.db

APP_SESSION_SECRET=
TOKEN_ENCRYPTION_KEY=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8001/api/google/auth/callback

EXTRACTION_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:4b

CANVAS_BASE_URL=
CANVAS_ACCESS_TOKEN=

GEMINI_API_KEY=
```

For local frontend development, create `frontend\.env.local`:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001
NEXT_PUBLIC_DEMO_MODE=false
```

Download the recommended local extraction model:

```powershell
ollama pull gemma3:4b
```

Provider options:

```text
EXTRACTION_PROVIDER=ollama
EXTRACTION_PROVIDER=gemini
EXTRACTION_PROVIDER=auto
```

### 5. Configure Google OAuth

Google identity sign-in uses this callback:

```text
http://127.0.0.1:8001/api/auth/callback
```

The optional Gmail and Calendar data connection uses this callback:

```text
http://127.0.0.1:8001/api/google/auth/callback
```

For deployed production, register the exact equivalents under your Render backend domain:

```text
[https://duescope.onrender.com/api/auth/callback](https://duescope.onrender.com/api/auth/callback)
[https://duescope.onrender.com/api/google/auth/callback](https://duescope.onrender.com/api/google/auth/callback)
```

In Google Cloud:

1. Create or select a project.
2. Enable the Google Calendar API and Gmail API.
3. Configure the OAuth consent screen and add test users while the app remains in Testing.
4. Create an OAuth 2.0 Web application client.
5. Register the exact callback URLs above.
6. Set the client ID and client secret only in local environment files or deployment secret settings.

### 6. Run locally

In one terminal, make sure Ollama is available:

```powershell
ollama list
ollama serve
```

Run backend tests from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v
```

Start the backend:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8001
```

Start the frontend in another terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000/demo
```

Backend API documentation:

```text
http://127.0.0.1:8001/docs
```

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Confirm the API is running |
| `GET` | `/api/auth/login` | Start Google identity sign-in |
| `GET` | `/api/auth/callback` | Receive the Google identity callback |
| `GET` | `/api/auth/me` | Return the signed-in user’s safe display data |
| `POST` | `/api/auth/logout` | Revoke the current app session |
| `GET` | `/api/demo/workspace` | Get displayed courses, events, changes, workload, and proposals |
| `GET` | `/api/events` | List canonical academic events |
| `GET` | `/api/events/{event_id}` | Get academic event details, evidence, and history |
| `PATCH` | `/api/events/{event_id}/approval` | Approve or unapprove an exportable academic event |
| `POST` | `/api/events/reconcile` | Reconcile an academic-event candidate |
| `GET` | `/api/events/proposals/pending` | List unresolved academic proposals |
| `POST` | `/api/events/proposals/{proposal_id}/accept` | Accept a proposal and update the canonical event |
| `POST` | `/api/events/proposals/{proposal_id}/reject` | Reject a proposal and preserve the canonical event |
| `POST` | `/api/sources/extract` | Extract academic deadline candidates from pasted text |
| `POST` | `/api/sources/extract-and-reconcile` | Extract, validate, and reconcile pasted source text |
| `GET` | `/api/canvas/profile` | Get Canvas profile information for configured Canvas access |
| `GET` | `/api/canvas/courses` | Load Canvas courses for configured Canvas access |
| `GET` | `/api/canvas/courses/{course_id}/assignments` | List Canvas assignments |
| `POST` | `/api/canvas/import-course/{course_id}` | Import upcoming Canvas deadlines |
| `POST` | `/api/calendar/export` | Export approved academic events as ICS |
| `GET` | `/api/google/auth/start` | Start optional Google Gmail/Calendar authorization |
| `GET` | `/api/google/auth/callback` | Receive the Google Gmail/Calendar callback |
| `GET` | `/api/google/auth/status` | Check the current user’s Google connection status |
| `POST` | `/api/google/auth/disconnect` | Delete the current user’s Google data connection |
| `POST` | `/api/google/calendar/sync-approved` | Sync explicitly approved academic deadlines |
| `GET` | `/api/jobs` | List tracked job applications |
| `POST` | `/api/jobs/scan` | Read-only Gmail scan for job updates |
| `PATCH` | `/api/jobs/{job_id}` | Review and update a tracked job application |
| `GET` | `/api/jobs/proposals` | List job Calendar proposals |
| `POST` | `/api/jobs/proposals/{proposal_id}/approve` | Approve a reminder and create/update Google Calendar |
| `POST` | `/api/jobs/proposals/{proposal_id}/dismiss` | Dismiss a reminder without changing Google Calendar |

## Development checks

Run before committing:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v

cd frontend
$env:NEXT_PUBLIC_API_BASE_URL = "[https://duescope.onrender.com](https://duescope.onrender.com)"
npm run build
Remove-Item Env:\NEXT_PUBLIC_API_BASE_URL -ErrorAction SilentlyContinue
cd ..

git diff --check
git status --short
```

## Limitations and next steps

- The displayed workspace still includes seeded/demo data; complete per-user migration of all courses, events, proposals, and job records remains a future milestone.
- Canvas import currently requires a configured Canvas connection and is not yet universal institutional Canvas OAuth.
- Gmail scanning requires a connected Google account and matching recruiting-message queries.
- Job-status inference and reminder detection are heuristic and intended for user review.
- Ollama must be installed and running for local AI extraction.
- Gemini is optional and requires usable API access.
- Future work includes universal per-user Canvas connection, complete per-user workspace persistence, background sync, notifications, richer workload forecasting, additional student platforms, and a custom-domain first-party session architecture.

## Repository safety

- Do not commit `.env`, API keys, Canvas tokens, Gmail credentials, OAuth credentials, OAuth access/refresh tokens, session secrets, encryption keys, database URLs, local databases, virtual environments, generated ICS files, `frontend\node_modules`, or `frontend\.next`.
- Save source and documentation files as UTF-8.
- Run backend tests and the frontend production build before merging.
- Use focused branches and review changes before merging to `main`.

## Team

- Khoi Anh Le Nguyen — [@ngkhoi111](https://github.com/ngkhoi111)
- Dong Quan Tran — [@dong-quan-tran](https://github.com/dong-quan-tran)

## HackRice 16

DueScope was built for the **HackRice 16 Work & Productivity** track. We plan to keep building it.

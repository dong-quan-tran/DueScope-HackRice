# DueScope

[Live public demo](https://due-scope-hack-rice.vercel.app/demo) · Built for **HackRice 16 — Work & Productivity**

DueScope is an evidence-backed deadline and opportunity manager for students. It turns fragmented academic and job-search information into a single **review-first** workflow: extract potential deadlines, retain the original evidence, validate dates and time zones, detect conflicts, preserve history, and require explicit approval before anything reaches a calendar.

## Public demo and privacy

The public demo uses safe seeded data and is intended to show the review workflow without requesting access to a visitor’s personal accounts:

- [Open the public demo](https://due-scope-hack-rice.vercel.app/demo)
- Canvas course import and Google Calendar synchronization are available in the private-alpha/local environment.
- The public demo does not request Canvas, Gmail, or Google Calendar authorization from visitors.
- Gmail ingestion is read-only. DueScope does not send, archive, label, or delete messages.
- Calendar exports and Google Calendar writes require explicit user approval.

## The problem

Students receive deadline changes through Canvas, announcements, instructor emails, syllabi, and messages. Separately, job applications generate recruiting emails, online-assessment deadlines, and interview scheduling requests. A calendar entry that is silently overwritten—or a reminder created from ambiguous text—can create more harm than help.

DueScope treats source data and AI output as **proposals**, not authority.

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
                                       one Google Calendar event after approval
```

### Review-first rules

- A candidate must have a usable title, a valid ISO-8601/timezone-aware date when required, retained source evidence, and an evidence excerpt grounded in the original source.
- A conflicting academic date becomes a proposal; it never silently overwrites the saved deadline.
- Accepting a proposal preserves the prior deadline in history, marks the event `updated`, and resets its calendar approval.
- Rejecting a proposal leaves the canonical event unchanged.
- Gmail is read-only. A job reminder is created only from explicit assessment deadlines, interview-scheduling deadlines, or confirmed interview times.
- Google Calendar changes occur only after a user explicitly approves an eligible academic event or a specific job-reminder proposal.

## Features

### Academic deadline workflow

- Canvas course lookup and import of upcoming assignments with due dates
- Pasted Canvas announcements, instructor emails, syllabus excerpts, and other course notices
- Structured local AI extraction with Ollama (`gemma3:4b`)
- Optional Gemini extraction when configured
- Candidate validation for title, evidence, ISO-8601 dates, and time zones
- Reconciliation that distinguishes new, unchanged, and conflicting deadlines
- Reviewable academic deadline-change proposals
- Evidence panel and deadline-history timeline
- Statuses including `verified`, `updated`, `needs_review`, and `canceled`
- Deadline display filters: next 7, 14, or 30 days, or all semester
- High-workload alert display
- Approval-gated standard `.ics` export
- Google Calendar sync for user-approved, trusted academic events in private alpha

### Job-application workflow

- Read-only Gmail search and parsing for recruiting-system messages
- Job application records with inferred company, role, status, next action, source metadata, and history
- Review/edit controls for correcting inferred job information
- Pending reminder proposals for explicit online-assessment and interview scheduling deadlines
- Exact evidence excerpts and Gmail search links for review
- Explicit approve/dismiss controls
- Google Calendar create-or-update behavior for approved reminders in private alpha

### Public demo behavior

The public demo deliberately demonstrates product boundaries:

- It displays safe sample deadlines, evidence, workload, and change-review states.
- It describes Canvas import and Google Calendar sync as private-alpha integrations rather than requesting visitor credentials.
- It does not expose a visitor’s Canvas, Gmail, or Google Calendar account to the demo.

## Example: deadline-change review

Given this course update:

```text
Programming Assignment 2 has been extended.
It is now due Monday, September 21, 2026 at 11:59 PM in Canvas.
```

DueScope compares the extracted candidate to the saved canonical event:

```text
Saved event: Programming Assignment 2, due Sept. 18
Candidate: Programming Assignment 2, due Sept. 21
Result: proposal requiring user review
```

The Sept. 18 deadline remains unchanged until the user selects **Accept change**. On acceptance, DueScope saves Sept. 18 in event history, applies Sept. 21 as the current deadline, marks the event `updated`, and clears its prior calendar approval.

## Tech stack

| Area | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Icons | Lucide React |
| Backend | Python, FastAPI, Pydantic |
| Testing | pytest |
| Calendar export | icalendar |
| Google integration | OAuth 2.0 with PKCE, Google Calendar API |
| Gmail ingestion | Gmail API, read-only search and message parsing |
| Course ingestion | Canvas REST API |
| Local AI extraction | Ollama with Gemma 3 |
| Optional cloud AI | Google Gemini API |
| Current demo storage | In-memory seeded workspace |

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

### 1. Clone the repository

```powershell
git clone https://github.com/dong-quan-tran/DueScope-HackRice.git
cd DueScope-HackRice
```

### 2. Create a Python environment

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

Do not commit `.env`, credentials, access tokens, or OAuth token files.

Common local settings:

```text
APP_ENV=development
API_PUBLIC_URL=http://127.0.0.1:8001
PUBLIC_APP_URL=http://localhost:3000
FRONTEND_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001
NEXT_PUBLIC_DEMO_MODE=false

EXTRACTION_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:4b

CANVAS_BASE_URL=
CANVAS_ACCESS_TOKEN=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8001/api/google/auth/callback
GEMINI_API_KEY=
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

Use `ollama` for the most reliable offline/local demo. Gemini is optional and requires usable API access.

### 5. Optional Google Calendar setup

Google Calendar sync requires a Google Cloud OAuth client and the Google Calendar API.

1. Create or select a Google Cloud project.
2. Enable the Google Calendar API.
3. Configure the OAuth consent screen and add test users when the app is in Testing mode.
4. Create an OAuth 2.0 **Web application** client.
5. Add this authorized redirect URI:

   ```text
   http://127.0.0.1:8001/api/google/auth/callback
   ```

6. Store client credentials locally as `backend/credentials.json` if your backend is configured for that file.
7. Keep `backend/credentials.json` and `backend/token.json` Git-ignored.

The local authorization start route is:

```text
http://127.0.0.1:8001/api/google/auth/start
```

### 6. Run Ollama, tests, backend, and frontend

In one terminal, make sure Ollama is available:

```powershell
ollama list
ollama serve
```

Run tests from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v
```

Start the backend:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8001
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000
```

Backend API documentation is available at:

```text
http://127.0.0.1:8001/docs
```

## Local demo workflow

### Academic workflow

1. Open `http://localhost:3000`.
2. Configure Canvas locally, then use **Import from Canvas** to load courses and import upcoming assignments.
3. Select an imported or seeded deadline to inspect its evidence and history.
4. In **Scan a course update**, paste a course announcement such as:

   ```text
   Programming Assignment 2 has been extended.
   It is now due Monday, September 21, 2026 at 11:59 PM in Canvas.
   ```

5. Select **Scan for deadlines**.
6. Review the resulting deadline proposal, including the saved date, proposed date, source excerpt, and rationale.
7. Select **Accept change** to update the canonical event, or **Keep saved date** to reject the proposal.
8. Approve an eligible trusted event and export it as ICS or sync it to Google Calendar locally.

### Job workflow

1. Configure local Gmail/Google authorization if you plan to scan mail or approve calendar reminders.
2. Use **Scan for new job updates**. Gmail scanning is read-only.
3. Review a job application’s inferred status, next action, source details, and history.
4. Inspect a pending job reminder’s exact evidence.
5. Approve it to create/update a Google Calendar reminder, or dismiss it with no calendar change.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Confirm the API is running |
| `GET` | `/api/demo/workspace` | Get courses, events, changes, workload, and proposals |
| `GET` | `/api/events` | List canonical academic events |
| `GET` | `/api/events/{event_id}` | Get academic event details, evidence, and history |
| `PATCH` | `/api/events/{event_id}/approval` | Approve or unapprove an exportable academic event |
| `POST` | `/api/events/reconcile` | Reconcile an academic event candidate |
| `GET` | `/api/events/proposals/pending` | List unresolved academic proposals |
| `POST` | `/api/events/proposals/{proposal_id}/accept` | Accept a proposal and update the canonical event |
| `POST` | `/api/events/proposals/{proposal_id}/reject` | Reject a proposal and preserve the canonical event |
| `POST` | `/api/sources/extract` | Extract academic deadline candidates from pasted text |
| `POST` | `/api/sources/extract-and-reconcile` | Extract, validate, and reconcile pasted source text |
| `GET` | `/api/canvas/profile` | Get Canvas profile information |
| `GET` | `/api/canvas/courses` | Load Canvas courses |
| `GET` | `/api/canvas/courses/{course_id}/assignments` | List Canvas assignments |
| `POST` | `/api/canvas/import-course/{course_id}` | Import upcoming Canvas deadlines |
| `POST` | `/api/calendar/export` | Export approved academic events as ICS |
| `GET` | `/api/google/auth/start` | Start Google OAuth authorization |
| `GET` | `/api/google/auth/callback` | Receive the Google OAuth callback |
| `GET` | `/api/google/auth/status` | Check Google Calendar connection status |
| `POST` | `/api/google/calendar/sync-approved` | Sync approved academic deadlines |
| `GET` | `/api/jobs` | List tracked job applications |
| `POST` | `/api/jobs/scan` | Read-only Gmail scan for job updates |
| `PATCH` | `/api/jobs/{job_id}` | Review and update a tracked job application |
| `GET` | `/api/jobs/proposals` | List job calendar proposals |
| `POST` | `/api/jobs/proposals/{proposal_id}/approve` | Approve a job reminder and create/update Google Calendar |
| `POST` | `/api/jobs/proposals/{proposal_id}/dismiss` | Dismiss a job reminder without changing Google Calendar |

## Development checks

Run before committing:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v

cd frontend
npm run build
cd ..

git diff --check
git status
```

## Limitations and next steps

- The current workspace uses in-memory demo storage, so backend restarts reset seeded data, imported Canvas records, proposals, approvals, and accepted changes.
- Canvas import requires valid local Canvas API configuration.
- Gmail scanning requires configured local authorization and matching job-message queries.
- Job-status inference and reminder detection are heuristic and designed for user review.
- Ollama must be installed and running for local AI scanning.
- Gemini is optional and needs usable API access.
- Persistent storage, scheduled background sync, notifications, richer workload forecasting, more student platforms, and a custom domain are future work.

## Repository safety

- Do not commit `.env`, API keys, Canvas tokens, Gmail credentials, OAuth credentials, OAuth token files, local databases, virtual environments, generated ICS files, `frontend\node_modules`, or `frontend\.next`.
- Save source and documentation files as UTF-8.
- Run backend tests and the frontend production build before merging.
- Use focused branches and review changes before merging to `main`.

## Team

- Khoi Anh Le Nguyen — [@ngkhoi111](https://github.com/ngkhoi111)
- Dong Quan Tran — [@dong-quan-tran](https://github.com/dong-quan-tran)

## HackRice 16

DueScope was built for the **HackRice 16 Work & Productivity** track. We plan to keep building it.
# DueScope

DueScope is an evidence-backed academic deadline manager built for HackRice 16's Work & Productivity track.

Students receive deadlines through Canvas, announcements, emails, syllabi, and class messages. DueScope turns those sources into a reviewable deadline workflow: it extracts candidate deadlines, validates evidence and timezones, detects conflicts with saved events, and exports approved deadlines as an ICS calendar file. It also supports optional Google OAuth and a verified Google Calendar test-sync integration for local development.

## Core idea

A source or AI model can suggest a deadline change, but it must never silently overwrite a student's saved calendar.

DueScope uses a review-first workflow:

```text
Canvas import or pasted course update
                |
                v
Structured AI deadline extraction
                |
                v
Candidate validation
- title is present
- due_at is ISO-8601 and timezone-aware
- source evidence appears in the original input
                |
                v
Reconciliation with saved events
                |
                +-- New event: create canonical event
                |
                +-- Same date: leave event unchanged
                |
                +-- Different date: create a proposal
                                  |
                                  v
                    User accepts or rejects the proposal
                                  |
                                  v
                    Approve trusted events and export ICS
                                  |
                                  +-- Optional Google Calendar test sync
```

When a user accepts a proposal, DueScope preserves the old deadline in history, applies the new source evidence and date, marks the event as `updated`, and resets calendar approval. A rejected proposal leaves the saved event unchanged.

## Current status

DueScope is a working full-stack MVP with:

- Next.js and TypeScript dashboard
- FastAPI backend and REST API
- Canvas course lookup and upcoming-deadline import
- Local Ollama AI extraction using `gemma3:4b`
- Optional Gemini integration when a funded Gemini project is available
- Candidate validation for title, evidence, and timezone-aware dates
- Reviewable deadline-change proposals
- Explicit proposal accept and reject actions
- Preserved event history after accepted changes
- Approval-gated ICS calendar export
- Google OAuth connection flow with PKCE
- Google Calendar event creation for connected users through a local test-sync endpoint
- High-workload alert display
- Automated validation and reconciliation tests

The application currently uses in-memory demo storage. Restarting the backend resets seeded events, imported records, proposals, approvals, and accepted changes. Google OAuth tokens are stored locally for development in `backend/token.json` and remain available across backend restarts unless removed.

## Features

### Dashboard

The DueScope dashboard includes:

- Upcoming deadlines sorted by due date
- Course color indicators
- Status badges for `verified`, `updated`, `needs_review`, and `canceled`
- Evidence panel for selected events
- Deadline history timeline
- Pending deadline-proposal review cards
- Accept change and Keep saved date controls
- Approval controls for exportable events
- High-workload warning
- Canvas import controls
- Course-update scanning form
- ICS calendar export

### AI extraction

DueScope uses structured AI output to extract academic obligations from pasted:

- Canvas announcements
- Instructor emails
- Syllabus excerpts
- Other course notices

The default local provider is Ollama with `gemma3:4b`. Gemini can be used when configured with an API key tied to a project with usable Gemini credits.

Example source text:

```text
Programming Assignment 2 has been extended.
It is now due Monday, September 21, 2026 at 11:59 PM in Canvas.
```

Expected outcome:

```text
Existing saved event: Programming Assignment 2, due Sept. 18
Extracted candidate: Programming Assignment 2, due Sept. 21
Result: proposed_change
```

The Sept. 18 event stays unchanged until the user accepts the proposal.

### Candidate validation

Before reconciliation, extracted candidates are checked for:

- A nonblank title
- A due date and time when one is required
- A valid ISO-8601 timestamp
- Timezone information in populated timestamps
- A nonblank source excerpt
- An exact source excerpt found in the original pasted source text

Candidates with missing or unreliable information are marked for review. They are never automatically approved for calendar export.

### Proposal review

When an extracted or imported deadline conflicts with an existing saved event, DueScope shows:

- The current saved deadline
- The proposed deadline
- The source evidence supporting the proposal
- Source priority and recency reasoning
- Accept change control
- Keep saved date control

Accepting a proposal:

- Updates the canonical event
- Saves the previous current deadline in history
- Adds the accepted date as the current history version
- Changes status to `updated`
- Clears prior export approval

Rejecting a proposal:

- Keeps the canonical event unchanged
- Resolves the proposal as `rejected`

### Canvas import

DueScope can:

1. Load available Canvas courses.
2. Let the user select a course.
3. Import upcoming Canvas assignment deadlines.
4. Skip past assignments by default.
5. Create canonical events for new work.
6. Create proposals instead of overwriting conflicting saved dates.

Canvas access requires valid local Canvas configuration.

### Calendar export and Google sync

Only events that are both:

- Approved by the user, and
- Marked `verified` or `updated`

can be exported.

DueScope generates a standard `.ics` file that can be imported into compatible calendar applications.

DueScope can also connect to a user's Google account through OAuth and create Calendar events in the user's primary Google Calendar. Google authorization uses PKCE and stores the local OAuth token in `backend/token.json`.

The current Google Calendar route is a Phase 4 local-development integration test. It creates a clearly labeled `DueScope test sync` event so developers can verify OAuth credentials and Google Calendar API access. A future iteration will sync selected approved DueScope deadlines, persist Google event IDs, and avoid duplicate calendar events.

## Tech stack

| Area | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Icons | Lucide React |
| Backend | Python, FastAPI, Pydantic |
| Testing | pytest |
| Calendar export | icalendar |
| Google integration | Google OAuth 2.0 with PKCE, Google Calendar API |
| OAuth token storage | Local `backend/token.json` for development |
| Local AI extraction | Ollama with Gemma 3 |
| Optional cloud AI | Google Gemini API |
| Course ingestion | Canvas REST API |
| Current storage | In-memory demo workspace |

## Prerequisites

Install:

- Git
- Python 3.11 or newer
- Node.js 20 or newer
- npm
- Ollama
- VS Code recommended

Check versions:

```powershell
python --version
node --version
npm --version
git --version
ollama --version
```

Install Ollama from [ollama.com](https://ollama.com/) if it is not already available.

## Quick start

### 1. Clone the repository

```powershell
git clone https://github.com/OWNER/DueScope.git
cd DueScope
```

Replace `OWNER` with the GitHub user or organization that owns the repository.

### 2. Create and activate the Python environment

```powershell
python -m venv backend\.venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\backend\.venv\Scripts\Activate.ps1
```

Your prompt should show:

```text
(.venv)
```

### 3. Install backend dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

If Google Calendar dependencies are not already included in `backend/requirements.txt`, install them with:

```powershell
python -m pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 4. Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

Do not commit `frontend\node_modules`.

### 5. Configure environment variables

Create a local `.env` file from the example if available:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`.

For local Ollama extraction, configure:

```text
EXTRACTION_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:4b
```

Download the recommended model if it is not already installed:

```powershell
ollama pull gemma3:4b
```

Optional Gemini configuration:

```text
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.6-flash
```

Provider choices:

```text
EXTRACTION_PROVIDER=ollama
EXTRACTION_PROVIDER=gemini
EXTRACTION_PROVIDER=auto
```

Use `ollama` for the most reliable offline demo. Use `auto` only when Gemini has valid funded access; it tries Gemini first and falls back to Ollama if Gemini fails.

Optional Canvas configuration:

```text
CANVAS_BASE_URL=
CANVAS_ACCESS_TOKEN=
```

### 5a. Configure Google Calendar sync (optional)

Google Calendar sync requires a Google Cloud OAuth client and the Google Calendar API.

1. In Google Cloud Console, create or select a project.
2. Enable the **Google Calendar API**.
3. Configure the OAuth consent screen and add your Google account as a test user if the app is in Testing mode.
4. Create an OAuth 2.0 **Web application** client.
5. Add this exact authorized redirect URI:

   ```text
   http://127.0.0.1:8001/api/google/auth/callback
   ```

6. Download the OAuth client JSON and save it as:

   ```text
   backend/credentials.json
   ```

7. Ensure these local secret/token files are Git-ignored:

   ```text
   backend/credentials.json
   backend/token.json
   ```

After starting the backend, begin Google authorization in a browser:

```text
http://127.0.0.1:8001/api/google/auth/start
```

After authorization succeeds, verify the connection:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/google/auth/status
```

Expected result:

```text
connected
---------
True
```

### 6. Start Ollama

In a terminal, verify the model is available:

```powershell
ollama list
```

If the Ollama service is not already running:

```powershell
ollama serve
```

Keep Ollama running while using the AI scanner.

### 7. Run backend tests

From the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v
```

### 8. Start the backend

DueScope uses port `8001` in local development:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8001
```

API documentation:

```text
http://127.0.0.1:8001/docs
```

### 9. Start the frontend

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000
```

The frontend expects the API at:

```text
http://127.0.0.1:8001
```

To use a different backend URL, configure `NEXT_PUBLIC_API_URL` in the frontend environment file and restart the frontend server.

## Demo workflow

For the most reliable demo, start from a freshly restarted backend so the seeded workspace is restored.

1. Open `http://localhost:3000`.
2. Select **Programming Assignment 2** and show its existing Sept. 18 deadline and source evidence.
3. In **Scan a course update**, paste:

   ```text
   Programming Assignment 2 has been extended.
   It is now due Monday, September 21, 2026 at 11:59 PM in Canvas.
   ```

4. Select **Scan for deadlines**.
5. Show the **Deadline proposals** card:
   - saved deadline: Sept. 18
   - proposed deadline: Sept. 21
   - exact source evidence
   - review rationale
6. Select **Accept change**.
7. Open Programming Assignment 2 again:
   - due date is now Sept. 21
   - event status is `updated`
   - Sept. 18 appears in deadline history
   - approval has reset
8. Select **Approve for export**.
9. Select **Export approved calendar** to download `duescope-calendar.ics`.

To demonstrate rejection, scan a conflicting Sept. 22 source update and select **Keep saved date**. The Sept. 21 canonical deadline remains unchanged.

### Google Calendar test-sync demo

1. Start the backend and open `http://127.0.0.1:8001/api/google/auth/start` in a browser.
2. Sign in with Google and approve the requested permissions.
3. Confirm the callback page says **Google connected successfully**.
4. Verify the connection:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8001/api/google/auth/status
   ```

5. Call the test-sync route:

   ```powershell
   Invoke-RestMethod `
     -Method Post `
     -Uri "http://127.0.0.1:8001/api/google/calendar/sync-approved"
   ```

6. Open Google Calendar and verify that a `DueScope test sync` event appears in the connected account's primary calendar.

Delete the test event after the demonstration if desired.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Confirm the API is running |
| `GET` | `/api/demo/workspace` | Get courses, events, changes, workload, and proposals |
| `GET` | `/api/events` | List canonical events |
| `GET` | `/api/events/{event_id}` | Get event details, evidence, and history |
| `PATCH` | `/api/events/{event_id}/approval` | Approve or unapprove an exportable event |
| `POST` | `/api/events/reconcile` | Reconcile one supplied event candidate |
| `GET` | `/api/events/proposals/pending` | List unresolved deadline proposals |
| `POST` | `/api/events/proposals/{proposal_id}/accept` | Accept a proposal and update the canonical event |
| `POST` | `/api/events/proposals/{proposal_id}/reject` | Reject a proposal and preserve the canonical event |
| `POST` | `/api/sources/extract` | Extract deadline candidates from pasted text |
| `POST` | `/api/sources/extract-and-reconcile` | Extract, validate, and reconcile pasted source text |
| `GET` | `/api/canvas/profile` | Get Canvas profile information |
| `GET` | `/api/canvas/courses` | Load Canvas courses |
| `GET` | `/api/canvas/courses/{course_id}/assignments` | List Canvas assignments |
| `POST` | `/api/canvas/import-course/{course_id}` | Import Canvas deadlines |
| `POST` | `/api/calendar/export` | Export approved events as ICS |
| `GET` | `/api/google/auth/start` | Start Google OAuth authorization |
| `GET` | `/api/google/auth/callback` | Receive the Google OAuth callback and save local credentials |
| `GET` | `/api/google/auth/status` | Check whether Google Calendar is connected |
| `POST` | `/api/google/calendar/sync-approved` | Create a Google Calendar test-sync event for the connected user |

## Useful API checks

### Backend health

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

### Current workspace

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/demo/workspace |
  ConvertTo-Json -Depth 20
```

### Pending proposals

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/events/proposals/pending |
  ConvertTo-Json -Depth 20
```

### Approve an event

```powershell
$approval = @{ approved = $true } | ConvertTo-Json

Invoke-RestMethod `
  -Method Patch `
  -Uri "http://127.0.0.1:8001/api/events/event-assignment-2/approval" `
  -ContentType "application/json" `
  -Body $approval |
  ConvertTo-Json -Depth 20
```

### Export approved events

```powershell
$exportBody = @{
  event_ids = @("event-assignment-2")
} | ConvertTo-Json

Invoke-WebRequest `
  -Method Post `
  -Uri "http://127.0.0.1:8001/api/calendar/export" `
  -ContentType "application/json" `
  -Body $exportBody `
  -OutFile "duescope-calendar.ics"

Get-Content .\duescope-calendar.ics
```

A successful export begins with:

```text
BEGIN:VCALENDAR
```

### Google Calendar connection status

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/google/auth/status
```

Before authorization, expected output:

```text
connected
---------
False
```

After authorization, expected output:

```text
connected
---------
True
```

### Google Calendar test sync

After connecting Google, create a test event:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8001/api/google/calendar/sync-approved"
```

A successful response contains `success: true`, an event ID, and a Google Calendar event URL. Confirm that a clearly labeled `DueScope test sync` event appears in the connected account's primary Google Calendar.

## Project structure

```text
DueScope/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── calendar.py
│   │   │   ├── canvas.py
│   │   │   ├── demo.py
│   │   │   ├── events.py
│   │   │   ├── google.py
│   │   │   └── sources.py
│   │   ├── schemas/
│   │   │   ├── events.py
│   │   │   └── extraction.py
│   │   ├── services/
│   │   │   ├── canvas.py
│   │   │   ├── deadline_validation.py
│   │   │   ├── gemini_extraction.py
│   │   │   ├── google_oauth.py
│   │   │   └── reconciliation.py
│   │   └── main.py
│   ├── credentials.json          # local only; Git-ignored
│   ├── token.json                # local only; Git-ignored
│   ├── tests/
│   │   ├── test_deadline_validation.py
│   │   └── test_reconciliation.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── globals.css
│   │       ├── layout.tsx
│   │       └── page.tsx
│   ├── package.json
│   └── next.config.ts
├── .env.example
├── .gitignore
├── BLUEPRINT.md
├── pytest.ini
└── README.md
```

## Development checks

Run backend tests:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v
```

Build the frontend:

```powershell
cd frontend
npm run build
cd ..
```

Check changed files:

```powershell
git diff --check
git status
```

## Repository rules

- Do not commit `.env`, API keys, Canvas tokens, Google OAuth credentials, OAuth token files, local databases, virtual environments, or generated ICS files.
- Do not commit `frontend\node_modules` or `frontend\.next`.
- Save source and documentation files as UTF-8.
- Run backend tests and the frontend production build before merging.
- Use focused branches and review changes before merging to `main`.

## Current limitations

- All DueScope workspace data is in memory and resets when the backend restarts.
- Canvas import requires valid Canvas API configuration.
- Ollama must be installed and running for local AI scanning.
- Gemini is optional and requires a funded project with usable API credits.
- Google OAuth and a Google Calendar test-sync endpoint are implemented locally.
- The current Google Calendar route creates a test event; syncing selected approved DueScope deadlines with deduplication and update behavior is future work.
- Gmail ingestion, persistent storage, scheduled sync, workload forecasting, deployment, and a custom domain are future work.

## Team

- Khoi Anh Le Nguyen - [@ngkhoi111](https://github.com/ngkhoi111)
- Dong Quan Tran - [@dong-quan-tran](https://github.com/dong-quan-tran)

## HackRice 16

DueScope is built for the HackRice 16 Work & Productivity track.

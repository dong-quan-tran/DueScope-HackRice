# DueScope

DueScope is an evidence-backed deadline and opportunity manager built for HackRice 16's Work & Productivity track.

Students juggle academic deadlines across Canvas, announcements, instructor emails, syllabi, and class messages. They also manage job-application updates, online assessments, and interview scheduling in Gmail. DueScope turns these fragmented sources into one reviewable workflow: it imports and extracts deadlines, validates evidence and timezones, detects conflicts, preserves history, and requires explicit user approval before creating Google Calendar events.

## Core idea

A source or AI model can suggest a deadline or reminder, but it must never silently overwrite a student's saved schedule or write to Google Calendar without approval.

DueScope uses a review-first workflow:

```text
Canvas import, pasted course update, or Gmail job message
                         |
                         v
Structured extraction and normalization
                         |
                         v
Candidate validation
- title is present
- date is ISO-8601 and timezone-aware
- source evidence is retained
                         |
                         v
Reconciliation with saved events or job records
                         |
                         +-- New academic event: create canonical event
                         |
                         +-- Same academic deadline: leave event unchanged
                         |
                         +-- Different academic deadline: create a proposal
                         |                                  |
                         |                                  v
                         |                    User accepts or rejects change
                         |
                         +-- Explicit job deadline: create pending calendar proposal
                                                            |
                                                            v
                                             User approves or dismisses proposal
                                                            |
                                                            v
                                  Export approved ICS events or create/update
                                       one Google Calendar event after approval
```

When a user accepts an academic deadline-change proposal, DueScope preserves the old deadline in history, applies the new evidence and date, marks the event as `updated`, and resets calendar approval. A rejected proposal leaves the saved event unchanged.

For job messages, Gmail is read-only: DueScope can create a pending reminder proposal from an explicit assessment deadline, interview scheduling deadline, or confirmed interview time, but only the user can approve a Google Calendar write.

## Current status

DueScope is a working full-stack MVP with:

- Next.js and TypeScript dashboard
- FastAPI backend and REST API
- Canvas course lookup and Canvas assignment import
- Academic deadline display windows: next 7, 14, or 30 days, or all semester
- Local Ollama AI extraction using `gemma3:4b`
- Optional Gemini extraction when configured
- Candidate validation for title, evidence, and timezone-aware dates
- Reviewable academic deadline-change proposals
- Preserved event history after accepted changes
- Approval-gated ICS calendar export
- Google OAuth connection flow with PKCE
- Google Calendar sync for user-approved academic deadlines
- Gmail job-application tracking from read-only Gmail searches
- Job status inference and user review/edit controls
- Pending job calendar proposals for online assessments and interview scheduling
- Explicit job-reminder approval/dismissal controls
- Google Calendar creation/update behavior for approved job reminders
- High-workload alert display
- Automated validation and reconciliation tests

The application currently uses in-memory demo storage. Restarting the backend resets seeded events, imported Canvas records, academic proposals, job applications, job reminder proposals, approvals, and accepted changes. Google OAuth tokens are stored locally for development in `backend/token.json` and remain available across backend restarts unless removed.

## Features

### Dashboard

The DueScope dashboard includes:

- Upcoming deadlines sorted by due date
- Display filters for next 7 days, next 14 days, next 30 days, or all semester
- Course color indicators
- Status badges for `verified`, `updated`, `needs_review`, and `canceled`
- Evidence panel for selected academic events
- Deadline history timeline
- Pending academic deadline-proposal review cards
- Accept change and Keep saved date controls
- Approval controls for exportable academic events
- Google Calendar connection and approved-deadline sync controls
- Canvas import controls
- Course-update scanning form
- ICS calendar export
- Job application cards with status, next action, source email, and review/edit controls
- Pending job-reminder cards with evidence, Gmail source links, and approval/dismissal controls

### Canvas import

DueScope can:

1. Load active Canvas courses.
2. Let the user select a course.
3. Import upcoming Canvas assignments with due dates.
4. Skip past assignments by default.
5. Add a Canvas course to the workspace when it is first imported.
6. Create canonical events for newly discovered work.
7. Create a proposal instead of silently overwriting a conflicting saved deadline.
8. Display imported work alongside other deadlines and filter the timeline by a selected display horizon.

Canvas assignments are stored with source IDs such as:

```text
canvas-assignment-2344093
```

and imported course IDs such as:

```text
canvas-282164
```

Canvas access requires valid local Canvas configuration.

### Academic AI extraction

DueScope uses structured AI output to extract academic obligations from pasted:

- Canvas announcements
- Instructor emails
- Syllabus excerpts
- Other course notices

The default local provider is Ollama with `gemma3:4b`. Gemini can be used when configured with an API key tied to a project with usable Gemini access.

Example source text:

```text
Programming Assignment 2 has been extended.
It is now due Monday, September 21, 2026 at 11:59 PM in Canvas.
```

Expected outcome:

```text
Existing saved event: Programming Assignment 2, due Sept. 18
Extracted candidate: Programming Assignment 2, due Sept. 21
Result: proposal requiring user review
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

Candidates with missing or unreliable information are marked for review. They are never automatically approved for calendar export or Google Calendar sync.

### Academic proposal review

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
- Clears prior calendar approval

Rejecting a proposal:

- Keeps the canonical event unchanged
- Resolves the proposal as `rejected`

### Gmail job tracking

DueScope can scan Gmail job-related messages in read-only mode and track an application through statuses such as:

```text
application_received
online_assessment
recruiter_screen
phone_screen
technical_interview
onsite_interview
final_interview
offer
rejected
unknown
```

Each tracked job record includes:

- Inferred company and role
- Current application status
- A suggested next action
- Source subject and sender
- Source message and thread identifiers
- Source excerpt
- A Gmail search link to open the source message
- Status history
- A review/edit action for correcting inferred information

Gmail scanning does not send, modify, archive, label, or delete messages.

### Job reminder proposals

When a job email has an explicit date and time, DueScope can create a pending calendar proposal for:

- Online assessment deadlines
- Interview scheduling deadlines
- Confirmed interviews

For example, this email text:

```text
Please choose a time for the interview by September 22, 2026 at 5:00 PM CT.
```

creates a proposal such as:

```text
Kind: interview_scheduling_deadline
Title: Choose interview time — Johnny Tran
Start: September 22, 2026, 4:30 PM CT
End: September 22, 2026, 5:00 PM CT
Status: pending
```

DueScope intentionally treats this as a deadline to choose an interview time, not as a confirmed interview appointment.

The user can:

- Open the Gmail source message
- Review the exact evidence excerpt
- Approve and add the reminder to Google Calendar
- Dismiss the proposal without changing Google Calendar

Approved job reminders retain the Google Calendar event ID and URL. Re-approving a previously approved reminder updates the existing Calendar event rather than creating a duplicate.

### Calendar export and Google sync

Academic events must be both:

- Approved by the user, and
- Marked `verified` or `updated`

before they can be exported or synced.

DueScope generates a standard `.ics` file that can be imported into compatible calendar applications.

DueScope can also connect to a user's Google account through OAuth and sync approved academic deadlines to the user's primary Google Calendar. For job reminders, DueScope creates or updates the Google Calendar event only after the user approves the specific pending proposal.

Google authorization uses PKCE and stores the local OAuth token in `backend/token.json` for development.

## Tech stack

| Area | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Icons | Lucide React |
| Backend | Python, FastAPI, Pydantic |
| Testing | pytest |
| Calendar export | icalendar |
| Google integration | Google OAuth 2.0 with PKCE, Google Calendar API |
| Gmail ingestion | Gmail API, read-only search and message parsing |
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

If Google dependencies are not already included in `backend/requirements.txt`, install them with:

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

Optional Gmail configuration depends on the Gmail OAuth/client setup implemented in the backend. Keep Gmail credentials and token files local and Git-ignored.

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

Keep Ollama running while using the academic AI scanner.

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

For the most reliable demo, start from a freshly restarted backend so the seeded workspace is restored. Because the current workspace is in memory, do not edit or restart backend files after importing Canvas data or seeding job data.

### Academic workflow

1. Open `http://localhost:3000`.
2. In **Import from Canvas**, select **Load Canvas courses**.
3. Select a course, such as Data Mining.
4. Select **Import deadlines**.
5. In **Upcoming deadlines**, select **All semester** to view later imported deadlines.
6. Select an imported Canvas event and show its evidence panel.
7. In **Scan a course update**, paste:

   ```text
   Programming Assignment 2 has been extended.
   It is now due Monday, September 21, 2026 at 11:59 PM in Canvas.
   ```

8. Select **Scan for deadlines**.
9. Show the **Deadline proposals** card:

   - Saved deadline: Sept. 18
   - Proposed deadline: Sept. 21
   - Exact source evidence
   - Review rationale

10. Select **Accept change**.
11. Open Programming Assignment 2 again and show:

   - The updated Sept. 21 deadline
   - `updated` status
   - Sept. 18 in deadline history
   - Reset approval state

12. Approve the trusted event and either export an ICS file or sync it to Google Calendar.

To demonstrate rejection, scan a conflicting Sept. 22 source update and select **Keep saved date**. The Sept. 21 canonical deadline remains unchanged.

### Job workflow

1. Start with Google Calendar connected if you plan to approve a job reminder.
2. In **Job applications**, select **Scan for new job updates**. Gmail scanning is read-only.
3. For a reliable local test, use a focused scan query in PowerShell for the test phone-screen message:

   ```powershell
   $jobScanBody = @{
     max_results = 5
     query = 'in:inbox subject:"DueScope test - phone screen scheduling"'
   } | ConvertTo-Json

   Invoke-RestMethod `
     -Method Post `
     -Uri "http://127.0.0.1:8001/api/jobs/scan" `
     -ContentType "application/json" `
     -Body $jobScanBody |
     ConvertTo-Json -Depth 20
   ```

4. Confirm the created job has status `phone_screen`.
5. In **Job reminders to review**, inspect the pending proposal:

   ```text
   Choose interview time — Johnny Tran
   Kind: interview_scheduling_deadline
   Evidence: September 22, 2026 at 5:00 PM CT
   ```

6. Use **Open source email** to verify the originating Gmail message if appropriate for the demo.
7. Select **Approve and add to Google Calendar**.
8. Confirm the proposal moves to approved and use **Open in Calendar** to view the created or updated event.

To test safe dismissal, select **Dismiss** on a pending proposal. The proposal is resolved without changing Google Calendar.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Confirm the API is running |
| `GET` | `/api/demo/workspace` | Get courses, events, changes, workload, and proposals |
| `GET` | `/api/events` | List canonical academic events |
| `GET` | `/api/events/{event_id}` | Get academic event details, evidence, and history |
| `PATCH` | `/api/events/{event_id}/approval` | Approve or unapprove an exportable academic event |
| `POST` | `/api/events/reconcile` | Reconcile one supplied academic event candidate |
| `GET` | `/api/events/proposals/pending` | List unresolved academic deadline proposals |
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
| `GET` | `/api/google/auth/callback` | Receive the Google OAuth callback and save local credentials |
| `GET` | `/api/google/auth/status` | Check whether Google Calendar is connected |
| `POST` | `/api/google/calendar/sync-approved` | Sync approved academic deadlines to Google Calendar |
| `GET` | `/api/jobs` | List tracked job applications |
| `POST` | `/api/jobs/scan` | Read-only Gmail scan for job application updates |
| `PATCH` | `/api/jobs/{job_id}` | Review and update a tracked job application |
| `GET` | `/api/jobs/proposals` | List job calendar proposals |
| `POST` | `/api/jobs/proposals/{proposal_id}/approve` | Approve a job reminder and create/update Google Calendar |
| `POST` | `/api/jobs/proposals/{proposal_id}/dismiss` | Dismiss a job reminder without changing Google Calendar |

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

### Verify Canvas import persistence

After importing a Canvas course, inspect the shared workspace:

```powershell
$workspace = Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8001/api/demo/workspace"

$workspace.events |
  Select-Object id, course_id, title, due_at, status, source_id |
  Format-Table -AutoSize
```

Imported Canvas events have IDs similar to `event-...`, course IDs such as `canvas-282164`, and source IDs such as `canvas-assignment-2344093`.

### Pending academic proposals

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/events/proposals/pending |
  ConvertTo-Json -Depth 20
```

### Approve an academic event

```powershell
$approval = @{ approved = $true } | ConvertTo-Json

Invoke-RestMethod `
  -Method Patch `
  -Uri "http://127.0.0.1:8001/api/events/event-assignment-2/approval" `
  -ContentType "application/json" `
  -Body $approval |
  ConvertTo-Json -Depth 20
```

### Export approved academic events

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

### Job applications

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/jobs |
  ConvertTo-Json -Depth 20
```

### Job reminder proposals

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/jobs/proposals |
  ConvertTo-Json -Depth 20
```

### Focused job-email scan

```powershell
$jobScanBody = @{
  max_results = 5
  query = 'in:inbox subject:"DueScope test - phone screen scheduling"'
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8001/api/jobs/scan" `
  -ContentType "application/json" `
  -Body $jobScanBody |
  ConvertTo-Json -Depth 20
```

### Approve a job reminder

Replace the proposal ID with a pending proposal returned by `/api/jobs/proposals`:

```powershell
$proposalId = "job-calendar-proposal-REPLACE_ME"

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8001/api/jobs/proposals/$proposalId/approve" |
  ConvertTo-Json -Depth 20
```

A successful response includes the updated proposal, a Calendar action of `created` or `updated`, and a Google Calendar URL.

### Dismiss a job reminder

```powershell
$proposalId = "job-calendar-proposal-REPLACE_ME"

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8001/api/jobs/proposals/$proposalId/dismiss" |
  ConvertTo-Json -Depth 20
```

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
│   │   │   ├── jobs.py
│   │   │   └── sources.py
│   │   ├── schemas/
│   │   │   ├── events.py
│   │   │   ├── extraction.py
│   │   │   └── jobs.py
│   │   ├── services/
│   │   │   ├── canvas.py
│   │   │   ├── deadline_validation.py
│   │   │   ├── gemini_extraction.py
│   │   │   ├── gmail.py
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

Names and exact files may vary slightly by branch; use the API documentation at `/docs` as the authoritative route list for your local build.

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

- Do not commit `.env`, API keys, Canvas tokens, Gmail credentials, Google OAuth credentials, OAuth token files, local databases, virtual environments, or generated ICS files.
- Do not commit `frontend\node_modules` or `frontend\.next`.
- Save source and documentation files as UTF-8.
- Run backend tests and the frontend production build before merging.
- Use focused branches and review changes before merging to `main`.

## Current limitations

- All DueScope workspace data is in memory and resets when the backend restarts.
- Canvas import requires valid Canvas API configuration.
- Canvas import currently imports all future assignments returned by Canvas; the dashboard's 7/14/30-day and all-semester options control the displayed deadline horizon.
- Ollama must be installed and running for local AI scanning.
- Gemini is optional and requires usable API access.
- Gmail scanning depends on configured local Gmail authorization and matching job-message queries.
- Job-status inference and reminder detection are heuristic and are designed to be reviewed by the user.
- Google Calendar requires local OAuth configuration.
- Persistent storage, scheduled background sync, notifications, richer workload forecasting, additional student platforms, deployment, and a custom domain are future work.

## Team

- Khoi Anh Le Nguyen - [@ngkhoi111](https://github.com/ngkhoi111)
- Dong Quan Tran - [@dong-quan-tran](https://github.com/dong-quan-tran)

## HackRice 16

DueScope is built for the HackRice 16 Work & Productivity track.
Will keep working on it.

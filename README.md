# DueScope

DueScope is an evidence-backed academic deadline manager built for HackRice 16's Work & Productivity track.

It turns course information from Canvas, instructor announcements, emails, syllabi, and pasted course updates into a single reviewable deadline workflow. DueScope preserves the source evidence behind every deadline, detects extensions and reschedules, highlights heavy workload days, and exports approved events to an ICS calendar file.

## What it does

Students often receive deadlines through multiple places: Canvas assignments, announcement posts, instructor emails, syllabus PDFs, and class messages. When dates change, it is easy to miss the update or lose track of which source is authoritative.

DueScope helps by:

- Importing official upcoming deadlines from Canvas
- Scanning pasted course updates for deadline information
- Reconciling new information against canonical events
- Recording deadline history when a date changes
- Flagging uncertain or conflicting information for review
- Showing source evidence for every event
- Requiring approval before a deadline is exported
- Exporting approved events as an ICS calendar file

```text
Canvas courses and course updates
            |
            v
Source-backed deadline extraction
            |
            v
Reconciliation and date-history preservation
            |
            v
Review, approval, and workload awareness
            |
            v
ICS calendar export
```

## Current status

DueScope currently includes a working full-stack MVP:

- FastAPI backend with seeded workspace data and REST endpoints
- Next.js and TypeScript frontend dashboard
- Canvas course lookup and deadline import UI
- Pasted course-update scanning workflow
- Canonical academic events with source evidence and history
- Deadline reconciliation for extensions, reschedules, and new events
- Review and approval workflow for calendar export
- Workload warning display for high-volume days
- ICS calendar export for approved deadlines
- Automated backend reconciliation tests

The application currently uses in-memory demo storage. Restarting the backend resets seeded data, imported events, approvals, and reconciliation changes.

## Features

### Dashboard

The frontend dashboard includes:

- Upcoming deadline list sorted by due date
- Status badges for verified, updated, needs-review, and canceled events
- Course color indicators
- Changes-to-review inbox
- Event evidence panel
- Deadline history timeline
- Approval controls for exportable events
- High-workload alert
- Canvas import controls
- Course-update scanning form
- ICS calendar export button

### Canvas import

DueScope can:

1. Load available Canvas courses.
2. Let the user choose a course.
3. Import its upcoming assignment deadlines.
4. Skip past deadlines.
5. Refresh the workspace after import.

Canvas API access requires the corresponding backend environment configuration.

### Source scanning and reconciliation

The course-update scanner accepts pasted text from sources such as:

- Canvas announcements
- Instructor emails
- Syllabus excerpts
- Other course notices

The backend extracts deadline candidates, compares them with existing academic events, and then either:

- Creates a new event
- Updates an existing deadline
- Preserves the prior deadline in event history
- Marks uncertain information as `needs_review`
- Records the relevant source evidence

Example input:

```text
Programming Assignment 2 has been extended.
It is now due Monday, September 21, 2026 at 11:59 PM in Canvas.
```

### Calendar export

Only events that are both approved and marked `verified` or `updated` can be exported.

DueScope generates a standard `.ics` file that can be imported into calendar applications that support iCalendar files.

## Tech stack

| Area | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| UI icons | Lucide React |
| Backend | Python, FastAPI, Pydantic |
| Testing | pytest |
| Calendar export | icalendar |
| Deadline extraction | Gemini-backed workflow when configured |
| Canvas ingestion | Canvas REST API |
| Development environment | Windows PowerShell, VS Code recommended |

## Prerequisites

Install the following before running the project:

- Git
- Python 3.11 or newer
- Node.js 20 or newer
- npm
- VS Code recommended

Check installed versions:

```powershell
python --version
node --version
npm --version
git --version
```

If Python is unavailable, install it from [python.org](https://www.python.org/downloads/). If Node.js is unavailable, install a current LTS release from [nodejs.org](https://nodejs.org/).

## Quick start

### 1. Clone the repository

```powershell
git clone [https://github.com/OWNER/DueScope.git](https://github.com/OWNER/DueScope.git)
cd DueScope
```

Replace `OWNER` with the GitHub account or organization that owns the repository.

If you already cloned the project:

```powershell
git pull origin main
```

### 2. Create the backend virtual environment

From the repository root:

```powershell
python -m venv backend\.venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\backend\.venv\Scripts\Activate.ps1
```

Your PowerShell prompt should begin with:

```text
(.venv)
```

### 3. Install backend dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

Optional dependency check:

```powershell
python -c "import fastapi, uvicorn, pydantic, dateutil, icalendar, pytest; print('Backend dependencies ready')"
```

Expected output:

```text
Backend dependencies ready
```

### 4. Install frontend dependencies

Open a second PowerShell terminal at the repository root:

```powershell
cd frontend
npm install
cd ..
```

Do not commit `frontend\node_modules`.

### 5. Configure environment variables

Create a local environment file if the repository provides an example:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`.

Depending on enabled integrations, your local configuration may include values such as:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
CANVAS_BASE_URL=
CANVAS_ACCESS_TOKEN=
GEMINI_API_KEY=
```

Leave integration values blank if you want to use only the seeded demo workspace and do not have credentials configured.

### 6. Run backend tests

From the repository root with the backend environment activated:

```powershell
python -m pytest -v
```

### 7. Start the backend API

DueScope uses port `8001` in local development.

```powershell
uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8001
```

Keep this terminal running.

API documentation is available at:

```text
http://127.0.0.1:8001/docs
```

### 8. Start the frontend

In another terminal:

```powershell
cd frontend
npm run dev
```

Open the local application:

```text
http://localhost:3000
```

The frontend expects the backend at:

```text
http://127.0.0.1:8001
```

To use a different backend URL, set `NEXT_PUBLIC_API_URL` in the frontend environment configuration and restart the frontend development server.

## Using the app

### Import Canvas deadlines

1. Start both the backend and frontend.
2. Open `http://localhost:3000`.
3. In **Import from Canvas**, select **Load Canvas courses**.
4. Select a returned Canvas course.
5. Choose **Import deadlines**.
6. Review the imported events in **Upcoming deadlines**.

If Canvas credentials are unavailable or invalid, the UI shows the backend error message instead of importing data.

### Scan a course update

1. In **Scan a course update**, select the relevant DueScope course.
2. Choose the source type.
3. Enter a source title.
4. Paste an announcement, email, or syllabus text.
5. Select **Scan for deadlines**.
6. Review the resulting notice and the affected event in the evidence panel.

### Review a deadline

1. Select an event from **Upcoming deadlines** or **Changes to review**.
2. Read the source evidence.
3. Compare current and previous due dates in **Deadline history**.
4. Review any `needs_review` reason.
5. Approve trusted verified or updated events for export.

### Export a calendar file

1. Select an event.
2. Choose **Approve for export** for events with `verified` or `updated` status.
3. Select **Export approved calendar** in the page header.
4. Import the downloaded `duescope-calendar.ics` file into a compatible calendar application.

The generated ICS file is local output and should remain untracked by Git.

## API quick reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Confirm that the API is running |
| `GET` | `/api/demo/workspace` | Get courses, events, changes, and workload data |
| `GET` | `/api/events` | List canonical deadline events |
| `GET` | `/api/events/{event_id}` | Get one event with evidence and history |
| `PATCH` | `/api/events/{event_id}/approval` | Approve or unapprove an exportable event |
| `POST` | `/api/events/reconcile` | Create, update, or flag a deadline candidate |
| `POST` | `/api/sources/extract-and-reconcile` | Scan pasted source text and reconcile results |
| `GET` | `/api/canvas/courses` | Load available Canvas courses |
| `POST` | `/api/canvas/import-course/{course_id}` | Import upcoming deadlines from one Canvas course |
| `POST` | `/api/calendar/export` | Download approved events as an ICS calendar |

## API examples

### Confirm backend health

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

### View the workspace

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/demo/workspace |
  ConvertTo-Json -Depth 10
```

### List events

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/events |
  ConvertTo-Json -Depth 10
```

### Approve an event

```powershell
$approval = @{ approved = $true } | ConvertTo-Json

Invoke-RestMethod `
  -Method Patch `
  -Uri "http://127.0.0.1:8001/api/events/event-quiz-2/approval" `
  -ContentType "application/json" `
  -Body $approval |
  ConvertTo-Json -Depth 10
```

### Export approved events

```powershell
$exportBody = @{
  event_ids = @(
    "event-quiz-2",
    "event-calculus-exam"
  )
} | ConvertTo-Json

Invoke-WebRequest `
  -Method Post `
  -Uri "http://127.0.0.1:8001/api/calendar/export" `
  -ContentType "application/json" `
  -Body $exportBody `
  -OutFile "duescope-calendar.ics"

Get-Content .\duescope-calendar.ics
```

A successful ICS export begins with:

```text
BEGIN:VCALENDAR
```

### Test reconciliation

This example simulates a new announcement moving Quiz 2 to Friday, September 18, 2026:

```powershell
$body = @{
  candidate = @{
    course_id = "cse-3310"
    type = "quiz"
    title = "Quiz 2"
    starts_at = "2026-09-18T08:00:00-05:00"
    due_at = "2026-09-18T23:59:00-05:00"
    source_id = "source-algorithms-announcement"
    source_excerpt = "Quiz 2 has been moved again to Friday, September 18 at 11:59 PM."
    change_type = "rescheduled"
    confidence = "high"
    needs_review_reason = $null
  }
  source_type = "instructor_announcement"
  source_received_at = "2026-09-12T10:30:00-05:00"
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8001/api/events/reconcile" `
  -ContentType "application/json" `
  -Body $body |
  ConvertTo-Json -Depth 10
```

Then inspect the event and its preserved history:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/events/event-quiz-2 |
  ConvertTo-Json -Depth 10
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
│   │   │   └── sources.py
│   │   ├── schemas/
│   │   │   └── events.py
│   │   ├── services/
│   │   │   ├── extraction.py
│   │   │   └── reconciliation.py
│   │   └── main.py
│   ├── tests/
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
├── docs/
├── fixtures/
├── .env.example
├── .gitignore
├── BLUEPRINT.md
├── pytest.ini
└── README.md
```

Some filenames may vary as the project evolves. Use the repository tree as the source of truth.

## Development workflow

### Start a feature branch

```powershell
git switch main
git pull origin main
git switch -c feat/your-feature-name
```

### Validate changes

Backend:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v
```

Frontend:

```powershell
cd frontend
npm run build
cd ..
```

Check your Git diff:

```powershell
git diff --check
git status
```

### Commit and push

```powershell
git add <files>
git commit -m "feat: concise description"
git push -u origin feat/your-feature-name
```

Open a pull request into `main` after pushing your branch.

## Repository rules

- Do not commit directly to `main`.
- Use one focused branch per feature or fix.
- Pull the latest `main` before beginning new work.
- Do not commit `.env`, API keys, tokens, local databases, virtual environments, or generated calendar files.
- Do not commit `frontend\node_modules` or `frontend\.next`.
- Keep pull requests focused and reviewable.
- Run backend tests and the frontend production build before merging.
- Use UTF-8 encoding when saving text files.

## Current limitations

- The backend uses in-memory storage, so application state resets when the API restarts.
- Canvas functionality depends on valid local Canvas API configuration.
- Gemini-backed extraction depends on valid local API configuration and is not guaranteed to be available in every development environment.
- The application exports ICS files but does not directly synchronize with Google Calendar.
- Gmail ingestion, persistent PostgreSQL or Tiger Data storage, ElevenLabs briefing generation, deployment, and custom-domain configuration remain future work.
- The current interface is an MVP dashboard rather than a full week or month calendar planner.

## Roadmap

- Persistent database storage
- Direct Google Calendar synchronization
- Gmail ingestion
- Improved Canvas synchronization and scheduled refreshes
- Better conflict resolution and confidence explanations
- Weekly and monthly calendar views
- Workload forecasting and study-time recommendations
- Daily spoken deadline briefings
- Production deployment and custom domain

## Team

- Khoi Anh Le Nguyen - [@ngkhoi111](https://github.com/ngkhoi111)
- Gail Le - [@dong-quan-tran](https://github.com/dong-quan-tran)

## HackRice 16

DueScope is built for the HackRice 16 Work & Productivity track.
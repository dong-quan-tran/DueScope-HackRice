@'
# DueScope

DueScope is an evidence-backed academic deadline manager built for HackRice 16.

It turns course information from syllabi, Canvas-style announcements, and instructor emails into a unified deadline workflow. DueScope preserves source evidence, detects reschedules and conflicting dates, flags high-workload days, and exports approved deadlines as a calendar file.

## Current status

The current version is a working backend MVP with seeded demo data.

```text
Seeded academic sources
→ canonical deadline events
→ deadline update/reconciliation
→ user approval
→ ICS calendar export
```

The current build does not yet connect to live Canvas, Gmail, Google Calendar, Tiger Data, or Gemini. Those integrations come after the core frontend and deterministic backend workflow are stable.

## Features implemented

- Seeded workspace with Algorithms, Calculus III, and Analytical Chemistry
- Assignments, quizzes, exams, labs, and review events
- Source-backed event evidence
- Deadline history for reschedules and extensions
- Event reconciliation API
- Approval workflow for verified and updated events
- ICS calendar export for approved events
- Automated reconciliation tests

## Planned features

- Gemini extraction from pasted syllabus, Canvas announcement, and email text
- Frontend dashboard with weekly calendar, changes inbox, evidence drawer, and workload view
- Canvas API ingestion
- Gmail API ingestion
- Google Calendar synchronization
- Tiger Data/PostgreSQL persistence
- ElevenLabs daily academic briefing
- Vultr deployment and GoDaddy domain

## Tech stack

- Backend: Python, FastAPI, Pydantic
- Testing: pytest
- Calendar export: icalendar
- Planned frontend: Next.js, TypeScript, Tailwind CSS
- Planned AI extraction: Google Gemini
- Planned storage: PostgreSQL / Tiger Data

## Prerequisites

Install the following before running the project:

- Git
- Python 3.11 or newer
- VS Code recommended

Check Python:

```powershell
python --version
```

If `python` is not recognized, install Python from [python.org](https://www.python.org/downloads/) and reopen VS Code.

## Quick start

### 1. Clone the repository

```powershell
git clone [https://github.com/OWNER/DueScope.git](https://github.com/OWNER/DueScope.git)
cd DueScope
```

Replace `OWNER` with the GitHub repository owner.

If you are already inside the cloned repository:

```powershell
git pull origin main
```

### 2. Create and activate the Python virtual environment

From the repository root:

```powershell
python -m venv backend\.venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\backend\.venv\Scripts\Activate.ps1
```

Your prompt should begin with:

```text
(.venv)
```

### 3. Install backend dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

Verify the installation:

```powershell
python -c "import fastapi, uvicorn, pydantic, dateutil, icalendar, pytest; print('Backend dependencies ready')"
```

Expected:

```text
Backend dependencies ready
```

### 4. Run tests

```powershell
python -m pytest -v
```

Expected:

```text
3 passed
```

### 5. Start the API

Port `8000` may be reserved on some Windows systems, so DueScope uses port `8001`.

```powershell
uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8001
```

Leave this terminal running.

The API documentation is available at:

```text
http://127.0.0.1:8001/docs
```

## Run the demo

Open a second VS Code PowerShell terminal from the DueScope repository root.

Activate the environment:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\backend\.venv\Scripts\Activate.ps1
```

### Check API health

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

Expected:

```text
status service
------ -------
ok     duescope-api
```

### View the complete demo workspace

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/demo/workspace | ConvertTo-Json -Depth 10
```

### View all deadline events

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/events | ConvertTo-Json -Depth 10
```

The seeded workspace contains:

- Algorithms Quiz 2, originally due Sept. 15 and updated to Sept. 17
- Algorithms Programming Assignment 2, due Sept. 18
- Algorithms Midterm Exam
- Calculus Exam 1 review session
- Calculus Exam 1
- Analytical Chemistry GC-MS lab report, extended to Sept. 21
- Analytical Chemistry pre-lab worksheet marked `needs_review`

## Approve and export events

Only events with status `verified` or `updated` can be approved and exported.

### Approve events

```powershell
$approval = @{ approved = $true } | ConvertTo-Json

Invoke-RestMethod `
  -Method Patch `
  -Uri "http://127.0.0.1:8001/api/events/event-quiz-2/approval" `
  -ContentType "application/json" `
  -Body $approval | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Patch `
  -Uri "http://127.0.0.1:8001/api/events/event-calculus-exam/approval" `
  -ContentType "application/json" `
  -Body $approval | ConvertTo-Json -Depth 10
```

### Export an ICS calendar

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

Expected output begins with:

```text
BEGIN:VCALENDAR
```

The generated `duescope-calendar.ics` file is ignored by Git. Import it into a compatible calendar app to add the approved events.

## Test deadline reconciliation

This command simulates a new instructor announcement moving Quiz 2 to Friday, Sept. 18. It should preserve the earlier dates in the event history.

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
  -Body $body | ConvertTo-Json -Depth 10
```

Then inspect the updated event:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/events/event-quiz-2 | ConvertTo-Json -Depth 10
```

Restarting the backend resets all in-memory changes and approvals to the seeded demo state.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Confirm the API is running |
| `GET` | `/api/demo/workspace` | Get all seeded courses, sources, events, changes, and workload data |
| `GET` | `/api/events` | List canonical deadline events |
| `GET` | `/api/events/{event_id}` | Get one event with history and evidence |
| `PATCH` | `/api/events/{event_id}/approval` | Approve or unapprove an exportable event |
| `POST` | `/api/events/reconcile` | Create, update, or flag a deadline candidate |
| `POST` | `/api/calendar/export` | Download selected approved events as an ICS calendar |

## Team workflow

### Start a task

```powershell
git switch main
git pull origin main
git switch -c feat/your-feature-name
```

### Save and push work

```powershell
git status
git add <files>
git commit -m "feat: concise description"
git push -u origin feat/your-feature-name
```

Open a pull request into `main` after pushing.

### Rules

- Do not commit directly to `main`.
- Use one branch per focused feature.
- Pull the latest `main` before starting a new task.
- Do not commit `.env`, API keys, virtual environments, generated ICS files, or local databases.
- Keep pull requests small and test the backend before merging.

## Project structure

```text
DueScope/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── calendar.py
│   │   │   ├── demo.py
│   │   │   └── events.py
│   │   ├── schemas/
│   │   │   └── events.py
│   │   ├── services/
│   │   │   └── reconciliation.py
│   │   └── main.py
│   ├── tests/
│   │   └── test_reconciliation.py
│   └── requirements.txt
├── docs/
├── fixtures/
├── BLUEPRINT.md
├── pytest.ini
└── README.md
```

## Current limitations

- Data is stored in memory and resets when the API restarts.
- Demo sources and events are seeded; live Canvas/email ingestion is not connected yet.
- The calendar output is ICS export only; direct Google Calendar sync is not implemented yet.
- No frontend dashboard is connected yet.
- Gemini extraction has not been added yet.

## Team

- Khoi Anh Le Nguyen — [@ngkhoi111](https://github.com/ngkhoi111)
- Gail Le — [@dong-quan-tran](https://github.com/dong-quan-tran)

## HackRice 16

DueScope is built for the Work & Productivity track.
'@ | Set-Content -Encoding utf8 README.md
# DueScope

DueScope is an evidence-backed academic deadline manager built for HackRice 16.

It extracts assignments, quizzes, exams, and schedule changes from syllabi, Canvas announcements, and instructor emails; reconciles updated deadlines; flags high-workload days; and exports approved events to a calendar.

## Core features

- Import or paste academic sources: syllabus, Canvas-style announcement, or email
- Extract deadline candidates with source evidence
- Detect reschedules, extensions, and conflicting dates
- Preserve deadline history instead of silently overwriting dates
- Display a unified weekly calendar and workload collisions
- Export approved deadlines as an `.ics` calendar file

## Tech stack

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, Python, Pydantic
- AI extraction: Google Gemini
- Data: PostgreSQL / Tiger Data when available
- Optional briefing: ElevenLabs
- Deployment: Vultr and GoDaddy

## Local development

### Backend

```powershell
python -m venv backend\.venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8001
```

Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
Invoke-RestMethod http://127.0.0.1:8001/api/demo/workspace | ConvertTo-Json -Depth 10
```

## Team

- Khoi Anh Le Nguyen — [@ngkhoi111](https://github.com/ngkhoi111)
- Gail Le — [@dong-quan-tran](https://github.com/dong-quan-tran)

## HackRice 16

DueScope is built for the Work & Productivity track.

# DueScope

[Live demo](https://due-scope-hack-rice.vercel.app/demo) · Built for **HackRice 16 - Work & Productivity**

DueScope is an evidence-first deadline and opportunity manager for students. It turns fragmented academic and job-search information into a review-first workflow: identify potential deadlines, preserve original evidence, validate dates and time zones, detect conflicts, retain history, and require explicit user approval before an external calendar is changed.

> **Project status:** DueScope is an early beta. The public demo uses safe sample data. The repository includes working local/private-alpha integrations for Canvas, Gmail, and Google Calendar, but every person who runs a private instance must configure their own provider credentials and tokens. Do not share credentials, OAuth client secrets, or access tokens.

## What it does

### Academic deadlines

- Import official Canvas courses and assignments when Canvas access is configured.
- Paste course announcements, instructor emails, syllabus excerpts, or other notices.
- Extract, validate, and normalize deadline candidates while preserving source evidence.
- Detect conflicting deadline updates and create review proposals instead of silently changing saved events.
- Export approved events as `.ics` files.
- Create or update Google Calendar events only after explicit user approval and sync.

### Job applications

- Scan Gmail read-only for recruiting and application-update messages.
- Keep source metadata, evidence excerpts, and Gmail search links.
- Infer job status, next actions, and explicit assessment/interview dates for review.
- Create pending job-reminder proposals only from explicit dates.
- Create or update a Google Calendar reminder only after the user approves that specific proposal.

## Safety model

```text
Source data from Canvas, pasted text, or Gmail
                    |
                    v
Evidence retained + date/time normalized
                    |
                    v
DueScope creates an event, job record, or review proposal
                    |
                    v
User reviews, edits, accepts, rejects, approves, or dismisses
                    |
                    v
Only an explicit user action can export or update Google Calendar
```

- Canvas is read-only in DueScope.
- Gmail is read-only in DueScope.
- DueScope does not send, archive, label, delete, or otherwise modify Gmail messages.
- DueScope does not submit Canvas work, modify grades, edit courses, or post announcements.
- A changed academic deadline creates a review proposal; it does not silently overwrite the saved event.
- Google Calendar changes require an explicit user action.

## Public demo and self-hosting

The [public demo](https://due-scope-hack-rice.vercel.app/demo) demonstrates the review-first experience with safe sample data.

To use real Canvas, Gmail, or Google Calendar data, run your own local/private instance and configure your own credentials. This is necessary because Google and Canvas control third-party access through OAuth, API tokens, developer keys, and institution policies.

| Capability | Public demo | Local/private instance |
|---|---|---|
| Evidence-backed deadline workflow | Yes, sample data | Yes |
| Pasted course updates | Yes | Yes |
| Review conflict proposals | Yes | Yes |
| Canvas courses/assignments | Sample/configuration-dependent | Yes, with your Canvas configuration |
| Gmail job scan | Sample workflow only | Yes, with your Google OAuth app and authorized account |
| Google Calendar sync | Sample workflow only | Yes, after explicit approval and Google OAuth authorization |

## Quick start

### Prerequisites

Install:

- Git
- Python 3.11 or newer
- Node.js 20 or newer
- npm
- Ollama, if using local AI extraction

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

### 2. Create and activate a Python environment

Windows PowerShell:

```powershell
python -m venv backend\.venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\backend\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
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

### 4. Create local configuration

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Create `frontend\.env.local`:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001
NEXT_PUBLIC_DEMO_MODE=false
```

A local development configuration can start with:

```text
APP_ENV=development
API_PUBLIC_URL=http://127.0.0.1:8001
PUBLIC_APP_URL=http://localhost:3000
FRONTEND_ORIGINS=http://localhost:3000
DATABASE_URL=sqlite:///./duescope.db

APP_SESSION_SECRET=replace-with-a-long-random-secret
TOKEN_ENCRYPTION_KEY=replace-with-a-valid-encryption-key

EXTRACTION_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:4b
```

Generate secrets locally. For example:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Use a valid Fernet-compatible key for `TOKEN_ENCRYPTION_KEY` if the project is configured to use Fernet encryption:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Never commit `.env`, `.env.local`, credentials, access tokens, refresh tokens, secrets, or local databases.

### 5. Install the local extraction model

If using Ollama:

```powershell
ollama pull gemma3:4b
```

You can choose an extraction provider in `.env`:

```text
EXTRACTION_PROVIDER=ollama
EXTRACTION_PROVIDER=gemini
EXTRACTION_PROVIDER=auto
```

For Gemini, also add:

```text
GEMINI_API_KEY=your-key
```

### 6. Run DueScope locally

In one terminal, start Ollama if you use it:

```powershell
ollama serve
```

In a second terminal, start the backend from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8001
```

In a third terminal, start the frontend:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000/demo
```

Useful local URLs:

```text
Frontend: http://localhost:3000/demo
Backend health: http://127.0.0.1:8001/health
Backend API docs: http://127.0.0.1:8001/docs
```

## Configure Google locally

Google has two separate actions in DueScope:

1. **Sign in with Google** creates a DueScope session.
2. **Connect Google** authorizes optional Gmail read-only scanning and approved Google Calendar writes.

For a private local instance, create and use your own Google Cloud OAuth application. Do not use someone else's client secret.

### 1. Create a Google Cloud project

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project, for example `DueScope Local`.
3. Enable these APIs:
   - Google Calendar API
   - Gmail API, if you want Gmail job scanning
4. Open **Google Auth Platform** and configure an OAuth consent screen.
5. Choose **External** if you use a personal Gmail account.
6. While the app is in Testing, add your own Google account under **Audience** -> **Test users**.

### 2. Create an OAuth web client

Create an OAuth 2.0 Client ID of type **Web application**.

Add these authorized redirect URIs exactly:

```text
http://127.0.0.1:8001/api/auth/callback
http://127.0.0.1:8001/api/google/auth/callback
```

Add these values to `.env`:

```text
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8001/api/google/auth/callback
```

If the app has a separate identity callback configuration variable, use:

```text
http://127.0.0.1:8001/api/auth/callback
```

The redirect URI in your code, `.env`, and Google Cloud OAuth client must match exactly, including protocol, hostname, port, path, and trailing slash behavior.

### 3. Choose Google scopes

DueScope uses only the scopes required by enabled features:

```text
openid
email
profile
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/gmail.readonly
```

- `gmail.readonly` lets DueScope read matching recruiting messages. It cannot modify Gmail.
- `calendar.events` lets DueScope create or update events only after your explicit approval.

For local testing, use only your own account or accounts you have explicitly added as OAuth test users.

### 4. Test Google Calendar

1. Start DueScope locally.
2. Select **Sign in with Google**.
3. Select **Connect Google Calendar**.
4. Complete the Google consent screen.
5. Create or select a DueScope academic event.
6. Select **Approve for export and sync**.
7. Select **Sync this deadline to Google**.
8. Confirm the event appears in your Google Calendar.

### 5. Test Gmail job scanning

1. Complete the Google connection flow above.
2. Ensure Gmail API is enabled in your Google Cloud project.
3. Send yourself a clearly labeled test recruiting email from a controlled account, for example:

```text
Subject: Action required: Complete your online assessment

Hello,
Thank you for applying to Example Software for the Software Engineering Intern role.
You are invited to complete an online assessment.
Assessment deadline: Friday, October 2, 2026 at 11:59 PM CDT.
Please complete the assessment before the deadline.
```

4. In DueScope, open **Job applications**.
5. Select **Scan for new job updates**.
6. Review the source evidence and proposed reminder.
7. Select **Approve and add to Google Calendar**.
8. Confirm the reminder appears in Google Calendar.

Do not use other people's mailboxes without their informed permission.

## Configure Canvas locally

Canvas is an institution-hosted learning-management system. Every school can have a different Canvas domain and policy.

### Option A: personal Canvas access token

For a private local instance, the simplest path is a personal Canvas access token tied to your own account.

1. Sign in to your institution's Canvas site.
2. Open **Account** -> **Settings**.
3. Find **Approved Integrations** or **New Access Token**. The exact label varies by institution.
4. Create a token with a clear purpose such as `DueScope local development`.
5. Copy it once and store it only in your local `.env`.
6. Add these values:

```text
CANVAS_BASE_URL=https://your-school.instructure.com
CANVAS_ACCESS_TOKEN=your-personal-canvas-token
```

Use the Canvas base URL only. Do not append `/api/v1`.

For example:

```text
CANVAS_BASE_URL=https://uta.instructure.com
CANVAS_ACCESS_TOKEN=replace-with-your-token
```

7. Restart the backend after changing `.env`.
8. In DueScope, use **Import from Canvas** to load courses and import upcoming assignments.

Canvas tokens act like passwords. Never put them in Git, screenshots, URLs, support tickets, or chat.

### Option B: institution-approved Canvas OAuth

For a multi-user public Canvas connection, the institution usually must register/enable a Canvas developer key for DueScope. The school provides or approves an OAuth client configuration, then each student can sign in and authorize their own Canvas account.

This repository currently documents the private configured-token path. Universal Canvas OAuth is a future feature because it depends on each institution's Canvas administrator and developer-key policy.

### What Canvas import does

When configured, DueScope can read:

- Active courses
- Upcoming assignments
- Assignment due dates
- Quiz/exam items when Canvas represents them as assignments
- Canvas source IDs, course context, titles, and official due timestamps

DueScope treats Canvas as read-only. It does not submit assignments, alter course content, change grades, or post announcements.

## Run checks

Run these before committing changes:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v

cd frontend
$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8001"
npm run build
Remove-Item Env:\NEXT_PUBLIC_API_BASE_URL -ErrorAction SilentlyContinue
cd ..

git diff --check
git status --short
```

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Confirm the API is running |
| `GET` | `/api/auth/login` | Start Google identity sign-in |
| `GET` | `/api/auth/callback` | Receive the Google identity callback |
| `GET` | `/api/auth/me` | Return the signed-in user's safe display data |
| `POST` | `/api/auth/logout` | Revoke the current app session |
| `GET` | `/api/demo/workspace` | Get displayed courses, events, changes, workload, and proposals |
| `GET` | `/api/events` | List canonical academic events |
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
| `GET` | `/api/google/auth/status` | Check the current user's Google connection status |
| `POST` | `/api/google/auth/disconnect` | Delete the current user's Google data connection |
| `POST` | `/api/google/calendar/sync-approved` | Sync explicitly approved academic deadlines |
| `GET` | `/api/jobs` | List tracked job applications |
| `POST` | `/api/jobs/scan` | Read-only Gmail scan for supported recruiting updates |
| `PATCH` | `/api/jobs/{job_id}` | Review and update a tracked job application |
| `GET` | `/api/jobs/proposals` | List job Calendar proposals |
| `POST` | `/api/jobs/proposals/{proposal_id}/approve` | Approve one pending job reminder and create/update its Google Calendar event |
| `POST` | `/api/jobs/proposals/{proposal_id}/dismiss` | Dismiss one pending job reminder without changing Google Calendar |

## Limitations and roadmap

- DueScope is an early beta and not a substitute for checking official course systems and employer communications.
- The public demo uses safe sample data for integrations that are not open to unrestricted public OAuth onboarding.
- Broad public Gmail and Google Calendar access requires Google OAuth verification; Gmail's read-only scope has additional restricted-data requirements.
- Canvas import works with configured Canvas credentials. Universal Canvas OAuth depends on institution developer-key approval and is not yet implemented.
- Canvas announcement ingestion is planned but is not yet part of the configured Canvas import path.
- Job-status inference and reminder detection are heuristic and should be reviewed by the user.
- The displayed workspace includes seeded/demo data; complete per-user persistence is a future milestone.
- Ollama must be installed and running for local AI extraction.
- Gemini is optional and requires a usable API key.

## Security and repository safety

- Do not commit `.env`, `.env.local`, API keys, Canvas tokens, Gmail credentials, OAuth credentials, OAuth access/refresh tokens, session secrets, encryption keys, database URLs, local databases, virtual environments, generated ICS files, `frontend\node_modules`, or `frontend\.next`.
- Save source and documentation files as UTF-8.
- Keep provider credentials in local environment files or deployment secret settings only.
- Revoke and replace a credential immediately if it is accidentally exposed.
- Use only your own accounts or accounts whose owners have explicitly authorized testing.

## Team

- Khoi Anh Le Nguyen - [@ngkhoi111](https://github.com/ngkhoi111)
- Dong Quan Tran - [@dong-quan-tran](https://github.com/dong-quan-tran)

## HackRice 16

DueScope was built for the **HackRice 16 Work & Productivity** track. We plan to keep building it.

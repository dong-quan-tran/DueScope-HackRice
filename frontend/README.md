# DueScope Frontend

This directory contains the Next.js frontend for DueScope, an evidence-backed academic deadline manager built for HackRice 16.

For the complete project overview, backend setup, local AI configuration, Canvas integration, API documentation, and demo workflow, see the repository-root [README](../README.md).

## Run locally

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

The frontend expects the FastAPI backend to run at:

```text
http://127.0.0.1:8001
```

Override the backend URL with:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
```

Place that value in `frontend/.env.local` if you need a different backend URL. Do not commit local environment files or tokens.

## Main interface features

- Upcoming academic deadline dashboard
- Canvas course selection and deadline import
- AI-assisted course-update scanning
- Evidence-backed deadline proposals
- Explicit accept/reject review controls
- Deadline history for accepted changes
- Export approval controls
- ICS calendar export

## Validate before merging

```bash
npm run build
```

Do not commit:

```text
node_modules/
.next/
.env.local
```

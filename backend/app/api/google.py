from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from app.api.demo import DEMO_WORKSPACE
from app.schemas.events import AcademicEvent
from app.services.google_oauth import (
    create_flow,
    get_credentials,
    save_credentials,
)


router = APIRouter(prefix="/google", tags=["google"])

# Local-development storage only. It is cleared when Uvicorn restarts.
# Production should use a signed session plus durable server-side storage.
oauth_flows: dict[str, Any] = {}


class GoogleCalendarSyncRequest(BaseModel):
    """
    If event_ids is omitted or empty, sync every currently eligible event.
    Eligible events must be approved and have verified/updated status.
    """

    event_ids: list[str] | None = Field(
        default=None,
        description=(
            "Optional DueScope event IDs to sync. Omit or provide an empty "
            "array to sync every approved verified/updated event."
        ),
    )


def get_workspace_event(event_id: str) -> AcademicEvent | None:
    for stored_event in DEMO_WORKSPACE["events"]:
        if stored_event["id"] == event_id:
            return AcademicEvent.model_validate(stored_event)

    return None


def selected_workspace_events(
    event_ids: list[str] | None,
) -> tuple[list[AcademicEvent], list[dict[str, str]]]:
    """
    Return selected events and explicit not-found failures.

    If no IDs are supplied, return all workspace events and let eligibility
    checks decide which records are skipped.
    """
    if not event_ids:
        return (
            [
                AcademicEvent.model_validate(event)
                for event in DEMO_WORKSPACE["events"]
            ],
            [],
        )

    events: list[AcademicEvent] = []
    failures: list[dict[str, str]] = []

    for event_id in event_ids:
        event = get_workspace_event(event_id)

        if event is None:
            failures.append(
                {
                    "event_id": event_id,
                    "reason": "DueScope event was not found.",
                }
            )
            continue

        events.append(event)

    return events, failures


def course_name_for_event(event: AcademicEvent) -> str:
    for course in DEMO_WORKSPACE["courses"]:
        if course["id"] == event.course_id:
            return str(course["name"])

    return event.course_id


def source_for_event(event: AcademicEvent) -> dict[str, Any] | None:
    for source in DEMO_WORKSPACE["sources"]:
        if source["id"] == event.source_id:
            return source

    return None


def event_description(event: AcademicEvent) -> str:
    """
    Build a human-readable Calendar description that preserves DueScope
    provenance without exposing OAuth secrets.
    """
    course_name = course_name_for_event(event)
    source = source_for_event(event)

    lines = [
        "Created by DueScope.",
        "",
        f"Course: {course_name}",
        f"DueScope event ID: {event.id}",
        f"Status: {event.status}",
        f"Approved for sync: {event.approved}",
    ]

    if source is not None:
        lines.extend(
            [
                "",
                "Evidence",
                f"Source type: {source.get('type', 'unknown')}",
                f"Source title: {source.get('title', 'Untitled source')}",
            ]
        )

        source_url = source.get("url")
        if source_url:
            lines.append(f"Source URL: {source_url}")

        excerpt = source.get("excerpt") or source.get("content")
        if excerpt:
            lines.extend(
                [
                    "",
                    "Source excerpt:",
                    str(excerpt).strip(),
                ]
            )

    return "\n".join(lines)


def calendar_event_body(event: AcademicEvent) -> dict[str, Any]:
    """
    Calendar deadlines use a 30-minute block ending at due_at.
    """
    if event.due_at is None:
        raise ValueError("DueScope event has no due date.")

    due_at = event.due_at
    start_at = due_at - timedelta(minutes=30)

    time_zone = (
        getattr(due_at.tzinfo, "key", None)
        or str(due_at.tzinfo)
        or "America/Chicago"
    )

    return {
        "summary": event.title,
        "description": event_description(event),
        "start": {
            "dateTime": start_at.isoformat(),
            "timeZone": time_zone,
        },
        "end": {
            "dateTime": due_at.isoformat(),
            "timeZone": time_zone,
        },
        "extendedProperties": {
            "private": {
                "duescope_event_id": event.id,
                "duescope_source_id": event.source_id,
                "duescope_status": str(event.status),
            }
        },
    }


def find_google_event_for_duescope_event(
    service: Any,
    duescope_event_id: str,
) -> dict[str, Any] | None:
    response = service.events().list(
        calendarId="primary",
        privateExtendedProperty=f"duescope_event_id={duescope_event_id}",
        singleEvents=True,
        maxResults=10,
    ).execute()

    items = response.get("items", [])
    return items[0] if items else None


def job_calendar_description(proposal: dict[str, Any]) -> str:
    lines = [
        "Created by DueScope after explicit user approval.",
        "",
        f"Job application: {proposal['company']}",
        f"Role: {proposal['role']}",
        f"Reminder type: {proposal['kind'].replace('_', ' ')}",
        f"DueScope job ID: {proposal['job_id']}",
        f"Proposal ID: {proposal['id']}",
        "",
        "Source evidence:",
        proposal["source_excerpt"],
    ]

    source_url = proposal.get("gmail_url")
    if source_url:
        lines.extend(["", f"Open source email: {source_url}"])

    return "\n".join(lines)


def job_calendar_event_body(proposal: dict[str, Any]) -> dict[str, Any]:
    """
    Convert an approved job-calendar proposal to a Google Calendar event.

    Assessments and scheduling deadlines are displayed as a 30-minute reminder
    ending at due_at. Confirmed interviews use their explicit start/end times.
    """
    start_at = datetime.fromisoformat(proposal["starts_at"])
    end_at = datetime.fromisoformat(proposal["ends_at"])

    time_zone = (
        getattr(start_at.tzinfo, "key", None)
        or str(start_at.tzinfo)
        or "America/Chicago"
    )

    return {
        "summary": proposal["title"],
        "description": job_calendar_description(proposal),
        "start": {
            "dateTime": start_at.isoformat(),
            "timeZone": time_zone,
        },
        "end": {
            "dateTime": end_at.isoformat(),
            "timeZone": time_zone,
        },
        "extendedProperties": {
            "private": {
                "duescope_job_id": proposal["job_id"],
                "duescope_job_proposal_id": proposal["id"],
                "duescope_job_kind": proposal["kind"],
            }
        },
    }


def find_google_event_for_job_proposal(
    service: Any,
    proposal_id: str,
) -> dict[str, Any] | None:
    response = service.events().list(
        calendarId="primary",
        privateExtendedProperty=f"duescope_job_proposal_id={proposal_id}",
        singleEvents=True,
        maxResults=10,
    ).execute()

    items = response.get("items", [])
    return items[0] if items else None


def upsert_job_calendar_event(proposal: dict[str, Any]) -> dict[str, str]:
    """
    Create or update the Calendar event for an already approved job proposal.

    This is intentionally called only from the explicit approve endpoint in
    jobs.py. It never runs just because Gmail finds an email.
    """
    if proposal.get("status") != "approved":
        raise ValueError("Only approved job proposals can sync to Google Calendar.")

    credentials = get_credentials()
    service = build("calendar", "v3", credentials=credentials)
    body = job_calendar_event_body(proposal)
    existing_event = find_google_event_for_job_proposal(service, proposal["id"])

    if existing_event is None:
        saved_event = service.events().insert(
            calendarId="primary",
            body=body,
        ).execute()
        action = "created"
    else:
        saved_event = service.events().update(
            calendarId="primary",
            eventId=existing_event["id"],
            body=body,
        ).execute()
        action = "updated"

    proposal["google_calendar_event_id"] = saved_event["id"]
    proposal["google_calendar_url"] = saved_event.get("htmlLink", "")
    proposal["calendar_synced_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "action": action,
        "google_calendar_event_id": saved_event["id"],
        "calendar_url": saved_event.get("htmlLink", ""),
    }


@router.get("/auth/start")
def start_google_auth() -> RedirectResponse:
    flow = create_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    oauth_flows[state] = flow

    return RedirectResponse(
        url=authorization_url,
        status_code=307,
    )


@router.get("/auth/callback")
def google_auth_callback(
    code: str = Query(...),
    state: str | None = Query(default=None),
) -> HTMLResponse:
    if not state:
        raise HTTPException(
            status_code=400,
            detail="Missing OAuth state. Start Google authorization again.",
        )

    flow = oauth_flows.pop(state, None)

    if flow is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "OAuth session was not found or expired. "
                "Start Google authorization again from /api/google/auth/start."
            ),
        )

    try:
        flow.fetch_token(code=code)
        save_credentials(flow.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Google token exchange failed: {exc}",
        ) from exc

    return HTMLResponse(
        content="""
        <!doctype html>
        <html>
          <head>
            <meta charset="utf-8">
            <title>DueScope Connected</title>
          </head>
          <body style="font-family: system-ui, sans-serif; max-width: 42rem; margin: 4rem auto; line-height: 1.5;">
            <h1>Google connected successfully</h1>
            <p>Your Google Calendar and Gmail permissions were saved for DueScope.</p>
            <p>You may close this tab and return to the application.</p>
          </body>
        </html>
        """,
        status_code=200,
    )


@router.get("/auth/status")
def google_auth_status() -> dict[str, bool]:
    try:
        get_credentials()
        return {"connected": True}
    except HTTPException:
        return {"connected": False}


@router.post("/calendar/sync-approved")
def sync_approved_deadlines(
    request: GoogleCalendarSyncRequest,
) -> dict[str, list[dict[str, str]]]:
    """
    Create or update Google Calendar events for approved trusted DueScope
    deadlines.

    This endpoint does not sync candidates, unresolved proposals, unapproved
    events, needs_review events, or canceled events.
    """
    credentials = get_credentials()
    service = build("calendar", "v3", credentials=credentials)

    events, failed = selected_workspace_events(request.event_ids)

    created: list[dict[str, str]] = []
    updated: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    for event in events:
        if not event.approved:
            skipped.append(
                {
                    "event_id": event.id,
                    "title": event.title,
                    "reason": "Event is not approved for calendar sync.",
                }
            )
            continue

        if event.status not in {"verified", "updated"}:
            skipped.append(
                {
                    "event_id": event.id,
                    "title": event.title,
                    "reason": (
                        "Only verified or updated events can sync to "
                        "Google Calendar."
                    ),
                }
            )
            continue

        try:
            body = calendar_event_body(event)
            existing_google_event = find_google_event_for_duescope_event(
                service,
                event.id,
            )

            if existing_google_event is None:
                saved_event = service.events().insert(
                    calendarId="primary",
                    body=body,
                ).execute()

                created.append(
                    {
                        "event_id": event.id,
                        "title": event.title,
                        "google_event_id": saved_event["id"],
                        "calendar_url": saved_event.get("htmlLink", ""),
                    }
                )
            else:
                saved_event = service.events().update(
                    calendarId="primary",
                    eventId=existing_google_event["id"],
                    body=body,
                ).execute()

                updated.append(
                    {
                        "event_id": event.id,
                        "title": event.title,
                        "google_event_id": saved_event["id"],
                        "calendar_url": saved_event.get("htmlLink", ""),
                    }
                )
        except Exception as exc:
            failed.append(
                {
                    "event_id": event.id,
                    "title": event.title,
                    "reason": str(exc),
                }
            )

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
    }
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services.google_oauth import (
    TOKEN_PATH,
    create_flow,
    get_credentials,
    save_credentials,
)


router = APIRouter(prefix="/google", tags=["google"])

# Local-development storage only. Uvicorn restart clears it; simply restart
# authorization if that happens. Use session/database/Redis storage in production.
oauth_flows = {}


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
def sync_approved_deadlines() -> dict:
    """
    Temporary Phase 4 verification endpoint.

    Creates one clearly labeled test event in the connected user's primary
    Google Calendar. Replace the hard-coded event with approved DueScope
    deadlines once the event model is wired in.
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    from googleapiclient.discovery import build

    credentials = get_credentials()
    service = build("calendar", "v3", credentials=credentials)

    central = ZoneInfo("America/Chicago")
    start = datetime.now(central) + timedelta(hours=1)
    end = start + timedelta(minutes=30)

    event_body = {
        "summary": "DueScope test sync",
        "description": (
            "Created by DueScope Phase 4 Google Calendar integration. "
            "You can delete this test event after verifying the sync."
        ),
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": "America/Chicago",
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": "America/Chicago",
        },
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event_body,
    ).execute()

    return {
        "success": True,
        "message": "Test event created in your primary Google Calendar.",
        "event_id": created_event["id"],
        "event_url": created_event.get("htmlLink"),
    }

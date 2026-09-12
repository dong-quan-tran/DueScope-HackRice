from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from icalendar import Calendar, Event
from pydantic import BaseModel, Field

from app.api.demo import DEMO_WORKSPACE
from app.schemas.events import AcademicEvent

router = APIRouter(prefix="/calendar", tags=["calendar"])


class CalendarExportRequest(BaseModel):
    event_ids: list[str] = Field(min_length=1)


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def event_start(event: AcademicEvent) -> Optional[datetime]:
    return event.starts_at or event.due_at


def event_end(event: AcademicEvent) -> Optional[datetime]:
    if event.due_at:
        return event.due_at
    return event.starts_at


@router.post("/export")
def export_calendar(request: CalendarExportRequest) -> Response:
    stored_events = {
        item["id"]: AcademicEvent.model_validate(item)
        for item in DEMO_WORKSPACE["events"]
    }

    missing_ids = [
        event_id
        for event_id in request.event_ids
        if event_id not in stored_events
    ]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown event IDs: {', '.join(missing_ids)}",
        )

    selected_events = [stored_events[event_id] for event_id in request.event_ids]
    invalid_events = [
        event.title
        for event in selected_events
        if not event.approved
        or event.status.value not in {"verified", "updated"}
        or event_start(event) is None
    ]
    if invalid_events:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only approved, verified/updated events with a date can be exported: "
                + ", ".join(invalid_events)
            ),
        )

    course_names = {
        course["id"]: f'{course["code"]} - {course["name"]}'
        for course in DEMO_WORKSPACE["courses"]
    }

    calendar = Calendar()
    calendar.add("prodid", "-//DueScope//HackRice 16//EN")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("x-wr-calname", "DueScope")

    for academic_event in selected_events:
        calendar_event = Event()
        start = event_start(academic_event)
        end = event_end(academic_event) or start

        calendar_event.add("uid", f'{academic_event.id}@duescope.local')
        calendar_event.add("dtstamp", datetime.now(timezone.utc))
        calendar_event.add("dtstart", to_utc(start))
        calendar_event.add("dtend", to_utc(end))
        calendar_event.add(
            "summary",
            f'{course_names[academic_event.course_id]}: {academic_event.title}',
        )
        calendar_event.add(
            "description",
            (
                f'DueScope status: {academic_event.status.value}\\n'
                f'Source: {academic_event.source_id}\\n'
                f'Evidence: {academic_event.source_excerpt}'
            ),
        )

        if academic_event.location:
            calendar_event.add("location", academic_event.location)

        calendar.add_component(calendar_event)

    return Response(
        content=calendar.to_ical(),
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="duescope-calendar.ics"'
        },
    )

"""Persistent demo-workspace bootstrap and serialization.

The existing in-memory DEMO_WORKSPACE remains available to legacy routes during
the migration. This module persists an equivalent academic dashboard dataset
for GET /api/demo/workspace so the public demo survives API restarts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import Base, engine
import app.models  # noqa: F401
from app.models.domain import AcademicEvent, AcademicEventHistory, AcademicProposal, Course, Source, User
from app.repositories.academic import get_or_create_demo_user


DEMO_TIMEZONE = "America/Chicago"


DEMO_COURSES: list[dict[str, str]] = [
    {"id": "cse-3310", "code": "CSE 3310", "name": "Algorithms", "color": "#3B82F6"},
    {"id": "math-2425", "code": "MATH 2425", "name": "Calculus III", "color": "#8B5CF6"},
    {"id": "chem-3315", "code": "CHEM 3315", "name": "Analytical Chemistry", "color": "#10B981"},
]

DEMO_SOURCES: list[dict[str, str]] = [
    {
        "id": "source-algorithms-syllabus",
        "course_id": "cse-3310",
        "type": "syllabus",
        "title": "CSE 3310 Syllabus",
        "received_at": "2026-09-01T09:00:00-05:00",
    },
    {
        "id": "source-algorithms-announcement",
        "course_id": "cse-3310",
        "type": "instructor_announcement",
        "title": "Quiz 2 schedule update",
        "received_at": "2026-09-12T09:20:00-05:00",
    },
    {
        "id": "source-calculus-email",
        "course_id": "math-2425",
        "type": "instructor_email",
        "title": "Exam 1 clarification",
        "received_at": "2026-09-12T08:10:00-05:00",
    },
    {
        "id": "source-chemistry-announcement",
        "course_id": "chem-3315",
        "type": "instructor_announcement",
        "title": "GC-MS lab report extension",
        "received_at": "2026-09-12T10:00:00-05:00",
    },
]

DEMO_EVENTS: list[dict[str, Any]] = [
    {
        "id": "event-quiz-2",
        "course_id": "cse-3310",
        "type": "quiz",
        "title": "Quiz 2",
        "starts_at": "2026-09-17T08:00:00-05:00",
        "due_at": "2026-09-17T23:59:00-05:00",
        "status": "updated",
        "approved": False,
        "workload_minutes": 90,
        "source_id": "source-algorithms-announcement",
        "source_excerpt": "Quiz 2 has been moved from Tuesday to Thursday, September 17. It will remain available in Canvas from 8:00 AM to 11:59 PM.",
        "history": [
            {
                "due_at": "2026-09-15T23:59:00-05:00",
                "source_id": "source-algorithms-syllabus",
                "reason": "Original syllabus schedule",
                "is_current": False,
            },
            {
                "due_at": "2026-09-17T23:59:00-05:00",
                "source_id": "source-algorithms-announcement",
                "reason": "Instructor announcement explicitly rescheduled Quiz 2",
                "is_current": True,
            },
        ],
    },
    {
        "id": "event-assignment-2",
        "course_id": "cse-3310",
        "type": "assignment",
        "title": "Programming Assignment 2",
        "starts_at": None,
        "due_at": "2026-09-18T23:59:00-05:00",
        "status": "verified",
        "approved": False,
        "workload_minutes": 420,
        "source_id": "source-algorithms-announcement",
        "source_excerpt": "Programming Assignment 2 is still due Friday at 11:59 PM. Please start the assignment early; expected work time is 6-8 hours.",
        "history": [],
    },
    {
        "id": "event-midterm",
        "course_id": "cse-3310",
        "type": "exam",
        "title": "Midterm Exam",
        "starts_at": "2026-09-23T19:00:00-05:00",
        "due_at": "2026-09-23T21:00:00-05:00",
        "status": "verified",
        "approved": False,
        "workload_minutes": 300,
        "source_id": "source-algorithms-syllabus",
        "source_excerpt": "Midterm Exam - Wednesday, September 23, 7:00 PM",
        "history": [],
    },
    {
        "id": "event-calculus-review",
        "course_id": "math-2425",
        "type": "review",
        "title": "Exam 1 Review Session",
        "starts_at": "2026-09-17T17:00:00-05:00",
        "due_at": "2026-09-17T18:00:00-05:00",
        "status": "verified",
        "approved": False,
        "workload_minutes": 60,
        "source_id": "source-calculus-email",
        "source_excerpt": "A review session will be held Thursday at 5 PM.",
        "history": [],
    },
    {
        "id": "event-calculus-exam",
        "course_id": "math-2425",
        "type": "exam",
        "title": "Exam 1",
        "starts_at": "2026-09-18T18:00:00-05:00",
        "due_at": "2026-09-18T20:00:00-05:00",
        "location": "PKH 102",
        "status": "verified",
        "approved": False,
        "workload_minutes": 300,
        "source_id": "source-calculus-email",
        "source_excerpt": "Exam 1 is Friday, September 18, from 6:00 PM to 8:00 PM in PKH 102.",
        "history": [],
    },
    {
        "id": "event-gcms-report",
        "course_id": "chem-3315",
        "type": "lab",
        "title": "GC-MS Lab Report",
        "starts_at": None,
        "due_at": "2026-09-21T17:00:00-05:00",
        "status": "updated",
        "approved": False,
        "workload_minutes": 240,
        "source_id": "source-chemistry-announcement",
        "source_excerpt": "The GC-MS lab report deadline is extended from Sunday to Monday, September 21 at 5:00 PM.",
        "history": [
            {
                "due_at": "2026-09-20T17:00:00-05:00",
                "source_id": "source-chemistry-announcement",
                "reason": "Original deadline referenced in extension notice",
                "is_current": False,
            },
            {
                "due_at": "2026-09-21T17:00:00-05:00",
                "source_id": "source-chemistry-announcement",
                "reason": "Deadline extension",
                "is_current": True,
            },
        ],
    },
    {
        "id": "event-chem-prelab",
        "course_id": "chem-3315",
        "type": "lab",
        "title": "GC-MS Pre-Lab Worksheet",
        "starts_at": None,
        "due_at": None,
        "status": "needs_review",
        "approved": False,
        "workload_minutes": 60,
        "source_id": "source-chemistry-announcement",
        "source_excerpt": "Pre-lab worksheets are still due before your lab section begins.",
        "needs_review_reason": "Lab-section meeting time is unavailable, so DueScope cannot safely determine the due time.",
        "history": [],
    },
]

DEMO_CHANGES = [
    {
        "event_id": "event-quiz-2",
        "kind": "rescheduled",
        "message": "Quiz 2 moved from Tuesday, Sept. 15 to Thursday, Sept. 17.",
    },
    {
        "event_id": "event-gcms-report",
        "kind": "extended",
        "message": "GC-MS Lab Report extended to Monday, Sept. 21 at 5:00 PM.",
    },
    {
        "event_id": "event-chem-prelab",
        "kind": "needs_review",
        "message": "GC-MS Pre-Lab Worksheet needs a lab-section time before it can be added to a calendar.",
    },
]

DEMO_WORKLOAD = [
    {
        "date": "2026-09-17",
        "minutes": 150,
        "level": "normal",
        "reason": "Quiz 2 and Calculus review session",
    },
    {
        "date": "2026-09-18",
        "minutes": 720,
        "level": "high",
        "reason": "Programming Assignment 2 is due and Calculus Exam 1 runs from 6:00 PM to 8:00 PM.",
    },
    {
        "date": "2026-09-21",
        "minutes": 240,
        "level": "normal",
        "reason": "GC-MS Lab Report due at 5:00 PM",
    },
]


def parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.isoformat()
    return value.isoformat()


def ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_demo_workspace(db: Session) -> User:
    """Seed the persistent demo dataset only when it does not already exist."""
    ensure_tables()
    user = get_or_create_demo_user(db)

    if db.scalar(select(AcademicEvent.id).where(AcademicEvent.user_id == user.id).limit(1)):
        return user

    courses_by_external_id: dict[str, Course] = {}
    for item in DEMO_COURSES:
        course = Course(
            user_id=user.id,
            external_id=item["id"],
            name=item["name"],
            code=item["code"],
            provider="demo",
            metadata_json={"color": item["color"]},
        )
        db.add(course)
        db.flush()
        courses_by_external_id[item["id"]] = course

    sources_by_external_id: dict[str, Source] = {}
    for item in DEMO_SOURCES:
        source = Source(
            user_id=user.id,
            external_id=item["id"],
            provider="demo",
            source_type=item["type"],
            title=item["title"],
            received_at=parse_datetime(item["received_at"]),
            metadata_json={"course_external_id": item["course_id"]},
        )
        db.add(source)
        db.flush()
        sources_by_external_id[item["id"]] = source

    for item in DEMO_EVENTS:
        due_at = parse_datetime(item["due_at"])
        if due_at is None:
            due_at = parse_datetime(item["starts_at"])

        if due_at is None:
            due_at = datetime(2026, 9, 1, 0, 0)

        event = AcademicEvent(
            id=item["id"],
            user_id=user.id,
            course_id=courses_by_external_id[item["course_id"]].id,
            source_id=sources_by_external_id[item["source_id"]].id,
            external_id=item["id"],
            title=item["title"],
            due_at=due_at,
            timezone_name=DEMO_TIMEZONE,
            status=item["status"],
            calendar_approved=item["approved"],
            metadata_json={
                "type": item["type"],
                "starts_at": item["starts_at"],
                "location": item.get("location"),
                "workload_minutes": item["workload_minutes"],
                "source_excerpt": item["source_excerpt"],
                "needs_review_reason": item.get("needs_review_reason"),
            },
        )
        db.add(event)
        db.flush()

        for history_item in item["history"]:
            history_due_at = parse_datetime(history_item["due_at"])
            if history_due_at is None:
                continue

            db.add(
                AcademicEventHistory(
                    event_id=event.id,
                    due_at=history_due_at,
                    title=item["title"],
                    status=item["status"],
                    reason=history_item["reason"],
                )
            )

    db.commit()
    return user


def _serialize_source(source: Source) -> dict[str, Any]:
    return {
        "id": source.external_id or source.id,
        "course_id": source.metadata_json.get("course_external_id"),
        "type": source.source_type,
        "title": source.title,
        "received_at": isoformat(source.received_at),
    }


def _serialize_event(event: AcademicEvent) -> dict[str, Any]:
    metadata = event.metadata_json or {}
    source_external_id = event.source.external_id if event.source else None
    course_external_id = event.course.external_id if event.course else None

    history = [
        {
            "due_at": isoformat(item.due_at),
            "source_id": source_external_id,
            "reason": item.reason,
            "is_current": False,
        }
        for item in event.history
    ]

    if event.status == "updated":
        history.append(
            {
                "due_at": isoformat(event.due_at),
                "source_id": source_external_id,
                "reason": "Current canonical deadline",
                "is_current": True,
            }
        )

    return {
        "id": event.external_id or event.id,
        "course_id": course_external_id,
        "type": metadata.get("type", "assignment"),
        "title": event.title,
        "starts_at": metadata.get("starts_at"),
        "due_at": isoformat(event.due_at) if metadata.get("has_due_at", True) else None,
        "location": metadata.get("location"),
        "status": event.status,
        "approved": event.calendar_approved,
        "workload_minutes": metadata.get("workload_minutes", 0),
        "source_id": source_external_id,
        "source_excerpt": metadata.get("source_excerpt"),
        "needs_review_reason": metadata.get("needs_review_reason"),
        "history": history,
    }


def persistent_demo_workspace(db: Session) -> dict[str, Any]:
    user = seed_demo_workspace(db)

    courses = list(
        db.scalars(
            select(Course)
            .where(Course.user_id == user.id)
            .order_by(Course.name.asc())
        )
    )
    sources = list(
        db.scalars(
            select(Source)
            .where(Source.user_id == user.id)
            .order_by(Source.received_at.asc())
        )
    )
    events = list(
        db.scalars(
            select(AcademicEvent)
            .options(
                selectinload(AcademicEvent.course),
                selectinload(AcademicEvent.source),
                selectinload(AcademicEvent.history),
            )
            .where(AcademicEvent.user_id == user.id)
            .order_by(AcademicEvent.due_at.asc(), AcademicEvent.title.asc())
        )
    )

    return {
        "student": {"name": "Demo Student", "timezone": DEMO_TIMEZONE},
        "courses": [
            {
                "id": course.external_id or course.id,
                "code": course.code,
                "name": course.name,
                "color": (course.metadata_json or {}).get("color", "#64748B"),
            }
            for course in courses
        ],
        "sources": [_serialize_source(source) for source in sources],
        "events": [_serialize_event(event) for event in events],
        "changes": DEMO_CHANGES,
        "workload": DEMO_WORKLOAD,
        "proposals": [],
        "job_applications": [],
        "job_calendar_proposals": [],
    }

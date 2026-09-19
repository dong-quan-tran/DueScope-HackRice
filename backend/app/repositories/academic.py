"""Persistent academic workflow repository.

This module intentionally contains no HTTP or Canvas/Gmail integration code.
It preserves DueScope's review-first rule: conflicting candidate dates become
proposals, and only an explicit accept operation updates a canonical event.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.domain import (
    AcademicEvent,
    AcademicEventHistory,
    AcademicProposal,
    Course,
    Source,
    User,
)


DEMO_USER_EMAIL = "demo@duescope.local"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_demo_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    if user is None:
        user = User(
            email=DEMO_USER_EMAIL,
            display_name="DueScope Demo",
            is_demo=True,
        )
        db.add(user)
        db.flush()
    return user


def list_courses(db: Session, user_id: str) -> list[Course]:
    return list(
        db.scalars(
            select(Course)
            .where(Course.user_id == user_id)
            .order_by(Course.name.asc())
        )
    )


def upsert_course(
    db: Session,
    *,
    user_id: str,
    external_id: str | None,
    name: str,
    code: str | None = None,
    provider: str = "manual",
    metadata: dict[str, Any] | None = None,
) -> Course:
    course: Course | None = None

    if external_id:
        course = db.scalar(
            select(Course).where(
                Course.user_id == user_id,
                Course.external_id == external_id,
            )
        )

    if course is None:
        course = Course(
            user_id=user_id,
            external_id=external_id,
            name=name,
            code=code,
            provider=provider,
            metadata_json=metadata or {},
        )
        db.add(course)
    else:
        course.name = name
        course.code = code
        course.provider = provider
        if metadata is not None:
            course.metadata_json = metadata

    db.flush()
    return course


def upsert_source(
    db: Session,
    *,
    user_id: str,
    external_id: str | None,
    provider: str,
    source_type: str,
    title: str,
    excerpt: str | None,
    source_url: str | None = None,
    received_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> Source:
    source: Source | None = None

    if external_id:
        source = db.scalar(
            select(Source).where(
                Source.user_id == user_id,
                Source.external_id == external_id,
            )
        )

    if source is None:
        source = Source(
            user_id=user_id,
            external_id=external_id,
            provider=provider,
            source_type=source_type,
            title=title,
            excerpt=excerpt,
            source_url=source_url,
            received_at=received_at,
            metadata_json=metadata or {},
        )
        db.add(source)
    else:
        source.provider = provider
        source.source_type = source_type
        source.title = title
        source.excerpt = excerpt
        source.source_url = source_url
        source.received_at = received_at
        if metadata is not None:
            source.metadata_json = metadata

    db.flush()
    return source


def get_event(db: Session, *, user_id: str, event_id: str) -> AcademicEvent | None:
    return db.scalar(
        select(AcademicEvent)
        .options(
            selectinload(AcademicEvent.history),
            selectinload(AcademicEvent.proposals),
            selectinload(AcademicEvent.course),
            selectinload(AcademicEvent.source),
        )
        .where(
            AcademicEvent.id == event_id,
            AcademicEvent.user_id == user_id,
        )
    )


def list_events(db: Session, user_id: str) -> list[AcademicEvent]:
    return list(
        db.scalars(
            select(AcademicEvent)
            .options(
                selectinload(AcademicEvent.history),
                selectinload(AcademicEvent.proposals),
                selectinload(AcademicEvent.course),
                selectinload(AcademicEvent.source),
            )
            .where(AcademicEvent.user_id == user_id)
            .order_by(AcademicEvent.due_at.asc(), AcademicEvent.title.asc())
        )
    )


def find_event_by_external_id(
    db: Session,
    *,
    user_id: str,
    external_id: str,
) -> AcademicEvent | None:
    return db.scalar(
        select(AcademicEvent).where(
            AcademicEvent.user_id == user_id,
            AcademicEvent.external_id == external_id,
        )
    )


def create_event(
    db: Session,
    *,
    user_id: str,
    title: str,
    due_at: datetime,
    timezone_name: str,
    status: str,
    course_id: str | None = None,
    source_id: str | None = None,
    external_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AcademicEvent:
    event = AcademicEvent(
        user_id=user_id,
        course_id=course_id,
        source_id=source_id,
        external_id=external_id,
        title=title,
        due_at=due_at,
        timezone_name=timezone_name,
        status=status,
        calendar_approved=False,
        metadata_json=metadata or {},
    )
    db.add(event)
    db.flush()
    return event


def create_proposal(
    db: Session,
    *,
    user_id: str,
    event_id: str,
    proposed_title: str,
    proposed_due_at: datetime,
    source_id: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AcademicProposal:
    proposal = AcademicProposal(
        user_id=user_id,
        event_id=event_id,
        source_id=source_id,
        proposed_title=proposed_title,
        proposed_due_at=proposed_due_at,
        reason=reason,
        status="pending",
        metadata_json=metadata or {},
    )
    db.add(proposal)
    db.flush()
    return proposal


def get_proposal(
    db: Session,
    *,
    user_id: str,
    proposal_id: str,
) -> AcademicProposal | None:
    return db.scalar(
        select(AcademicProposal)
        .options(selectinload(AcademicProposal.event))
        .where(
            AcademicProposal.id == proposal_id,
            AcademicProposal.user_id == user_id,
        )
    )


def accept_proposal(
    db: Session,
    *,
    user_id: str,
    proposal_id: str,
) -> AcademicProposal | None:
    proposal = get_proposal(db, user_id=user_id, proposal_id=proposal_id)

    if proposal is None or proposal.status != "pending":
        return None

    event = proposal.event

    history = AcademicEventHistory(
        event_id=event.id,
        title=event.title,
        due_at=event.due_at,
        status=event.status,
        reason=f"Accepted proposal {proposal.id}",
    )
    db.add(history)

    event.title = proposal.proposed_title
    event.due_at = proposal.proposed_due_at
    event.status = "updated"
    event.calendar_approved = False
    event.calendar_event_id = None
    event.calendar_event_url = None

    proposal.status = "accepted"
    proposal.resolved_at = utc_now()

    db.flush()
    return proposal


def reject_proposal(
    db: Session,
    *,
    user_id: str,
    proposal_id: str,
) -> AcademicProposal | None:
    proposal = get_proposal(db, user_id=user_id, proposal_id=proposal_id)

    if proposal is None or proposal.status != "pending":
        return None

    proposal.status = "rejected"
    proposal.resolved_at = utc_now()

    db.flush()
    return proposal

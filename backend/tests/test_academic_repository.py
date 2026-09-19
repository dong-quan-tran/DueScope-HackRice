from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import Base
import app.models  # noqa: F401
from app.repositories.academic import (
    accept_proposal,
    create_event,
    create_proposal,
    get_or_create_demo_user,
    reject_proposal,
)


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    with factory() as session:
        yield session

    Base.metadata.drop_all(engine)


def test_accept_proposal_preserves_history_and_resets_calendar_approval(db: Session) -> None:
    user = get_or_create_demo_user(db)

    original_due_at = datetime(2026, 9, 25, 17, 0, tzinfo=timezone.utc)
    revised_due_at = original_due_at + timedelta(days=2)

    event = create_event(
        db,
        user_id=user.id,
        title="Project proposal",
        due_at=original_due_at,
        timezone_name="America/Chicago",
        status="verified",
    )
    event.calendar_approved = True
    event.calendar_event_id = "calendar-event-1"
    event.calendar_event_url = "https://calendar.google.com/event?eid=1"

    proposal = create_proposal(
        db,
        user_id=user.id,
        event_id=event.id,
        proposed_title="Project proposal — revised",
        proposed_due_at=revised_due_at,
        reason="Instructor extension",
    )

    accepted = accept_proposal(db, user_id=user.id, proposal_id=proposal.id)
    db.commit()

    assert accepted is not None
    assert accepted.status == "accepted"
    assert event.title == "Project proposal — revised"
    assert event.due_at == revised_due_at
    assert event.status == "updated"
    assert event.calendar_approved is False
    assert event.calendar_event_id is None
    assert event.calendar_event_url is None
    assert len(event.history) == 1
    assert event.history[0].title == "Project proposal"
    assert event.history[0].due_at.replace(tzinfo=timezone.utc) == original_due_at


def test_reject_proposal_keeps_canonical_event_unchanged(db: Session) -> None:
    user = get_or_create_demo_user(db)

    original_due_at = datetime(2026, 9, 25, 17, 0, tzinfo=timezone.utc)
    event = create_event(
        db,
        user_id=user.id,
        title="Homework 5",
        due_at=original_due_at,
        timezone_name="America/Chicago",
        status="verified",
    )

    proposal = create_proposal(
        db,
        user_id=user.id,
        event_id=event.id,
        proposed_title="Homework 5",
        proposed_due_at=original_due_at + timedelta(days=1),
    )

    rejected = reject_proposal(db, user_id=user.id, proposal_id=proposal.id)
    db.commit()

    assert rejected is not None
    assert rejected.status == "rejected"
    assert event.title == "Homework 5"
    assert event.due_at == original_due_at
    assert event.status == "verified"
    assert event.history == []


def test_proposals_are_scoped_to_their_owner(db: Session) -> None:
    first_user = get_or_create_demo_user(db)

    second_user = type(first_user)(
        email=f"second-{uuid4()}@duescope.local",
        display_name="Second user",
        is_demo=False,
    )
    db.add(second_user)
    db.flush()

    event = create_event(
        db,
        user_id=first_user.id,
        title="Quiz",
        due_at=datetime(2026, 9, 25, 17, 0, tzinfo=timezone.utc),
        timezone_name="America/Chicago",
        status="verified",
    )
    proposal = create_proposal(
        db,
        user_id=first_user.id,
        event_id=event.id,
        proposed_title="Quiz",
        proposed_due_at=datetime(2026, 9, 26, 17, 0, tzinfo=timezone.utc),
    )

    assert accept_proposal(db, user_id=second_user.id, proposal_id=proposal.id) is None
    assert proposal.status == "pending"

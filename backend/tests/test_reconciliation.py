from datetime import datetime

from app.schemas.events import (
    AcademicEvent,
    ChangeType,
    EventCandidate,
    EventStatus,
    EventType,
    EventVersion,
    SourceType,
)
from app.services.reconciliation import reconcile_candidate


def test_creates_new_event_when_no_match_exists():
    candidate = EventCandidate(
        course_id="cse-3310",
        type=EventType.QUIZ,
        title="Quiz 3",
        due_at=datetime.fromisoformat("2026-09-24T23:59:00-05:00"),
        source_id="announcement-1",
        source_excerpt="Quiz 3 is due Thursday.",
        change_type=ChangeType.NEW,
    )

    result = reconcile_candidate(
        candidate=candidate,
        candidate_source_type=SourceType.INSTRUCTOR_ANNOUNCEMENT,
        candidate_received_at=datetime.fromisoformat(
            "2026-09-12T09:00:00-05:00"
        ),
        events=[],
        source_types={},
        source_received_at={},
    )

    assert result.action == "created"
    assert result.event.title == "Quiz 3"
    assert result.event.due_at == candidate.due_at
    assert result.event.status == EventStatus.VERIFIED
    assert result.event.approved is False
    assert result.proposed_candidate is None


def test_proposes_change_from_newer_higher_priority_announcement():
    old_date = datetime.fromisoformat("2026-09-15T23:59:00-05:00")

    existing = AcademicEvent(
        id="event-quiz-2",
        course_id="cse-3310",
        type=EventType.QUIZ,
        title="Quiz 2",
        due_at=old_date,
        status=EventStatus.VERIFIED,
        approved=True,
        workload_minutes=90,
        source_id="syllabus-1",
        source_excerpt="Quiz 2 - Tuesday, September 15.",
        history=[
            EventVersion(
                due_at=old_date,
                source_id="syllabus-1",
                reason="Original deadline.",
                is_current=True,
            )
        ],
    )

    candidate = EventCandidate(
        course_id="cse-3310",
        type=EventType.QUIZ,
        title="Quiz 2",
        due_at=datetime.fromisoformat("2026-09-17T23:59:00-05:00"),
        source_id="announcement-1",
        source_excerpt="Quiz 2 has been moved to Thursday, September 17.",
        change_type=ChangeType.RESCHEDULED,
    )

    original_event = existing.model_copy(deep=True)
    original_candidate = candidate.model_copy(deep=True)

    result = reconcile_candidate(
        candidate=candidate,
        candidate_source_type=SourceType.INSTRUCTOR_ANNOUNCEMENT,
        candidate_received_at=datetime.fromisoformat(
            "2026-09-12T09:00:00-05:00"
        ),
        events=[existing],
        source_types={"syllabus-1": SourceType.SYLLABUS},
        source_received_at={
            "syllabus-1": datetime.fromisoformat(
                "2026-09-01T09:00:00-05:00"
            )
        },
    )

    assert result.action == "proposed_change"

    # Preserve the saved date, evidence, approval, and history.
    assert existing == original_event
    assert result.event == original_event
    assert candidate == original_candidate

    # Preserve the incoming information in a separate proposal.
    assert result.proposed_candidate is not None
    assert result.proposed_candidate == original_candidate
    assert result.proposed_candidate is not candidate
    assert "higher priority" in result.message

    # Editing the proposal must not change either original input.
    result.proposed_candidate.title = "Edited proposal"
    assert candidate == original_candidate
    assert existing == original_event


def test_proposes_change_when_lower_priority_source_conflicts():
    existing = AcademicEvent(
        id="event-quiz-2",
        course_id="cse-3310",
        type=EventType.QUIZ,
        title="Quiz 2",
        due_at=datetime.fromisoformat("2026-09-17T23:59:00-05:00"),
        status=EventStatus.VERIFIED,
        workload_minutes=90,
        source_id="canvas-1",
        source_excerpt="Due Sept. 17.",
    )

    candidate = EventCandidate(
        course_id="cse-3310",
        type=EventType.QUIZ,
        title="Quiz 2",
        due_at=datetime.fromisoformat("2026-09-15T23:59:00-05:00"),
        source_id="syllabus-1",
        source_excerpt="Quiz 2 - Tuesday, September 15.",
        change_type=ChangeType.UNKNOWN,
    )

    original_event = existing.model_copy(deep=True)
    original_candidate = candidate.model_copy(deep=True)

    result = reconcile_candidate(
        candidate=candidate,
        candidate_source_type=SourceType.SYLLABUS,
        candidate_received_at=datetime.fromisoformat(
            "2026-09-01T09:00:00-05:00"
        ),
        events=[existing],
        source_types={"canvas-1": SourceType.CANVAS_DUE_FIELD},
        source_received_at={
            "canvas-1": datetime.fromisoformat(
                "2026-09-12T09:00:00-05:00"
            )
        },
    )

    assert result.action == "proposed_change"
    assert existing == original_event
    assert result.event == original_event
    assert candidate == original_candidate
    assert result.proposed_candidate == original_candidate
    assert "lower priority" in result.message

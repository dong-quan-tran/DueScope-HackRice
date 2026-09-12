from datetime import datetime

from app.schemas.events import (
    AcademicEvent,
    ChangeType,
    EventCandidate,
    EventStatus,
    EventType,
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
        candidate_received_at=datetime.fromisoformat("2026-09-12T09:00:00-05:00"),
        events=[],
        source_types={},
        source_received_at={},
    )

    assert result.action == "created"
    assert result.event.title == "Quiz 3"
    assert result.event.status == EventStatus.VERIFIED


def test_updates_event_from_newer_higher_priority_announcement():
    existing = AcademicEvent(
        id="event-quiz-2",
        course_id="cse-3310",
        type=EventType.QUIZ,
        title="Quiz 2",
        due_at=datetime.fromisoformat("2026-09-15T23:59:00-05:00"),
        status=EventStatus.VERIFIED,
        workload_minutes=90,
        source_id="syllabus-1",
        source_excerpt="Quiz 2 — Tuesday, September 15.",
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

    result = reconcile_candidate(
        candidate=candidate,
        candidate_source_type=SourceType.INSTRUCTOR_ANNOUNCEMENT,
        candidate_received_at=datetime.fromisoformat("2026-09-12T09:00:00-05:00"),
        events=[existing],
        source_types={"syllabus-1": SourceType.SYLLABUS},
        source_received_at={
            "syllabus-1": datetime.fromisoformat("2026-09-01T09:00:00-05:00")
        },
    )

    assert result.action == "updated"
    assert result.event.status == EventStatus.UPDATED
    assert result.event.due_at == datetime.fromisoformat("2026-09-17T23:59:00-05:00")
    assert len(result.event.history) == 2
    assert result.event.history[0].due_at == datetime.fromisoformat(
        "2026-09-15T23:59:00-05:00"
    )
    assert result.event.history[0].is_current is False
    assert result.event.history[1].due_at == datetime.fromisoformat(
        "2026-09-17T23:59:00-05:00"
    )
    assert result.event.history[1].is_current is True


def test_marks_event_for_review_when_lower_priority_source_conflicts():
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
        source_excerpt="Quiz 2 — Tuesday, September 15.",
        change_type=ChangeType.UNKNOWN,
    )

    result = reconcile_candidate(
        candidate=candidate,
        candidate_source_type=SourceType.SYLLABUS,
        candidate_received_at=datetime.fromisoformat("2026-09-01T09:00:00-05:00"),
        events=[existing],
        source_types={"canvas-1": SourceType.CANVAS_DUE_FIELD},
        source_received_at={
            "canvas-1": datetime.fromisoformat("2026-09-12T09:00:00-05:00")
        },
    )

    assert result.action == "needs_review"
    assert result.event.status == EventStatus.NEEDS_REVIEW
    assert result.event.needs_review_reason is not None


def test_marks_matching_event_for_review_when_date_is_inferred():
    existing = AcademicEvent(
        id="event-assignment-2",
        course_id="cse-3310",
        type=EventType.ASSIGNMENT,
        title="Programming Assignment 2",
        due_at=datetime.fromisoformat("2026-09-18T23:59:00-05:00"),
        status=EventStatus.VERIFIED,
        workload_minutes=420,
        source_id="announcement-1",
        source_excerpt="Assignment 2 is due Friday.",
    )

    candidate = EventCandidate(
        course_id="cse-3310",
        type=EventType.ASSIGNMENT,
        title="Programming Assignment 2",
        due_at=datetime.fromisoformat("2026-09-18T23:59:00-05:00"),
        source_id="announcement-2",
        source_excerpt="Programming Assignment 2 is still due Friday.",
        change_type=ChangeType.UNCHANGED,
        needs_review_reason="The source uses a relative or inferred date. Review before calendar export.",
    )

    result = reconcile_candidate(
        candidate=candidate,
        candidate_source_type=SourceType.INSTRUCTOR_ANNOUNCEMENT,
        candidate_received_at=datetime.fromisoformat("2026-09-12T09:20:00-05:00"),
        events=[existing],
        source_types={"announcement-1": SourceType.INSTRUCTOR_ANNOUNCEMENT},
        source_received_at={
            "announcement-1": datetime.fromisoformat("2026-09-12T09:00:00-05:00")
        },
    )

    assert result.action == "needs_review"
    assert result.event.status == EventStatus.NEEDS_REVIEW
    assert result.event.needs_review_reason is not None


def test_update_preserves_existing_deadline_when_history_is_empty():
    existing = AcademicEvent(
        id="event-assignment-2",
        course_id="cse-3310",
        type=EventType.ASSIGNMENT,
        title="Programming Assignment 2",
        due_at=datetime.fromisoformat("2026-09-18T23:59:00-05:00"),
        status=EventStatus.VERIFIED,
        workload_minutes=420,
        source_id="announcement-original",
        source_excerpt="Programming Assignment 2 is due Friday at 11:59 PM.",
        history=[],
    )

    candidate = EventCandidate(
        course_id="cse-3310",
        type=EventType.ASSIGNMENT,
        title="Programming Assignment 2",
        due_at=datetime.fromisoformat("2026-09-21T23:59:00-05:00"),
        source_id="announcement-extension",
        source_excerpt="Programming Assignment 2 has been extended to Sept. 21.",
        change_type=ChangeType.EXTENDED,
    )

    result = reconcile_candidate(
        candidate=candidate,
        candidate_source_type=SourceType.INSTRUCTOR_ANNOUNCEMENT,
        candidate_received_at=datetime.fromisoformat("2026-09-12T11:30:00-05:00"),
        events=[existing],
        source_types={
            "announcement-original": SourceType.INSTRUCTOR_ANNOUNCEMENT
        },
        source_received_at={
            "announcement-original": datetime.fromisoformat(
                "2026-09-12T09:00:00-05:00"
            )
        },
    )

    assert result.action == "updated"
    assert len(result.event.history) == 2
    assert result.event.history[0].due_at == datetime.fromisoformat(
        "2026-09-18T23:59:00-05:00"
    )
    assert result.event.history[0].is_current is False
    assert result.event.history[1].due_at == datetime.fromisoformat(
        "2026-09-21T23:59:00-05:00"
    )
    assert result.event.history[1].is_current is True

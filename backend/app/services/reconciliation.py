import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.schemas.events import (
    AcademicEvent,
    EventCandidate,
    EventStatus,
    EventVersion,
    SourceType,
)

SOURCE_PRIORITY = {
    SourceType.CANVAS_DUE_FIELD: 100,
    SourceType.INSTRUCTOR_ANNOUNCEMENT: 90,
    SourceType.INSTRUCTOR_EMAIL: 85,
    SourceType.SYLLABUS: 60,
    SourceType.MANUAL_ENTRY: 30,
}


@dataclass
class ReconciliationResult:
    event: AcademicEvent
    action: str
    message: str


def normalize_title(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\b(the|a|an|due)\b", " ", value)
    return " ".join(value.split())


def find_matching_event(
    candidate: EventCandidate,
    events: list[AcademicEvent],
) -> Optional[AcademicEvent]:
    candidate_title = normalize_title(candidate.title)

    for event in events:
        if event.course_id != candidate.course_id:
            continue
        if event.type != candidate.type:
            continue
        if normalize_title(event.title) == candidate_title:
            return event

    return None


def mark_for_review(
    event: AcademicEvent,
    reason: str,
) -> ReconciliationResult:
    event.status = EventStatus.NEEDS_REVIEW
    event.needs_review_reason = reason

    return ReconciliationResult(
        event=event,
        action="needs_review",
        message=f"Marked {event.title} for review: {reason}",
    )


def ensure_current_history(event: AcademicEvent) -> None:
    if any(version.is_current for version in event.history):
        return

    event.history.append(
        EventVersion(
            due_at=event.due_at,
            source_id=event.source_id,
            reason="Previous current deadline preserved before update.",
            is_current=True,
        )
    )


def reconcile_candidate(
    candidate: EventCandidate,
    candidate_source_type: SourceType,
    candidate_received_at: datetime,
    events: list[AcademicEvent],
    source_types: dict[str, SourceType],
    source_received_at: dict[str, datetime],
) -> ReconciliationResult:
    existing = find_matching_event(candidate, events)

    if existing is None:
        event = AcademicEvent(
            id=f"event-{normalize_title(candidate.title).replace(' ', '-')}",
            course_id=candidate.course_id,
            type=candidate.type,
            title=candidate.title,
            starts_at=candidate.starts_at,
            due_at=candidate.due_at,
            status=(
                EventStatus.NEEDS_REVIEW
                if candidate.needs_review_reason
                else EventStatus.VERIFIED
            ),
            workload_minutes=0,
            source_id=candidate.source_id,
            source_excerpt=candidate.source_excerpt,
            needs_review_reason=candidate.needs_review_reason,
            history=[
                EventVersion(
                    due_at=candidate.due_at,
                    source_id=candidate.source_id,
                    reason="New deadline discovered from source",
                    is_current=True,
                )
            ],
        )
        return ReconciliationResult(
            event=event,
            action=(
                "needs_review"
                if candidate.needs_review_reason
                else "created"
            ),
            message=(
                f"Created {event.title}, but it needs review: "
                f"{candidate.needs_review_reason}"
                if candidate.needs_review_reason
                else f"Created new event: {event.title}."
            ),
        )

    if candidate.needs_review_reason:
        return mark_for_review(existing, candidate.needs_review_reason)

    existing_source_type = source_types.get(
        existing.source_id,
        SourceType.MANUAL_ENTRY,
    )
    existing_source_time = source_received_at.get(
        existing.source_id,
        datetime.min,
    )

    incoming_priority = SOURCE_PRIORITY[candidate_source_type]
    existing_priority = SOURCE_PRIORITY[existing_source_type]

    has_new_due_date = candidate.due_at != existing.due_at
    incoming_is_newer = candidate_received_at >= existing_source_time
    incoming_is_stronger = incoming_priority >= existing_priority

    if not has_new_due_date:
        return ReconciliationResult(
            event=existing,
            action="unchanged",
            message=f"No deadline change detected for {existing.title}.",
        )

    if incoming_is_newer and incoming_is_stronger:
        ensure_current_history(existing)

        for version in existing.history:
            version.is_current = False

        existing.history.append(
            EventVersion(
                due_at=candidate.due_at,
                source_id=candidate.source_id,
                reason=f"Updated by {candidate_source_type.value}.",
                is_current=True,
            )
        )
        existing.starts_at = candidate.starts_at or existing.starts_at
        existing.due_at = candidate.due_at
        existing.source_id = candidate.source_id
        existing.source_excerpt = candidate.source_excerpt
        existing.status = EventStatus.UPDATED
        existing.needs_review_reason = None

        return ReconciliationResult(
            event=existing,
            action="updated",
            message=f"Updated {existing.title} with a newer trusted source.",
        )

    return mark_for_review(
        existing,
        (
            "A source reports a different deadline, but DueScope cannot "
            "safely determine which source should take precedence."
        ),
    )

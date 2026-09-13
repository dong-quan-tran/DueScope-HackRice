import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

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
    proposed_candidate: Optional[EventCandidate] = None


def normalize_title(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\b(the|a|an|due)\b", " ", value)
    return " ".join(value.split())


def has_timezone(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def find_matching_event(
    candidate: EventCandidate,
    events: list[AcademicEvent],
) -> Optional[AcademicEvent]:
    candidate_title = normalize_title(candidate.title)

    if not candidate_title:
        return None

    for event in events:
        if event.course_id != candidate.course_id:
            continue
        if event.type != candidate.type:
            continue
        if normalize_title(event.title) == candidate_title:
            return event

    return None


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


def apply_accepted_proposal(
    event: AcademicEvent,
    proposal: EventCandidate,
) -> AcademicEvent:
    """Return an updated event after a user explicitly accepts a proposal."""
    updated = event.model_copy(deep=True)

    ensure_current_history(updated)

    for version in updated.history:
        version.is_current = False

    updated.history.append(
        EventVersion(
            due_at=proposal.due_at,
            source_id=proposal.source_id,
            reason="Accepted proposed deadline change after review.",
            is_current=True,
        )
    )

    updated.title = proposal.title
    updated.starts_at = proposal.starts_at
    updated.due_at = proposal.due_at
    updated.source_id = proposal.source_id
    updated.source_excerpt = proposal.source_excerpt
    updated.status = EventStatus.UPDATED
    updated.approved = False
    updated.needs_review_reason = None

    return updated


def reconcile_candidate(
    candidate: EventCandidate,
    candidate_source_type: SourceType,
    candidate_received_at: datetime,
    events: list[AcademicEvent],
    source_types: dict[str, SourceType],
    source_received_at: dict[str, datetime],
) -> ReconciliationResult:
    """Compare one candidate to canonical events without mutating inputs."""
    proposed = candidate.model_copy(deep=True)
    warnings: list[str] = []

    if proposed.needs_review_reason:
        warnings.append(proposed.needs_review_reason)

    if not proposed.title.strip():
        warnings.append("Title is missing or blank.")

    if not proposed.source_excerpt.strip():
        warnings.append("Source excerpt is missing or blank.")

    if proposed.due_at is None:
        warnings.append("The deadline is missing.")
    elif not has_timezone(proposed.due_at):
        warnings.append("The deadline must include timezone information.")

    proposed.needs_review_reason = " | ".join(warnings) if warnings else None

    existing = find_matching_event(proposed, events)

    if existing is None:
        event = AcademicEvent(
            id=f"event-{uuid4()}",
            course_id=proposed.course_id,
            type=proposed.type,
            title=proposed.title,
            starts_at=proposed.starts_at,
            due_at=proposed.due_at,
            status=EventStatus.NEEDS_REVIEW if warnings else EventStatus.VERIFIED,
            approved=False,
            workload_minutes=0,
            source_id=proposed.source_id,
            source_excerpt=proposed.source_excerpt,
            needs_review_reason=proposed.needs_review_reason,
            history=[
                EventVersion(
                    due_at=proposed.due_at,
                    source_id=proposed.source_id,
                    reason="New deadline discovered from source.",
                    is_current=True,
                )
            ],
        )

        message = f"Created new event: {event.title}."
        if warnings:
            message += f" Review needed: {proposed.needs_review_reason}"

        return ReconciliationResult(
            event=event,
            action="created",
            message=message,
        )

    reasons: list[str] = []

    if existing.needs_review_reason:
        reasons.append(f"Existing warning: {existing.needs_review_reason}")

    if proposed.needs_review_reason:
        reasons.append(f"Incoming warning: {proposed.needs_review_reason}")

    if proposed.due_at == existing.due_at:
        if reasons:
            return ReconciliationResult(
                event=existing,
                action="needs_review",
                message=(
                    "The deadline is unchanged, but review is needed. "
                    + " ".join(reasons)
                ),
                proposed_candidate=proposed,
            )

        return ReconciliationResult(
            event=existing,
            action="unchanged",
            message=f"No deadline change detected for {existing.title}.",
        )

    if proposed.due_at is None or not has_timezone(proposed.due_at):
        return ReconciliationResult(
            event=existing,
            action="needs_review",
            message=(
                "The incoming deadline needs correction. "
                + " ".join(reasons)
                + " The saved event was not changed."
            ),
            proposed_candidate=proposed,
        )

    existing_source_type = source_types.get(existing.source_id)
    incoming_priority = SOURCE_PRIORITY.get(candidate_source_type)
    existing_priority = SOURCE_PRIORITY.get(existing_source_type)

    if incoming_priority is None or existing_priority is None:
        reasons.append("Source priority could not be fully determined.")
    elif incoming_priority > existing_priority:
        reasons.append("The incoming source has higher priority.")
    elif incoming_priority == existing_priority:
        reasons.append("The sources have equal priority.")
    else:
        reasons.append("The incoming source has lower priority.")

    existing_source_time = source_received_at.get(existing.source_id)

    if existing_source_time is None:
        reasons.append("The existing source's received time is unknown.")
    elif (
        not has_timezone(candidate_received_at)
        or not has_timezone(existing_source_time)
    ):
        reasons.append(
            "Source timing cannot be compared because timezone information is missing."
        )
    elif candidate_received_at > existing_source_time:
        reasons.append("The incoming source was received more recently.")
    elif candidate_received_at == existing_source_time:
        reasons.append("Both sources have the same received time.")
    else:
        reasons.append("The incoming source was received earlier.")

    return ReconciliationResult(
        event=existing,
        action="proposed_change",
        message=(
            f"A different deadline was found for {existing.title}. "
            + " ".join(reasons)
            + " Review the suggestion before accepting it. "
            "The saved event was not changed."
        ),
        proposed_candidate=proposed,
    )


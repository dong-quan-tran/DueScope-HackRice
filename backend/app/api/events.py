from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.demo import DEMO_WORKSPACE
from app.schemas.events import (
    AcademicEvent,
    DeadlineProposal,
    EventCandidate,
    SourceType,
)
from app.services.reconciliation import (
    apply_accepted_proposal,
    reconcile_candidate,
)

router = APIRouter(prefix="/events", tags=["events"])


class ReconcileRequest(BaseModel):
    candidate: EventCandidate
    source_type: SourceType
    source_received_at: datetime


class ApprovalRequest(BaseModel):
    approved: bool


def source_maps() -> tuple[dict[str, SourceType], dict[str, datetime]]:
    source_types = {
        source["id"]: SourceType(source["type"])
        for source in DEMO_WORKSPACE["sources"]
    }
    source_received_at = {
        source["id"]: datetime.fromisoformat(source["received_at"])
        for source in DEMO_WORKSPACE["sources"]
    }
    return source_types, source_received_at


def store_proposal(
    event_id: str,
    candidate: EventCandidate,
    message: str,
) -> DeadlineProposal:
    for stored in DEMO_WORKSPACE["proposals"]:
        proposal = DeadlineProposal.model_validate(stored)

        if (
            not proposal.resolved
            and proposal.event_id == event_id
            and proposal.candidate.source_id == candidate.source_id
            and proposal.candidate.due_at == candidate.due_at
        ):
            return proposal

    proposal = DeadlineProposal(
        id=f"proposal-{uuid4().hex}",
        event_id=event_id,
        candidate=candidate.model_copy(deep=True),
        message=message,
        created_at=datetime.now(timezone.utc),
    )

    DEMO_WORKSPACE["proposals"].append(proposal.model_dump(mode="json"))
    return proposal


def persist_created_event(event: AcademicEvent) -> None:
    DEMO_WORKSPACE["events"].append(event.model_dump(mode="json"))


@router.get("")
def list_events() -> list[AcademicEvent]:
    return [
        AcademicEvent.model_validate(event)
        for event in DEMO_WORKSPACE["events"]
    ]


@router.get("/{event_id}")
def get_event(event_id: str) -> AcademicEvent:
    for event in DEMO_WORKSPACE["events"]:
        if event["id"] == event_id:
            return AcademicEvent.model_validate(event)

    raise HTTPException(status_code=404, detail="Event not found")


@router.patch("/{event_id}/approval")
def set_event_approval(event_id: str, request: ApprovalRequest) -> AcademicEvent:
    for event in DEMO_WORKSPACE["events"]:
        if event["id"] == event_id:
            if event["status"] not in {"verified", "updated"}:
                raise HTTPException(
                    status_code=400,
                    detail="Only verified or updated events can be approved.",
                )

            event["approved"] = request.approved
            return AcademicEvent.model_validate(event)

    raise HTTPException(status_code=404, detail="Event not found")


@router.get("/proposals/pending")
def list_pending_proposals() -> list[DeadlineProposal]:
    return [
        DeadlineProposal.model_validate(proposal)
        for proposal in DEMO_WORKSPACE["proposals"]
        if not proposal.get("resolved", False)
    ]


@router.post("/proposals/{proposal_id}/accept")
def accept_proposal(proposal_id: str) -> AcademicEvent:
    proposal_index = next(
        (
            index
            for index, proposal in enumerate(DEMO_WORKSPACE["proposals"])
            if proposal["id"] == proposal_id
        ),
        None,
    )

    if proposal_index is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal = DeadlineProposal.model_validate(
        DEMO_WORKSPACE["proposals"][proposal_index]
    )

    if proposal.resolved:
        raise HTTPException(
            status_code=400,
            detail="Proposal has already been resolved.",
        )

    event_index = next(
        (
            index
            for index, event in enumerate(DEMO_WORKSPACE["events"])
            if event["id"] == proposal.event_id
        ),
        None,
    )

    if event_index is None:
        raise HTTPException(
            status_code=404,
            detail="Event for proposal not found",
        )

    existing_event = AcademicEvent.model_validate(
        DEMO_WORKSPACE["events"][event_index]
    )

    updated_event = apply_accepted_proposal(
        existing_event,
        proposal.candidate,
    )

    DEMO_WORKSPACE["events"][event_index] = updated_event.model_dump(mode="json")

    proposal.resolved = True
    proposal.resolution = "accepted"
    DEMO_WORKSPACE["proposals"][proposal_index] = proposal.model_dump(mode="json")

    return updated_event


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: str) -> DeadlineProposal:
    proposal_index = next(
        (
            index
            for index, proposal in enumerate(DEMO_WORKSPACE["proposals"])
            if proposal["id"] == proposal_id
        ),
        None,
    )

    if proposal_index is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal = DeadlineProposal.model_validate(
        DEMO_WORKSPACE["proposals"][proposal_index]
    )

    if proposal.resolved:
        raise HTTPException(
            status_code=400,
            detail="Proposal has already been resolved.",
        )

    proposal.resolved = True
    proposal.resolution = "rejected"
    DEMO_WORKSPACE["proposals"][proposal_index] = proposal.model_dump(mode="json")

    return proposal


@router.post("/reconcile")
def reconcile_event(request: ReconcileRequest) -> dict:
    events = [
        AcademicEvent.model_validate(event)
        for event in DEMO_WORKSPACE["events"]
    ]

    source_types, source_received_at = source_maps()

    result = reconcile_candidate(
        candidate=request.candidate,
        candidate_source_type=request.source_type,
        candidate_received_at=request.source_received_at,
        events=events,
        source_types=source_types,
        source_received_at=source_received_at,
    )

    proposal = None

    if result.action == "created":
        persist_created_event(result.event)
    elif result.proposed_candidate is not None:
        proposal = store_proposal(
            event_id=result.event.id,
            candidate=result.proposed_candidate,
            message=result.message,
        )

    return {
        "action": result.action,
        "message": result.message,
        "event": result.event.model_dump(mode="json"),
        "proposed_candidate": (
            result.proposed_candidate.model_dump(mode="json")
            if result.proposed_candidate is not None
            else None
        ),
        "proposal": proposal.model_dump(mode="json") if proposal else None,
    }

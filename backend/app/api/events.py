from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.demo import DEMO_WORKSPACE
from app.schemas.events import AcademicEvent, EventCandidate, SourceType
from app.services.reconciliation import reconcile_candidate

router = APIRouter(prefix="/events", tags=["events"])


class ReconcileRequest(BaseModel):
    candidate: EventCandidate
    source_type: SourceType
    source_received_at: datetime


class ApprovalRequest(BaseModel):
    approved: bool


@router.get("")
def list_events() -> list[AcademicEvent]:
    return [AcademicEvent.model_validate(event) for event in DEMO_WORKSPACE["events"]]


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


@router.post("/reconcile")
def reconcile_event(request: ReconcileRequest) -> dict:
    events = [AcademicEvent.model_validate(event) for event in DEMO_WORKSPACE["events"]]

    source_types = {
        source["id"]: SourceType(source["type"])
        for source in DEMO_WORKSPACE["sources"]
    }
    source_received_at = {
        source["id"]: datetime.fromisoformat(source["received_at"])
        for source in DEMO_WORKSPACE["sources"]
    }

    result = reconcile_candidate(
        candidate=request.candidate,
        candidate_source_type=request.source_type,
        candidate_received_at=request.source_received_at,
        events=events,
        source_types=source_types,
        source_received_at=source_received_at,
    )

    existing_index = next(
        (
            index
            for index, event in enumerate(DEMO_WORKSPACE["events"])
            if event["id"] == result.event.id
        ),
        None,
    )

    event_payload = result.event.model_dump(mode="json")

    if existing_index is None:
        DEMO_WORKSPACE["events"].append(event_payload)
    else:
        DEMO_WORKSPACE["events"][existing_index] = event_payload

    return {
        "action": result.action,
        "message": result.message,
        "event": event_payload,
    }

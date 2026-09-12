from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.demo import DEMO_WORKSPACE
from app.schemas.events import ChangeType, EventCandidate, SourceType
from app.schemas.extraction import ExtractDeadlineRequest, ExtractionResponse
from app.services.gemini_extraction import extract_deadlines
from app.services.reconciliation import reconcile_candidate

router = APIRouter(prefix="/sources", tags=["sources"])


class ReconciledExtractionItem(BaseModel):
    title: str
    action: str
    message: str
    event_id: str


class ExtractAndReconcileResponse(BaseModel):
    source_id: str
    extraction: ExtractionResponse
    results: list[ReconciledExtractionItem]


def to_source_type(value: str) -> SourceType:
    return SourceType(value)


@router.post("/extract", response_model=ExtractionResponse)
def extract_source_deadlines(request: ExtractDeadlineRequest) -> ExtractionResponse:
    try:
        return extract_deadlines(request)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini extraction failed: {error}",
        ) from error


@router.post("/extract-and-reconcile", response_model=ExtractAndReconcileResponse)
def extract_and_reconcile(
    request: ExtractDeadlineRequest,
) -> ExtractAndReconcileResponse:
    try:
        extraction = extract_deadlines(request)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini extraction failed: {error}",
        ) from error

    source_id = f"source-import-{uuid4().hex[:8]}"
    source_type = to_source_type(request.source_type.value)

    DEMO_WORKSPACE["sources"].append(
        {
            "id": source_id,
            "course_id": request.course_id,
            "type": source_type.value,
            "title": request.source_title,
            "received_at": request.source_received_at.isoformat(),
            "raw_text": request.source_text,
        }
    )

    events = [
        event
        for event in DEMO_WORKSPACE["events"]
    ]
    source_types = {
        source["id"]: SourceType(source["type"])
        for source in DEMO_WORKSPACE["sources"]
    }
    source_received_at = {
        source["id"]: datetime.fromisoformat(source["received_at"])
        for source in DEMO_WORKSPACE["sources"]
    }

    results: list[ReconciledExtractionItem] = []

    for extracted in extraction.events:
        needs_review_reason = (
            "; ".join(extracted.uncertainties)
            if extracted.uncertainties
            else None
        )

        candidate = EventCandidate(
            course_id=request.course_id,
            type=extracted.event_type,
            title=extracted.title,
            starts_at=extracted.starts_at,
            due_at=extracted.due_at,
            source_id=source_id,
            source_excerpt=extracted.source_excerpt,
            change_type=extracted.change_type,
            confidence=extracted.confidence,
            needs_review_reason=needs_review_reason,
        )

        result = reconcile_candidate(
            candidate=candidate,
            candidate_source_type=source_type,
            candidate_received_at=request.source_received_at,
            events=[
                __import__(
                    "app.schemas.events",
                    fromlist=["AcademicEvent"],
                ).AcademicEvent.model_validate(event)
                for event in events
            ],
            source_types=source_types,
            source_received_at=source_received_at,
        )

        payload = result.event.model_dump(mode="json")
        existing_index = next(
            (
                index
                for index, event in enumerate(DEMO_WORKSPACE["events"])
                if event["id"] == result.event.id
            ),
            None,
        )

        if existing_index is None:
            DEMO_WORKSPACE["events"].append(payload)
            events.append(payload)
        else:
            DEMO_WORKSPACE["events"][existing_index] = payload
            events[existing_index] = payload

        results.append(
            ReconciledExtractionItem(
                title=extracted.title,
                action=result.action,
                message=result.message,
                event_id=result.event.id,
            )
        )

    return ExtractAndReconcileResponse(
        source_id=source_id,
        extraction=extraction,
        results=results,
    )

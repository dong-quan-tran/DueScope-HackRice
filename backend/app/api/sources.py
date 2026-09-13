from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.demo import DEMO_WORKSPACE
from app.api.events import source_maps, store_proposal
from app.schemas.events import AcademicEvent, EventCandidate, SourceType
from app.schemas.extraction import ExtractDeadlineRequest, ExtractionResponse
from app.services.deadline_validation import validate_candidate
from app.services.gemini_extraction import extract_deadlines
from app.services.reconciliation import reconcile_candidate

router = APIRouter(prefix="/sources", tags=["sources"])


class ReconciledExtractionItem(BaseModel):
    title: str
    action: str
    message: str
    event_id: str
    proposal_id: str | None = None


class ExtractAndReconcileResponse(BaseModel):
    source_id: str
    extraction: ExtractionResponse
    results: list[ReconciledExtractionItem]


def to_source_type(value: str) -> SourceType:
    if value == "other":
        return SourceType.MANUAL_ENTRY

    return SourceType(value)


def run_extraction(request: ExtractDeadlineRequest) -> ExtractionResponse:
    try:
        return extract_deadlines(request)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini extraction failed: {error}",
        ) from error


@router.post("/extract", response_model=ExtractionResponse)
def extract_source_deadlines(
    request: ExtractDeadlineRequest,
) -> ExtractionResponse:
    return run_extraction(request)


@router.post(
    "/extract-and-reconcile",
    response_model=ExtractAndReconcileResponse,
)
def extract_and_reconcile(
    request: ExtractDeadlineRequest,
) -> ExtractAndReconcileResponse:
    extraction = run_extraction(request)

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

    results: list[ReconciledExtractionItem] = []

    for extracted in extraction.events:
        raw_candidate = {
            "course_id": request.course_id,
            "type": extracted.event_type.value,
            "title": extracted.title,
            "starts_at": (
                extracted.starts_at.isoformat()
                if extracted.starts_at
                else None
            ),
            "due_at": (
                extracted.due_at.isoformat()
                if extracted.due_at
                else None
            ),
            "source_id": source_id,
            "source_excerpt": extracted.source_excerpt,
            "change_type": extracted.change_type.value,
            "confidence": extracted.confidence,
            "needs_review_reason": (
                " | ".join(extracted.uncertainties)
                if extracted.uncertainties
                else None
            ),
        }

        validation = validate_candidate(
            raw_candidate,
            request.source_text,
        )
        candidate_data = validation["candidate"]

        validation_reason = " | ".join(validation["issues"])
        existing_reason = candidate_data.get("needs_review_reason")
        reasons = [
            reason
            for reason in (existing_reason, validation_reason)
            if reason
        ]
        candidate_data["needs_review_reason"] = " | ".join(reasons) or None

        try:
            candidate = EventCandidate.model_validate(candidate_data)
        except Exception as error:
            raise HTTPException(
                status_code=422,
                detail=f"Extracted deadline candidate is invalid: {error}",
            ) from error

        events = [
            AcademicEvent.model_validate(event)
            for event in DEMO_WORKSPACE["events"]
        ]
        source_types, source_received_at = source_maps()

        result = reconcile_candidate(
            candidate=candidate,
            candidate_source_type=source_type,
            candidate_received_at=request.source_received_at,
            events=events,
            source_types=source_types,
            source_received_at=source_received_at,
        )

        proposal_id = None

        if result.action == "created":
            DEMO_WORKSPACE["events"].append(
                result.event.model_dump(mode="json")
            )
        elif result.proposed_candidate is not None:
            proposal = store_proposal(
                event_id=result.event.id,
                candidate=result.proposed_candidate,
                message=result.message,
            )
            proposal_id = proposal.id

        results.append(
            ReconciledExtractionItem(
                title=extracted.title,
                action=result.action,
                message=result.message,
                event_id=result.event.id,
                proposal_id=proposal_id,
            )
        )

    return ExtractAndReconcileResponse(
        source_id=source_id,
        extraction=extraction,
        results=results,
    )

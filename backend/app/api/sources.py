from fastapi import APIRouter, HTTPException

from app.schemas.extraction import ExtractDeadlineRequest, ExtractionResponse
from app.services.gemini_extraction import extract_deadlines

router = APIRouter(prefix="/sources", tags=["sources"])


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

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.events import ChangeType, EventType


class ExtractionSourceType(str, Enum):
    SYLLABUS = "syllabus"
    CANVAS_ANNOUNCEMENT = "instructor_announcement"
    INSTRUCTOR_EMAIL = "instructor_email"
    OTHER = "other"


class ExtractDeadlineRequest(BaseModel):
    course_id: str = Field(min_length=1)
    source_type: ExtractionSourceType
    source_title: str = Field(min_length=1, max_length=200)
    source_text: str = Field(min_length=1, max_length=30000)
    source_received_at: datetime
    timezone: str = "America/Chicago"


class ExtractedEvent(BaseModel):
    event_type: EventType
    title: str = Field(min_length=1, max_length=200)
    change_type: ChangeType = ChangeType.UNKNOWN
    starts_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    location: Optional[str] = None
    workload_estimate_minutes: Optional[int] = Field(default=None, ge=0)
    date_is_explicit: bool
    source_excerpt: str = Field(min_length=1, max_length=1000)
    uncertainties: list[str] = Field(default_factory=list)
    confidence: str = Field(pattern="^(high|medium|low)$")

    @model_validator(mode="after")
    def require_review_for_non_explicit_dates(self) -> "ExtractedEvent":
        if not self.date_is_explicit and (self.starts_at or self.due_at):
            message = (
                "The source uses a relative or inferred date. "
                "Review before calendar export."
            )
            if message not in self.uncertainties:
                self.uncertainties.append(message)
            if self.confidence == "high":
                self.confidence = "medium"
        return self


class ExtractionResponse(BaseModel):
    source_summary: str
    events: list[ExtractedEvent] = Field(default_factory=list)
    no_deadline_content: bool = False
    provider: str = ""
    used_demo_fallback: bool = False

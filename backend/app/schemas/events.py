from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    SYLLABUS = "syllabus"
    CANVAS_DUE_FIELD = "canvas_due_field"
    INSTRUCTOR_ANNOUNCEMENT = "instructor_announcement"
    INSTRUCTOR_EMAIL = "instructor_email"
    MANUAL_ENTRY = "manual_entry"


class EventType(str, Enum):
    ASSIGNMENT = "assignment"
    QUIZ = "quiz"
    EXAM = "exam"
    LAB = "lab"
    PROJECT = "project"
    REVIEW = "review"
    OTHER = "other"


class EventStatus(str, Enum):
    VERIFIED = "verified"
    UPDATED = "updated"
    NEEDS_REVIEW = "needs_review"
    CANCELED = "canceled"


class ChangeType(str, Enum):
    NEW = "new"
    RESCHEDULED = "rescheduled"
    EXTENDED = "extended"
    CANCELED = "canceled"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"


class Course(BaseModel):
    id: str
    code: str
    name: str
    color: str


class Source(BaseModel):
    id: str
    course_id: str
    type: SourceType
    title: str
    received_at: datetime
    raw_text: Optional[str] = None
    source_url: Optional[str] = None


class EventVersion(BaseModel):
    due_at: Optional[datetime] = None
    source_id: str
    reason: str
    is_current: bool


class AcademicEvent(BaseModel):
    id: str
    course_id: str
    type: EventType
    title: str
    starts_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    location: Optional[str] = None
    status: EventStatus
    approved: bool = False
    workload_minutes: int = Field(ge=0)
    source_id: str
    source_excerpt: str
    needs_review_reason: Optional[str] = None
    history: list[EventVersion] = Field(default_factory=list)


class Change(BaseModel):
    event_id: str
    kind: ChangeType
    message: str


class WorkloadDay(BaseModel):
    date: str
    minutes: int = Field(ge=0)
    level: str
    reason: str


class DemoWorkspace(BaseModel):
    student: dict[str, str]
    courses: list[Course]
    sources: list[Source]
    events: list[AcademicEvent]
    changes: list[Change]
    workload: list[WorkloadDay]


class EventCandidate(BaseModel):
    course_id: str
    type: EventType
    title: str
    starts_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    source_id: str
    source_excerpt: str
    change_type: ChangeType = ChangeType.UNKNOWN
    confidence: str = "medium"
    needs_review_reason: Optional[str] = None

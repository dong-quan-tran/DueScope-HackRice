"""Persistent domain models for DueScope."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class TimestampedModel:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class User(TimestampedModel, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(160))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    courses: Mapped[list[Course]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sources: Mapped[list[Source]] = relationship(back_populates="user", cascade="all, delete-orphan")
    academic_events: Mapped[list[AcademicEvent]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    academic_proposals: Mapped[list[AcademicProposal]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    job_applications: Mapped[list[JobApplication]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    job_calendar_proposals: Mapped[list[JobCalendarProposal]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    oauth_credentials: Mapped[list[OAuthCredential]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    app_sessions: Mapped[list[AppSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    oauth_transactions: Mapped[list[OAuthTransaction]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AppSession(Base):
    __tablename__ = "app_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    session_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="app_sessions")


class OAuthTransaction(Base):
    __tablename__ = "oauth_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False, default="connect")
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    encrypted_code_verifier: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="oauth_transactions")

class Course(TimestampedModel, Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("user_id", "external_id", name="uq_courses_user_external_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="courses")
    events: Mapped[list[AcademicEvent]] = relationship(back_populates="course")


class Source(TimestampedModel, Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="sources")
    events: Mapped[list[AcademicEvent]] = relationship(back_populates="source")


class AcademicEvent(TimestampedModel, Base):
    __tablename__ = "academic_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    timezone_name: Mapped[str] = mapped_column(String(100), default="America/Chicago", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="verified", nullable=False)
    calendar_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    calendar_event_id: Mapped[str | None] = mapped_column(String(255))
    calendar_event_url: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="academic_events")
    course: Mapped[Course | None] = relationship(back_populates="events")
    source: Mapped[Source | None] = relationship(back_populates="events")
    history: Mapped[list[AcademicEventHistory]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="AcademicEventHistory.changed_at",
    )
    proposals: Mapped[list[AcademicProposal]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )


class AcademicEventHistory(Base):
    __tablename__ = "academic_event_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(ForeignKey("academic_events.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    event: Mapped[AcademicEvent] = relationship(back_populates="history")


class AcademicProposal(TimestampedModel, Base):
    __tablename__ = "academic_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("academic_events.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), index=True)
    proposed_title: Mapped[str] = mapped_column(String(500), nullable=False)
    proposed_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="academic_proposals")
    event: Mapped[AcademicEvent] = relationship(back_populates="proposals")


class JobApplication(TimestampedModel, Base):
    __tablename__ = "job_applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    gmail_message_id: Mapped[str | None] = mapped_column(String(255), index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    next_action: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="job_applications")
    history: Mapped[list[JobHistory]] = relationship(
        back_populates="job_application",
        cascade="all, delete-orphan",
    )
    calendar_proposals: Mapped[list[JobCalendarProposal]] = relationship(
        back_populates="job_application",
        cascade="all, delete-orphan",
    )


class JobHistory(Base):
    __tablename__ = "job_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_application_id: Mapped[str] = mapped_column(
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    job_application: Mapped[JobApplication] = relationship(back_populates="history")


class JobCalendarProposal(TimestampedModel, Base):
    __tablename__ = "job_calendar_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_application_id: Mapped[str] = mapped_column(
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    calendar_event_id: Mapped[str | None] = mapped_column(String(255))
    calendar_event_url: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="job_calendar_proposals")
    job_application: Mapped[JobApplication] = relationship(back_populates="calendar_proposals")


class CalendarSyncRecord(Base):
    __tablename__ = "calendar_sync_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    local_record_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    calendar_event_id: Mapped[str | None] = mapped_column(String(255))
    calendar_event_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class OAuthState(Base):
    __tablename__ = "oauth_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    encrypted_code_verifier: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

class OAuthCredential(TimestampedModel, Base):
    __tablename__ = "oauth_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_oauth_credentials_user_provider"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted_token: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="oauth_credentials")


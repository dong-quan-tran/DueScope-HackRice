from __future__ import annotations

import base64
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any
from urllib.parse import quote_plus
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from app.api.demo import DEMO_WORKSPACE
from app.api.google import upsert_job_calendar_event
from app.services.google_oauth import get_credentials


router = APIRouter(prefix="/jobs", tags=["jobs"])


DEFAULT_JOB_QUERY = (
    "newer_than:14d in:inbox "
    "-from:linkedin.com "
    "-from:chase.com "
    "-from:americanexpress.com "
    "-from:salliemae.com "
    "-from:seaworldparks.com "
    "("
    "from:greenhouse.io OR "
    "from:lever.co OR "
    "from:ashbyhq.com OR "
    "from:workday.com OR "
    "from:myworkday.com OR "
    "from:smartrecruiters.com OR "
    "from:icims.com OR "
    "from:jobvite.com OR "
    "from:successfactors.com OR "
    "from:recruiting.com"
    ")"
)


class JobScanRequest(BaseModel):
    query: str = Field(
        default=DEFAULT_JOB_QUERY,
        min_length=1,
        max_length=500,
        description=(
            "Gmail query used to find recruiting messages. The default scans "
            "the previous 14 days from common recruiting-system sender domains."
        ),
    )
    max_results: int = Field(
        default=25,
        ge=1,
        le=50,
        description="Maximum number of job-related messages to inspect.",
    )


class JobApplicationUpdateRequest(BaseModel):
    company: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=250)
    status: str | None = Field(default=None, max_length=50)
    next_action: str | None = Field(default=None, max_length=500)
    requires_review: bool | None = None


VALID_STATUSES = {
    "application_received",
    "online_assessment",
    "recruiter_screen",
    "phone_screen",
    "technical_interview",
    "onsite_interview",
    "final_interview",
    "offer",
    "rejected",
    "unknown",
}


STATUS_PRIORITY = {
    "unknown": 0,
    "application_received": 1,
    "online_assessment": 2,
    "recruiter_screen": 3,
    "phone_screen": 4,
    "technical_interview": 5,
    "onsite_interview": 6,
    "final_interview": 7,
    "offer": 8,
    "rejected": 9,
}


def decode_base64url(value: str) -> str:
    padding = "=" * (-len(value) % 4)

    return base64.urlsafe_b64decode(value + padding).decode(
        "utf-8",
        errors="replace",
    )


def html_to_text(value: str) -> str:
    without_scripts = re.sub(
        r"(?is)<(script|style).*?>.*?</\1>",
        " ",
        value,
    )
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_scripts)

    return re.sub(r"\s+", " ", unescape(without_tags)).strip()


def extract_text_parts(payload: dict[str, Any]) -> list[str]:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime_type == "text/plain" and body_data:
        return [decode_base64url(body_data)]

    plain_parts: list[str] = []
    html_parts: list[str] = []

    for part in payload.get("parts", []):
        part_mime_type = part.get("mimeType", "")
        part_data = part.get("body", {}).get("data")

        if part_mime_type == "text/plain" and part_data:
            plain_parts.append(decode_base64url(part_data))
            continue

        if part_mime_type == "text/html" and part_data:
            html_parts.append(html_to_text(decode_base64url(part_data)))
            continue

        plain_parts.extend(extract_text_parts(part))

    if plain_parts:
        return plain_parts

    if mime_type == "text/html" and body_data:
        return [html_to_text(decode_base64url(body_data))]

    return html_parts


def header_value(headers: list[dict[str, str]], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")

    return ""


def sender_email(sender: str) -> str:
    match = re.search(r"<([^>]+)>", sender)

    if match:
        return match.group(1).strip()

    fallback = re.search(r"[\w.+-]+@[\w.-]+\.\w+", sender)

    return fallback.group(0) if fallback else sender.strip()


def gmail_search_url(sender: str, subject: str) -> str:
    email_address = sender_email(sender)
    query = f'from:{email_address} subject:"{subject}"'

    return f"https://mail.google.com/mail/u/0/#search/{quote_plus(query)}"


def message_received_at(message: dict[str, Any]) -> datetime:
    headers = message.get("payload", {}).get("headers", [])
    raw_date = header_value(headers, "Date")

    if raw_date:
        try:
            received_at = parsedate_to_datetime(raw_date)

            if received_at.tzinfo is None:
                return received_at.replace(tzinfo=timezone.utc)

            return received_at
        except (TypeError, ValueError, IndexError):
            pass

    internal_date = message.get("internalDate")

    if internal_date:
        return datetime.fromtimestamp(
            int(internal_date) / 1000,
            tz=timezone.utc,
        )

    return datetime.now(timezone.utc)


def cleaned_message_text(payload: dict[str, Any]) -> str:
    parts = extract_text_parts(payload)
    text = "\n\n".join(part.strip() for part in parts if part.strip())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text[:12000]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def classify_job_status(subject: str, body: str) -> tuple[str, str]:
    text = normalize_text(f"{subject}\n{body}").lower()

    rejection_phrases = (
        "we regret to inform you",
        "will not be moving forward",
        "not moving forward",
        "decided not to move forward",
        "decided to move forward with other candidates",
        "proceed with other applicants",
        "proceed with other candidates",
        "cannot offer you",
        "unable to offer you",
        "application was not selected",
        "position has been filled",
    )

    if any(phrase in text for phrase in rejection_phrases):
        return (
            "rejected",
            "No action required unless you want to archive the application.",
        )

    offer_phrases = (
        "we are pleased to offer",
        "we are delighted to offer",
        "offer letter",
        "employment offer",
        "we would like to extend an offer",
    )

    if any(phrase in text for phrase in offer_phrases):
        return "offer", "Review the offer details and its acceptance deadline."

    if any(
        phrase in text
        for phrase in (
            "final interview",
            "final round interview",
            "final round",
        )
    ):
        return (
            "final_interview",
            "Review the email and confirm the final interview schedule.",
        )

    if any(
        phrase in text
        for phrase in (
            "onsite interview",
            "on-site interview",
            "virtual onsite",
        )
    ):
        return (
            "onsite_interview",
            "Review the email and confirm the interview schedule.",
        )

    if any(
        phrase in text
        for phrase in (
            "technical interview",
            "technical screen",
            "system design interview",
            "live coding interview",
        )
    ):
        return (
            "technical_interview",
            "Review the email and confirm the interview schedule.",
        )

    if any(
        phrase in text
        for phrase in (
            "phone screen",
            "phone screening",
            "phone interview",
        )
    ):
        return (
            "phone_screen",
            "Choose a time or confirm the phone-screen schedule.",
        )

    if any(
        phrase in text
        for phrase in (
            "recruiter screen",
            "recruiter call",
            "speak with a recruiter",
        )
    ):
        return (
            "recruiter_screen",
            "Choose a time or respond to the recruiter.",
        )

    if any(
        phrase in text
        for phrase in (
            "online assessment",
            "coding assessment",
            "coding challenge",
            "technical assessment",
            "complete the assessment",
            "take-home assessment",
        )
    ):
        return (
            "online_assessment",
            "Review the assessment deadline and complete it.",
        )

    if any(
        phrase in text
        for phrase in (
            "application received",
            "received your application",
            "thank you for applying",
            "thank you for your application",
            "application confirmation",
        )
    ):
        return (
            "application_received",
            "Wait for a recruiter update or follow up if appropriate.",
        )

    return "unknown", "Review this message and set the correct application status."


def company_from_sender(sender: str) -> str:
    display_name = sender.split("<", maxsplit=1)[0].strip().strip("\"")

    if display_name:
        return display_name

    match = re.search(r"@([\w.-]+)", sender)

    if not match:
        return "Unknown company"

    domain = match.group(1).lower()
    domain = re.sub(
        r"^(mail|email|jobs|careers|recruiting|notifications)\.",
        "",
        domain,
    )

    return domain.split(".")[0].replace("-", " ").title()


def role_from_message(subject: str, body: str) -> str:
    text = normalize_text(f"{subject}\n{body}")

    patterns = (
        r"(?:application for(?: the)? position of|application for(?: the)? position|"
        r"applied for(?: the)? position of|applied for(?: the)? position|"
        r"position of|position:|role of)\s+"
        r"(.+?)(?:\.\s|,\s|;\s|\|\s| we\s| you\s| at\s| with\s|$)",
        r"(?:thank you for your interest in|interest in)\s+"
        r"(.+?)\s+position\s+at\s+",
        r"(?:interview for|interviewing for|application to)\s+"
        r"(.+?)(?:\.\s|,\s|;\s|\|\s| at\s| with\s|$)",
    )

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if not match:
            continue

        role = re.sub(r"\s+", " ", match.group(1)).strip(" -:|.")
        role = re.sub(
            r"^(?:the\s+)?(?:position\s+of\s+|position\s+|role\s+of\s+)",
            "",
            role,
            flags=re.IGNORECASE,
        ).strip()
        role = re.sub(
            r"^the\s+",
            "",
            role,
            flags=re.IGNORECASE,
        ).strip()

        if 4 <= len(role) <= 180:
            return role

    return "Role needs review"


def message_excerpt(text: str) -> str:
    return normalize_text(text)[:700]


def find_existing_job_by_message_id(message_id: str) -> dict[str, Any] | None:
    for job in DEMO_WORKSPACE["job_applications"]:
        if job.get("source_message_id") == message_id:
            return job

        for history_item in job.get("history", []):
            if history_item.get("message_id") == message_id:
                return job

    return None


def find_best_matching_job(
    company: str,
    role: str,
) -> dict[str, Any] | None:
    if role == "Role needs review":
        return None

    normalized_company = company.lower()
    normalized_role = role.lower()

    for job in DEMO_WORKSPACE["job_applications"]:
        job_company = str(job.get("company", "")).lower()
        job_role = str(job.get("role", "")).lower()

        if job_role == "role needs review":
            continue

        company_matches = (
            normalized_company in job_company
            or job_company in normalized_company
        )
        role_matches = (
            normalized_role in job_role
            or job_role in normalized_role
        )

        if company_matches and role_matches:
            return job

    return None


def parse_explicit_datetime(
    text: str,
    received_at: datetime,
) -> tuple[datetime, str] | None:
    """
    Parse deliberately narrow explicit date formats.

    Supported examples:
    - September 18, 2026 at 11:59 PM CT
    - Sep 18 at 5:00 PM CDT
    - 09/18/2026 11:59 PM CT

    The function returns None for ambiguous/no-time statements. That is safer
    than inventing a deadline from incomplete email wording.
    """
    normalized = normalize_text(text)

    month_pattern = (
        r"(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
        r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
        r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    )

    patterns = (
        rf"{month_pattern}\s+(?P<day>\d{{1,2}})(?:,\s*(?P<year>\d{{4}}))?"
        rf"(?:\s+at)?\s+(?P<hour>\d{{1,2}}):(?P<minute>\d{{2}})\s*"
        rf"(?P<ampm>AM|PM)\s*(?P<tz>CT|CDT|CST)?",
        r"(?P<month_num>\d{1,2})/(?P<day_num>\d{1,2})/(?P<year_num>\d{4})"
        r"(?:\s+at)?\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*"
        r"(?P<ampm>AM|PM)\s*(?P<tz>CT|CDT|CST)?",
    )

    month_lookup = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12,
    }

    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)

        if not match:
            continue

        values = match.groupdict()

        try:
            if values.get("month_num"):
                month = int(values["month_num"])
                day = int(values["day_num"])
                year = int(values["year_num"])
            else:
                month = month_lookup[values["month"].lower()]
                day = int(values["day"])
                year = int(values["year"] or received_at.year)

                candidate_date = datetime(year, month, day, tzinfo=received_at.tzinfo)
                if candidate_date < received_at - timedelta(days=30):
                    year += 1

            hour = int(values["hour"])
            minute = int(values["minute"])
            ampm = values["ampm"].upper()

            if ampm == "PM" and hour != 12:
                hour += 12
            elif ampm == "AM" and hour == 12:
                hour = 0

            parsed = datetime(
                year,
                month,
                day,
                hour,
                minute,
                tzinfo=timezone(timedelta(hours=-5)),
            )
            return parsed, match.group(0)
        except (KeyError, ValueError):
            continue

    return None


def proposal_kind_for_message(status: str, text: str) -> str | None:
    """
    Determine whether a job email contains a Calendar-worthy action.

    A proposal is created only after a separate explicit datetime parser finds
    a specific date and time. This function only identifies the action type.
    """
    normalized = normalize_text(text).lower()

    assessment_signals = (
        "online assessment",
        "coding assessment",
        "coding challenge",
        "technical assessment",
        "complete the assessment",
        "take-home assessment",
    )

    confirmed_interview_signals = (
        "interview is confirmed",
        "interview confirmed",
        "scheduled interview",
        "your interview is scheduled",
    )

    if any(signal in normalized for signal in confirmed_interview_signals):
        return "confirmed_interview"

    if status == "online_assessment" and any(
        signal in normalized for signal in assessment_signals
    ):
        return "online_assessment_deadline"

    is_interview_stage = status in {
        "recruiter_screen",
        "phone_screen",
        "technical_interview",
        "onsite_interview",
        "final_interview",
    }

    scheduling_deadline_patterns = (
        r"\bchoose\s+(?:a\s+)?(?:time|day|slot).*?\bby\b",
        r"\bselect\s+(?:a\s+)?(?:time|day|slot).*?\bby\b",
        r"\bschedule.*?\bby\b",
        r"\brespond\s+by\b",
        r"\breply\s+by\b",
        r"\bconfirm.*?\bby\b",
    )

    if is_interview_stage and any(
        re.search(pattern, normalized, flags=re.IGNORECASE)
        for pattern in scheduling_deadline_patterns
    ):
        return "interview_scheduling_deadline"

    return None


def proposal_title(kind: str, company: str) -> str:
    if kind == "online_assessment_deadline":
        return f"Complete assessment — {company}"

    if kind == "interview_scheduling_deadline":
        return f"Choose interview time — {company}"

    return f"Interview — {company}"


def create_job_calendar_proposal(
    *,
    job: dict[str, Any],
    kind: str,
    detected_at: datetime,
    matched_excerpt: str,
    source_message_id: str,
    gmail_url: str,
) -> dict[str, Any] | None:
    """
    Create one pending proposal per Gmail message/kind.

    A missing/ambiguous date returns None. DueScope will keep the job's next
    action but never invent a Calendar reminder.
    """
    for proposal in DEMO_WORKSPACE["job_calendar_proposals"]:
        if (
            proposal["source_message_id"] == source_message_id
            and proposal["kind"] == kind
        ):
            return proposal

    if kind == "confirmed_interview":
        starts_at = detected_at
        ends_at = detected_at + timedelta(minutes=30)
    else:
        starts_at = detected_at - timedelta(minutes=30)
        ends_at = detected_at

    proposal = {
        "id": f"job-calendar-proposal-{uuid4().hex}",
        "job_id": job["id"],
        "company": job["company"],
        "role": job["role"],
        "kind": kind,
        "title": proposal_title(kind, job["company"]),
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "source_message_id": source_message_id,
        "source_excerpt": matched_excerpt,
        "gmail_url": gmail_url,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
        "google_calendar_event_id": None,
        "google_calendar_url": None,
        "calendar_synced_at": None,
    }

    DEMO_WORKSPACE["job_calendar_proposals"].append(proposal)
    return proposal


def job_summary(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job["id"],
        "company": job["company"],
        "role": job["role"],
        "status": job["status"],
        "next_action": job["next_action"],
        "received_at": job["received_at"],
        "requires_review": job["requires_review"],
        "source_subject": job["source_subject"],
        "source_sender": job["source_sender"],
        "source_message_id": job["source_message_id"],
        "source_thread_id": job.get("source_thread_id", ""),
        "gmail_url": job["gmail_url"],
        "source_excerpt": job["source_excerpt"],
        "updated_at": job["updated_at"],
        "history": job.get("history", []),
    }


@router.get("")
def list_job_applications() -> list[dict[str, Any]]:
    jobs = sorted(
        DEMO_WORKSPACE["job_applications"],
        key=lambda job: job["updated_at"],
        reverse=True,
    )

    return [job_summary(job) for job in jobs]


@router.get("/proposals")
def list_job_calendar_proposals() -> list[dict[str, Any]]:
    return sorted(
        DEMO_WORKSPACE["job_calendar_proposals"],
        key=lambda proposal: proposal["created_at"],
        reverse=True,
    )


@router.post("/scan")
def scan_job_application_email(request: JobScanRequest) -> dict[str, Any]:
    """
    Scan Gmail read-only for recruiting/application messages.

    Job reminders are created as pending proposals only when an email contains
    explicit date-and-time wording. Gmail scanning never writes to Calendar.
    """
    credentials = get_credentials()
    service = build("gmail", "v1", credentials=credentials)

    try:
        listing = service.users().messages().list(
            userId="me",
            q=request.query,
            maxResults=request.max_results,
        ).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not search Gmail for job messages: {exc}",
        ) from exc

    message_refs = listing.get("messages", [])
    created: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    calendar_proposals: list[dict[str, Any]] = []

    for message_ref in message_refs:
        message_id = message_ref["id"]

        if find_existing_job_by_message_id(message_id):
            skipped.append(
                {
                    "message_id": message_id,
                    "reason": "This Gmail message was already processed.",
                }
            )
            continue

        try:
            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full",
            ).execute()

            payload = message.get("payload", {})
            headers = payload.get("headers", [])
            sender = header_value(headers, "From")
            subject = header_value(headers, "Subject") or "Untitled job email"
            received_at = message_received_at(message)
            body = cleaned_message_text(payload)

            if not body:
                skipped.append(
                    {
                        "message_id": message_id,
                        "reason": "The email did not contain readable text.",
                    }
                )
                continue

            status, next_action = classify_job_status(subject, body)
            company = company_from_sender(sender)
            role = role_from_message(subject, body)
            source_url = gmail_search_url(sender, subject)

            existing_job = None
            if role != "Role needs review":
                existing_job = find_best_matching_job(company, role)

            if existing_job is None:
                job = {
                    "id": f"job-{uuid4().hex}",
                    "company": company,
                    "role": role,
                    "status": status,
                    "next_action": next_action,
                    "received_at": received_at.isoformat(),
                    "requires_review": True,
                    "source_subject": subject,
                    "source_sender": sender,
                    "source_message_id": message_id,
                    "source_thread_id": message.get("threadId", ""),
                    "gmail_url": source_url,
                    "source_excerpt": message_excerpt(body),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "history": [
                        {
                            "status": status,
                            "message_id": message_id,
                            "received_at": received_at.isoformat(),
                            "reason": "Initial status inferred from Gmail message.",
                        }
                    ],
                }
                DEMO_WORKSPACE["job_applications"].append(job)
                created.append(job_summary(job))
            else:
                job = existing_job
                old_status = str(job["status"])
                should_replace_status = (
                    STATUS_PRIORITY[status] >= STATUS_PRIORITY.get(old_status, 0)
                    or status == "rejected"
                )

                if should_replace_status:
                    job["status"] = status
                    job["next_action"] = next_action
                    job["received_at"] = received_at.isoformat()
                    job["source_subject"] = subject
                    job["source_sender"] = sender
                    job["source_message_id"] = message_id
                    job["source_thread_id"] = message.get("threadId", "")
                    job["gmail_url"] = source_url
                    job["source_excerpt"] = message_excerpt(body)
                    job["updated_at"] = datetime.now(timezone.utc).isoformat()
                    job["requires_review"] = True
                    job["history"].append(
                        {
                            "status": status,
                            "message_id": message_id,
                            "received_at": received_at.isoformat(),
                            "reason": (
                                f"Status updated from {old_status} to {status} "
                                "based on Gmail message."
                            ),
                        }
                    )
                else:
                    job["history"].append(
                        {
                            "status": status,
                            "message_id": message_id,
                            "received_at": received_at.isoformat(),
                            "reason": (
                                f"Earlier or lower-priority Gmail message "
                                f"classified as {status}; current status "
                                f"remains {old_status}."
                            ),
                        }
                    )

                updated.append(job_summary(job))

            kind = proposal_kind_for_message(status, f"{subject}\n{body}")
            parsed_datetime = parse_explicit_datetime(
                f"{subject}\n{body}",
                received_at,
            )

            if kind is not None and parsed_datetime is not None:
                detected_at, matched_excerpt = parsed_datetime
                proposal = create_job_calendar_proposal(
                    job=job,
                    kind=kind,
                    detected_at=detected_at,
                    matched_excerpt=matched_excerpt,
                    source_message_id=message_id,
                    gmail_url=source_url,
                )

                if proposal is not None:
                    calendar_proposals.append(proposal)

        except Exception as exc:
            errors.append(
                {
                    "message_id": message_id,
                    "reason": str(exc),
                }
            )

    return {
        "query": request.query,
        "matched_count": len(message_refs),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "calendar_proposals": calendar_proposals,
        "safety_note": (
            "Job messages are read-only. Calendar reminders are generated only "
            "as pending proposals from explicit dates and require user approval "
            "before Google Calendar is changed."
        ),
    }


@router.post("/proposals/{proposal_id}/approve")
def approve_job_calendar_proposal(proposal_id: str) -> dict[str, Any]:
    proposal = next(
        (
            item
            for item in DEMO_WORKSPACE["job_calendar_proposals"]
            if item["id"] == proposal_id
        ),
        None,
    )

    if proposal is None:
        raise HTTPException(status_code=404, detail="Job calendar proposal not found.")

    if proposal["status"] == "dismissed":
        raise HTTPException(
            status_code=400,
            detail="Dismissed job calendar proposals cannot be approved.",
        )

    proposal["status"] = "approved"
    proposal["resolved_at"] = datetime.now(timezone.utc).isoformat()

    try:
        calendar_result = upsert_job_calendar_event(proposal)
    except Exception as exc:
        proposal["status"] = "pending"
        proposal["resolved_at"] = None
        raise HTTPException(
            status_code=502,
            detail=f"Could not sync approved job reminder to Google Calendar: {exc}",
        ) from exc

    return {
        "proposal": proposal,
        "calendar": calendar_result,
    }


@router.post("/proposals/{proposal_id}/dismiss")
def dismiss_job_calendar_proposal(proposal_id: str) -> dict[str, Any]:
    proposal = next(
        (
            item
            for item in DEMO_WORKSPACE["job_calendar_proposals"]
            if item["id"] == proposal_id
        ),
        None,
    )

    if proposal is None:
        raise HTTPException(status_code=404, detail="Job calendar proposal not found.")

    if proposal["status"] == "approved":
        raise HTTPException(
            status_code=400,
            detail=(
                "This reminder is already approved and synced. Delete it from "
                "Google Calendar manually if it is no longer needed."
            ),
        )

    proposal["status"] = "dismissed"
    proposal["resolved_at"] = datetime.now(timezone.utc).isoformat()

    return proposal


@router.patch("/{job_id}")
def update_job_application(
    job_id: str,
    request: JobApplicationUpdateRequest,
) -> dict[str, Any]:
    for job in DEMO_WORKSPACE["job_applications"]:
        if job["id"] != job_id:
            continue

        update_data = request.model_dump(exclude_none=True)

        if "status" in update_data and update_data["status"] not in VALID_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Invalid job status. Valid values are: "
                    + ", ".join(sorted(VALID_STATUSES))
                ),
            )

        job.update(update_data)
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        job["requires_review"] = False

        return job_summary(job)

    raise HTTPException(status_code=404, detail="Job application not found")
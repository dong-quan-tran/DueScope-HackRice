from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from app.api.demo import DEMO_WORKSPACE
from app.services.google_oauth import get_credentials


router = APIRouter(prefix="/jobs", tags=["jobs"])


DEFAULT_JOB_QUERY = (
    "newer_than:365d in:inbox "
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
            "Gmail query used to find recruiting messages. The default only "
            "allows common applicant-tracking-system sender domains."
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
    """
    Recursively collect readable Gmail content.

    Prefer text/plain and use converted HTML only if plain text is unavailable.
    Attachments are intentionally ignored.
    """
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


def classify_job_status(subject: str, body: str) -> tuple[str, str]:
    """
    Classify only explicit recruiting language.

    Rejection checks must run before application-received checks because
    rejection emails commonly include phrases such as "thank you for applying."
    """
    text = unescape(f"{subject}\n{body}").lower()
    text = re.sub(r"\s+", " ", text)

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
    """
    Use the sender display name as a cautious fallback company label.

    The user can correct it through PATCH /api/jobs/{job_id}.
    """
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
    """
    Extract a role only from explicit application/interview wording.

    The parser intentionally returns "Role needs review" when it cannot find
    a sufficiently clear title. This avoids merging unrelated recruiter mail.
    """
    text = unescape(f"{subject}\n{body}")
    text = re.sub(r"\s+", " ", text).strip()

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
    normalized = re.sub(r"\s+", " ", text).strip()
    return normalized[:700]


def find_existing_job_by_message_id(message_id: str) -> dict[str, Any] | None:
    return next(
        (
            job
            for job in DEMO_WORKSPACE["job_applications"]
            if job.get("source_message_id") == message_id
        ),
        None,
    )


def find_best_matching_job(
    company: str,
    role: str,
) -> dict[str, Any] | None:
    """
    Match only records whose company and role are both meaningful.

    Do not merge vague "Role needs review" messages. Merging unknown messages
    is how unrelated notifications can become one invented job record.
    """
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
        "gmail_url": job["gmail_url"],
        "source_excerpt": job["source_excerpt"],
        "updated_at": job["updated_at"],
    }


@router.get("")
def list_job_applications() -> list[dict[str, Any]]:
    jobs = sorted(
        DEMO_WORKSPACE["job_applications"],
        key=lambda job: job["updated_at"],
        reverse=True,
    )

    return [job_summary(job) for job in jobs]


@router.post("/scan")
@router.post("/scan")
def scan_job_application_email(request: JobScanRequest) -> dict[str, Any]:
    """
    Scan read-only Gmail for recruiting/application messages.

    Safety rules:
    - The default search limits messages to common ATS sender domains.
    - Classifications require explicit language.
    - Every result retains a Gmail source link and requires review.
    - No interview, assessment, or job status is automatically written to
      Google Calendar.
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
                    "gmail_url": (
                        f"https://mail.google.com/mail/u/0/#all/{message_id}"
                    ),
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
                continue

            old_status = str(existing_job["status"])
            should_replace_status = (
                STATUS_PRIORITY[status] >= STATUS_PRIORITY.get(old_status, 0)
                or status == "rejected"
            )

            if should_replace_status:
                existing_job["status"] = status
                existing_job["next_action"] = next_action
                existing_job["received_at"] = received_at.isoformat()
                existing_job["source_subject"] = subject
                existing_job["source_sender"] = sender
                existing_job["source_message_id"] = message_id
                existing_job["source_thread_id"] = message.get("threadId", "")
                existing_job["gmail_url"] = (
                    f"https://mail.google.com/mail/u/0/#all/{message_id}"
                )
                existing_job["source_excerpt"] = message_excerpt(body)
                existing_job["updated_at"] = datetime.now(timezone.utc).isoformat()
                existing_job["requires_review"] = True
                existing_job["history"].append(
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

                updated.append(job_summary(existing_job))
                continue

            existing_job["history"].append(
                {
                    "status": status,
                    "message_id": message_id,
                    "received_at": received_at.isoformat(),
                    "reason": (
                        f"Earlier or lower-priority Gmail message classified as "
                        f"{status}; current status remains {old_status}."
                    ),
                }
            )

            updated.append(job_summary(existing_job))

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
        "safety_note": (
            "Job messages are read-only. The default search is restricted to "
            "common recruiting-system senders. All inferred statuses require "
            "review, and no interview or assessment is automatically added "
            "to Google Calendar."
        ),
    }


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
from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any

from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from app.api.demo import DEMO_WORKSPACE
from app.api.sources import extract_and_reconcile
from app.schemas.events import SourceType
from app.schemas.extraction import ExtractDeadlineRequest
from app.services.google_oauth import get_credentials


router = APIRouter(prefix="/gmail", tags=["gmail"])


DEFAULT_GMAIL_QUERY = (
    "newer_than:120d in:inbox "
    "(from:canvas OR from:instructure OR from:notifications) "
    "(assignment OR deadline OR due OR exam OR quiz OR syllabus)"
)


class GmailScanRequest(BaseModel):
    course_id: str = Field(
        default="cse-3310",
        description=(
            "DueScope course ID for every message in this scan. "
            "Run one scan per course so extracted deadlines reconcile "
            "against the correct course."
        ),
    )
    query: str = Field(
        default=DEFAULT_GMAIL_QUERY,
        min_length=1,
        max_length=500,
        description=(
            "Gmail search query. Prefer specific instructor, Canvas, TA, or "
            "institutional sender filters to avoid promotional-email matches."
        ),
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=25,
        description="Maximum number of matching Gmail messages to inspect.",
    )


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
    Recursively gather readable content from Gmail MIME parts.

    Prefer text/plain. Use converted HTML only when plain text is unavailable.
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


def source_type_from_sender(sender: str) -> SourceType:
    normalized_sender = sender.lower()

    if "canvas" in normalized_sender or "instructure" in normalized_sender:
        return SourceType("instructor_announcement")

    return SourceType("instructor_email")


def course_exists(course_id: str) -> bool:
    return any(
        course["id"] == course_id
        for course in DEMO_WORKSPACE["courses"]
    )


def clean_message_text(parts: list[str]) -> str:
    """
    Build bounded source text for AI extraction.

    Keeping the body bounded prevents giant mailing-list footers and rich-email
    templates from becoming an unnecessarily large extraction prompt.
    """
    text = "\n\n".join(part.strip() for part in parts if part.strip())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text[:12000]


def gmail_source_text(
    *,
    sender: str,
    subject: str,
    received_at: datetime,
    body: str,
) -> str:
    """
    Include reliable message metadata in the source text while preserving the
    email body as the evidence that deadline extraction must cite.
    """
    return (
        f"From: {sender or 'Unknown sender'}\n"
        f"Subject: {subject or 'Untitled Gmail message'}\n"
        f"Received: {received_at.isoformat()}\n\n"
        f"{body}"
    )


def summary_from_response(response: Any) -> dict[str, int]:
    """
    Convert results from sources.extract_and_reconcile into a compact Gmail
    scan summary without depending on a particular AI provider.
    """
    counts = {
        "candidates_found": len(response.results),
        "events_created": 0,
        "proposals_created": 0,
        "unchanged": 0,
        "needs_review": 0,
    }

    for result in response.results:
        if result.action == "created":
            counts["events_created"] += 1
        elif result.proposal_id:
            counts["proposals_created"] += 1
        elif result.action in {"unchanged", "same_date"}:
            counts["unchanged"] += 1
        elif result.action == "needs_review":
            counts["needs_review"] += 1

    return counts


@router.post("/scan")
def scan_gmail(request: GmailScanRequest) -> dict[str, Any]:
    """
    Scan selected Gmail messages and route each one through the existing
    DueScope extraction, evidence-validation, and reconciliation workflow.

    Safety rules:
    - Gmail access is read-only.
    - Every candidate retains the Gmail message as its source evidence.
    - Conflicting dates become proposals rather than overwriting deadlines.
    - No candidate is automatically approved or synced to Google Calendar.
    """
    if not course_exists(request.course_id):
        raise HTTPException(
            status_code=404,
            detail=f"DueScope course '{request.course_id}' was not found.",
        )

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
            detail=f"Could not search Gmail: {exc}",
        ) from exc

    message_refs = listing.get("messages", [])

    messages: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    totals = {
        "matched_count": len(message_refs),
        "scanned_count": 0,
        "sources_saved": 0,
        "candidates_found": 0,
        "events_created": 0,
        "proposals_created": 0,
        "unchanged": 0,
        "needs_review": 0,
        "skipped_messages": 0,
    }

    for message_ref in message_refs:
        message_id = message_ref["id"]

        try:
            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full",
            ).execute()

            payload = message.get("payload", {})
            headers = payload.get("headers", [])

            sender = header_value(headers, "From")
            subject = header_value(headers, "Subject") or "Untitled Gmail message"
            received_at = message_received_at(message)
            body = clean_message_text(extract_text_parts(payload))

            if not body:
                totals["skipped_messages"] += 1
                messages.append(
                    {
                        "message_id": message_id,
                        "thread_id": message.get("threadId", ""),
                        "sender": sender,
                        "subject": subject,
                        "received_at": received_at.isoformat(),
                        "status": "skipped",
                        "reason": "The message did not contain readable text.",
                    }
                )
                continue

            source_type = source_type_from_sender(sender)
            source_text = gmail_source_text(
                sender=sender,
                subject=subject,
                received_at=received_at,
                body=body,
            )

            extraction_request = ExtractDeadlineRequest(
                course_id=request.course_id,
                source_type=source_type,
                source_title=subject,
                source_received_at=received_at,
                timezone="America/Chicago",
                source_text=source_text,
            )

            extraction_response = extract_and_reconcile(extraction_request)
            summary = summary_from_response(extraction_response)

            totals["scanned_count"] += 1
            totals["sources_saved"] += 1
            totals["candidates_found"] += summary["candidates_found"]
            totals["events_created"] += summary["events_created"]
            totals["proposals_created"] += summary["proposals_created"]
            totals["unchanged"] += summary["unchanged"]
            totals["needs_review"] += summary["needs_review"]

            messages.append(
                {
                    "message_id": message_id,
                    "thread_id": message.get("threadId", ""),
                    "sender": sender,
                    "subject": subject,
                    "received_at": received_at.isoformat(),
                    "gmail_url": (
                        f"https://mail.google.com/mail/u/0/#all/{message_id}"
                    ),
                    "source_id": extraction_response.source_id,
                    "status": "processed",
                    "excerpt": body[:360],
                }
            )

            results.extend(
                {
                    "message_id": message_id,
                    "source_id": extraction_response.source_id,
                    "title": item.title,
                    "action": item.action,
                    "message": item.message,
                    "event_id": item.event_id,
                    "proposal_id": item.proposal_id,
                }
                for item in extraction_response.results
            )
        except HTTPException as exc:
            errors.append(
                {
                    "message_id": message_id,
                    "reason": str(exc.detail),
                }
            )
        except Exception as exc:
            errors.append(
                {
                    "message_id": message_id,
                    "reason": str(exc),
                }
            )

    return {
        "query": request.query,
        "course_id": request.course_id,
        **totals,
        "messages": messages,
        "results": results,
        "errors": errors,
        "safety_note": (
            "Gmail is read-only. Extracted deadlines follow the same "
            "validation and proposal-review process as pasted sources. "
            "Nothing is automatically approved or synced to Google Calendar."
        ),
    }
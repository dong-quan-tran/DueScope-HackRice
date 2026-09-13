"""Validation for extracted deadline candidates."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Mapping


def _has_timezone(timestamp: str) -> bool:
    """Return whether an ISO-8601 timestamp includes timezone information."""
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False

    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def validate_candidate(candidate: Any, source_text: Any) -> dict[str, Any]:
    """Validate an extracted candidate without changing its input."""
    issues: list[str] = []

    if not isinstance(candidate, Mapping):
        return {
            "candidate": deepcopy(candidate),
            "needs_review": True,
            "issues": ["Candidate must be an object."],
            "approved": False,
        }

    validated_candidate = deepcopy(dict(candidate))

    title = validated_candidate.get("title")
    if not isinstance(title, str) or not title.strip():
        issues.append("Title is missing.")
    else:
        validated_candidate["title"] = title.strip()

    due_at = validated_candidate.get("due_at")
    if due_at is None or (isinstance(due_at, str) and not due_at.strip()):
        issues.append("Due date and time (due_at) is missing.")
    elif not isinstance(due_at, str):
        issues.append("Due date and time (due_at) must be an ISO-8601 timestamp.")
    else:
        normalized_due_at = due_at.strip().replace("Z", "+00:00")

        try:
            if "T" not in normalized_due_at and " " not in normalized_due_at:
                raise ValueError

            datetime.fromisoformat(normalized_due_at)
        except ValueError:
            issues.append("Due date and time (due_at) is invalid.")
        else:
            if not _has_timezone(due_at.strip()):
                issues.append(
                    "Due date and time (due_at) must include timezone information."
                )

    if not isinstance(source_text, str):
        issues.append("Source text must be a string.")

    source_excerpt = validated_candidate.get("source_excerpt")
    if not isinstance(source_excerpt, str) or not source_excerpt.strip():
        issues.append("Source excerpt is missing or blank.")
    else:
        normalized_excerpt = source_excerpt.strip()
        validated_candidate["source_excerpt"] = normalized_excerpt

        if isinstance(source_text, str) and normalized_excerpt not in source_text:
            issues.append("Source excerpt does not appear exactly in source text.")

    return {
        "candidate": validated_candidate,
        "needs_review": bool(issues),
        "issues": issues,
        "approved": False,
    }

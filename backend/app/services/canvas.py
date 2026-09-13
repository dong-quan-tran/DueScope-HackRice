import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")


def parse_canvas_datetime(value: str | None) -> datetime | None:
    """Convert a Canvas ISO date into a Python datetime."""
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class CanvasClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
        self.access_token = os.getenv("CANVAS_ACCESS_TOKEN", "")

        if not self.base_url:
            raise RuntimeError("CANVAS_BASE_URL is not configured in .env.")
        if not self.access_token:
            raise RuntimeError("CANVAS_ACCESS_TOKEN is not configured in .env.")

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = httpx.get(
            f"{self.base_url}{path}",
            headers=self.headers,
            params=params,
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()

    def profile(self) -> dict[str, Any]:
        return self.get("/api/v1/users/self/profile")

    def courses(self) -> list[dict[str, Any]]:
        return self.get(
            "/api/v1/courses",
            {
                "enrollment_state": "active",
                "per_page": 100,
            },
        )

    def assignments(self, course_id: int) -> list[dict[str, Any]]:
        """Return raw assignments from Canvas for one course."""
        return self.get(
            f"/api/v1/courses/{course_id}/assignments",
            {
                "per_page": 100,
                "order_by": "due_at",
            },
        )

    def upcoming_assignments(self, course_id: int) -> list[dict[str, Any]]:
        """Return only future Canvas assignments that have a due date."""
        now = datetime.now(timezone.utc)
        upcoming: list[dict[str, Any]] = []

        for assignment in self.assignments(course_id):
            due_at = assignment.get("due_at")
            parsed_due_at = parse_canvas_datetime(due_at)

            if parsed_due_at is None or parsed_due_at < now:
                continue

            upcoming.append(
                {
                    "id": assignment.get("id"),
                    "course_id": course_id,
                    "name": assignment.get("name", "Untitled Canvas assignment"),
                    "due_at": due_at,
                    "html_url": assignment.get("html_url"),
                    "description": assignment.get("description") or "",
                }
            )

        return sorted(item for item in upcoming if item["due_at"])


def canvas_client() -> CanvasClient:
    return CanvasClient()
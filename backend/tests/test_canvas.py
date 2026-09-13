from copy import deepcopy
from datetime import datetime, timezone

from app.api import canvas as canvas_api
from app.api.demo import DEMO_WORKSPACE


class MockCanvasClient:
    def __init__(self, assignments):
        self._assignments = assignments

    def courses(self):
        return [{"id": 42, "course_code": "BIO 101", "name": "Biology"}]

    def assignments(self, course_id):
        assert course_id == 42
        return self._assignments


def assignment(assignment_id, name, due_at, description=""):
    return {
        "id": assignment_id,
        "name": name,
        "due_at": due_at,
        "html_url": f"https://canvas.example/assignments/{assignment_id}",
        "description": description,
    }


def test_imports_real_future_assignments_and_is_idempotent(monkeypatch):
    original_workspace = deepcopy(DEMO_WORKSPACE)
    due_at = "2099-10-01T18:30:00Z"
    assignments = [
        assignment(
            9001,
            "Lab report alpha",
            due_at,
            "Submit the lab report through Canvas.",
        ),
        assignment(9002, "Past assignment", "2020-01-01T00:00:00Z"),
        assignment(9003, "Undated assignment", None),
    ]
    monkeypatch.setattr(
        canvas_api,
        "canvas_client",
        lambda: MockCanvasClient(assignments),
    )

    try:
        first = canvas_api.import_canvas_course(42)
        second = canvas_api.import_canvas_course(42)

        imported_events = [
            event
            for event in DEMO_WORKSPACE["events"]
            if event["source_id"] == "canvas-assignment-9001"
        ]
        assert first["imported_count"] == 1
        assert first["skipped_past_count"] == 1
        assert first["items"][0]["title"] == "Lab report alpha"
        assert first["items"][0]["description"] == (
            "Submit the lab report through Canvas."
        )
        assert first["items"][0]["html_url"] == (
            "https://canvas.example/assignments/9001"
        )
        assert len(imported_events) == 1
        assert imported_events[0]["course_id"] == "canvas-42"
        assert imported_events[0]["due_at"] == due_at
        source = next(
            source
            for source in DEMO_WORKSPACE["sources"]
            if source["id"] == "canvas-assignment-9001"
        )
        assert source["raw_text"] == "Submit the lab report through Canvas."
        assert source["source_url"] == (
            "https://canvas.example/assignments/9001"
        )
        assert second["items"][0]["action"] == "unchanged"
        assert len(
            [
                event
                for event in DEMO_WORKSPACE["events"]
                if event["source_id"] == "canvas-assignment-9001"
            ]
        ) == 1
    finally:
        DEMO_WORKSPACE.clear()
        DEMO_WORKSPACE.update(original_workspace)


def test_import_reports_no_upcoming_assignments(monkeypatch):
    original_workspace = deepcopy(DEMO_WORKSPACE)
    monkeypatch.setattr(
        canvas_api,
        "canvas_client",
        lambda: MockCanvasClient(
            [assignment(9004, "Past assignment", "2020-01-01T00:00:00Z")]
        ),
    )

    try:
        result = canvas_api.import_canvas_course(42)

        assert result["imported_count"] == 0
        assert result["message"] == (
            "No upcoming Canvas assignments with due dates were found"
        )
        assert not any(
            event["source_id"] == "canvas-assignment-9004"
            for event in DEMO_WORKSPACE["events"]
        )
    finally:
        DEMO_WORKSPACE.clear()
        DEMO_WORKSPACE.update(original_workspace)
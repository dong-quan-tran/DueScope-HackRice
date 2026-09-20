from pathlib import Path
import sys

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


def test_demo_workspace_keeps_unknown_deadlines_unknown() -> None:
    with TestClient(app) as client:
        response = client.get("/api/demo/workspace")

    assert response.status_code == 200
    workspace = response.json()

    prelab = next(
        event
        for event in workspace["events"]
        if event["id"] == "event-chem-prelab"
    )

    assert prelab["due_at"] is None
    assert prelab["status"] == "needs_review"
    assert prelab["needs_review_reason"]


def test_updated_demo_event_has_one_current_history_entry() -> None:
    with TestClient(app) as client:
        response = client.get("/api/demo/workspace")

    assert response.status_code == 200
    quiz = next(
        event
        for event in response.json()["events"]
        if event["id"] == "event-quiz-2"
    )

    current_items = [
        item for item in quiz["history"] if item["is_current"] is True
    ]

    assert len(current_items) == 1
    assert current_items[0]["due_at"] == quiz["due_at"]

from pathlib import Path
import sys

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


def test_demo_workspace_returns_expected_persistent_shape() -> None:
    with TestClient(app) as client:
        response = client.get("/api/demo/workspace")

    assert response.status_code == 200
    workspace = response.json()

    assert workspace["student"]["timezone"] == "America/Chicago"
    assert len(workspace["courses"]) == 3
    assert len(workspace["sources"]) == 4
    assert len(workspace["events"]) == 7
    assert workspace["proposals"] == []
    assert workspace["job_applications"] == []
    assert workspace["job_calendar_proposals"] == []

    quiz = next(event for event in workspace["events"] if event["id"] == "event-quiz-2")
    assert quiz["status"] == "updated"
    assert quiz["history"]
    assert quiz["history"][-1]["is_current"] is True


def test_demo_workspace_is_stable_on_repeat_reads() -> None:
    with TestClient(app) as client:
        first = client.get("/api/demo/workspace")
        second = client.get("/api/demo/workspace")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["events"] == second.json()["events"]

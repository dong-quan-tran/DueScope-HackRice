from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.api.demo import DEMO_WORKSPACE
from app.api.events import source_maps, store_proposal
from app.schemas.events import (
    AcademicEvent,
    ChangeType,
    EventCandidate,
    EventType,
    SourceType,
)
from app.services.canvas import canvas_client, parse_canvas_datetime
from app.services.reconciliation import reconcile_candidate

router = APIRouter(prefix="/canvas", tags=["canvas"])


def assignment_event_type(name: str) -> EventType:
    normalized = name.lower()

    if "quiz" in normalized:
        return EventType.QUIZ
    if any(term in normalized for term in ("exam", "midterm", "final")):
        return EventType.EXAM
    if "lab" in normalized:
        return EventType.LAB
    if "project" in normalized:
        return EventType.PROJECT

    return EventType.ASSIGNMENT


def canvas_error(error: Exception) -> HTTPException:
    if isinstance(error, RuntimeError):
        return HTTPException(status_code=503, detail=str(error))

    if isinstance(error, httpx.HTTPStatusError):
        return HTTPException(
            status_code=error.response.status_code,
            detail=f"Canvas request failed: {error.response.text}",
        )

    return HTTPException(
        status_code=502,
        detail=f"Could not connect to Canvas: {error}",
    )


@router.get("/profile")
def get_canvas_profile() -> dict:
    try:
        return canvas_client().profile()
    except Exception as error:
        raise canvas_error(error) from error


@router.get("/courses")
def get_canvas_courses() -> list[dict]:
    try:
        courses = canvas_client().courses()

        return [
            {
                "id": course["id"],
                "course_code": course.get("course_code", ""),
                "name": course.get("name", ""),
                "workflow_state": course.get("workflow_state", ""),
            }
            for course in courses
        ]
    except Exception as error:
        raise canvas_error(error) from error


@router.get("/courses/{course_id}/assignments")
def get_canvas_assignments(
    course_id: int,
    include_past: bool = Query(default=False),
) -> list[dict]:
    try:
        now = datetime.now(timezone.utc)
        assignments = canvas_client().assignments(course_id)

        results = []

        for assignment in assignments:
            due_at = parse_canvas_datetime(assignment.get("due_at"))

            if due_at is None:
                continue

            if not include_past and due_at < now:
                continue

            results.append(
                {
                    "id": assignment["id"],
                    "name": assignment.get("name", ""),
                    "due_at": assignment.get("due_at"),
                    "points_possible": assignment.get("points_possible"),
                    "html_url": assignment.get("html_url"),
                    "description": assignment.get("description"),
                }
            )

        return results
    except Exception as error:
        raise canvas_error(error) from error


@router.post("/import-course/{course_id}")
def import_canvas_course(
    course_id: int,
    include_past: bool = Query(default=False),
) -> dict:
    try:
        client = canvas_client()
        courses = client.courses()
        canvas_course = next(
            (course for course in courses if course["id"] == course_id),
            None,
        )

        if canvas_course is None:
            raise HTTPException(
                status_code=404,
                detail="Canvas course not found among active courses.",
            )

        course_key = f"canvas-{course_id}"

        if not any(
            course["id"] == course_key
            for course in DEMO_WORKSPACE["courses"]
        ):
            DEMO_WORKSPACE["courses"].append(
                {
                    "id": course_key,
                    "code": (
                        canvas_course.get("course_code")
                        or f"Canvas {course_id}"
                    ),
                    "name": (
                        canvas_course.get("name")
                        or "Canvas Course"
                    ),
                    "color": "#F97316",
                }
            )

        now = datetime.now(timezone.utc)
        assignments = client.assignments(course_id)
        imported: list[dict] = []
        skipped_past_count = 0

        for assignment in assignments:
            due_at = parse_canvas_datetime(assignment.get("due_at"))

            if due_at is None:
                continue

            if not include_past and due_at < now:
                skipped_past_count += 1
                continue

            source_id = f"canvas-assignment-{assignment['id']}"
            source_excerpt = (
                f"Canvas assignment due date: {due_at.isoformat()}. "
                f"Points possible: {assignment.get('points_possible')}."
            )

            if not any(
                source["id"] == source_id
                for source in DEMO_WORKSPACE["sources"]
            ):
                DEMO_WORKSPACE["sources"].append(
                    {
                        "id": source_id,
                        "course_id": course_key,
                        "type": SourceType.CANVAS_DUE_FIELD.value,
                        "title": assignment.get(
                            "name",
                            "Canvas assignment",
                        ),
                        "received_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                        "raw_text": source_excerpt,
                        "source_url": assignment.get("html_url"),
                    }
                )

            candidate = EventCandidate(
                course_id=course_key,
                type=assignment_event_type(
                    assignment.get("name", "")
                ),
                title=assignment.get("name", "Canvas assignment"),
                due_at=due_at,
                source_id=source_id,
                source_excerpt=source_excerpt,
                change_type=ChangeType.NEW,
                confidence="high",
            )

            events = [
                AcademicEvent.model_validate(event)
                for event in DEMO_WORKSPACE["events"]
            ]
            source_types, source_received_at = source_maps()

            result = reconcile_candidate(
                candidate=candidate,
                candidate_source_type=SourceType.CANVAS_DUE_FIELD,
                candidate_received_at=datetime.now(timezone.utc),
                events=events,
                source_types=source_types,
                source_received_at=source_received_at,
            )

            proposal_id = None

            if result.action == "created":
                DEMO_WORKSPACE["events"].append(
                    result.event.model_dump(mode="json")
                )
            elif result.proposed_candidate is not None:
                proposal = store_proposal(
                    event_id=result.event.id,
                    candidate=result.proposed_candidate,
                    message=result.message,
                )
                proposal_id = proposal.id

            imported.append(
                {
                    "canvas_assignment_id": assignment["id"],
                    "title": assignment.get("name", ""),
                    "due_at": due_at.isoformat(),
                    "action": result.action,
                    "event_id": result.event.id,
                    "proposal_id": proposal_id,
                }
            )

        return {
            "course": {
                "canvas_id": course_id,
                "course_id": course_key,
                "course_code": canvas_course.get("course_code", ""),
                "name": canvas_course.get("name", ""),
            },
            "include_past": include_past,
            "imported_count": len(imported),
            "skipped_past_count": skipped_past_count,
            "items": imported,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise canvas_error(error) from error

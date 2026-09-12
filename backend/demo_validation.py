from app.services.deadline_validation import validate_candidate


SOURCE_TEXT = "Quiz 2 is due Thursday, September 17 at 11:59 PM."

EXAMPLES = [
    (
        "Valid event",
        {
            "title": " Quiz 2 ",
            "due_at": "2026-09-17T23:59:00-05:00",
            "source_excerpt": SOURCE_TEXT,
        },
    ),
    ("Missing date", {"title": "Quiz 2", "due_at": None, "source_excerpt": SOURCE_TEXT}),
    (
        "Invalid date",
        {"title": "Quiz 2", "due_at": "September 17", "source_excerpt": SOURCE_TEXT},
    ),
    (
        "Missing timezone",
        {"title": "Quiz 2", "due_at": "2026-09-17T23:59:00", "source_excerpt": SOURCE_TEXT},
    ),
    (
        "Invented evidence",
        {
            "title": "Quiz 2",
            "due_at": "2026-09-17T23:59:00-05:00",
            "source_excerpt": "Quiz 2 is due Friday, September 18.",
        },
    ),
]


for name, candidate in EXAMPLES:
    result = validate_candidate(candidate, SOURCE_TEXT)
    print(f"{name}: needs_review={result['needs_review']}, approved={result['approved']}")
    print(f"  title={result['candidate'].get('title')!r}")
    print(f"  issues={result['issues'] or ['None']}")
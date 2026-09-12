import copy
import unittest

from app.services.deadline_validation import validate_candidate


SOURCE_TEXT = "Quiz 2 is due Thursday, September 17 at 11:59 PM."


def make_candidate(**overrides):
    candidate = {
        "event_type": "quiz",
        "title": " Quiz 2 ",
        "due_at": "2026-09-17T23:59:00-05:00",
        "source_excerpt": "Quiz 2 is due Thursday, September 17 at 11:59 PM.",
        "unknown_value": {"kept": True},
    }
    candidate.update(overrides)
    return candidate


class ValidateCandidateTests(unittest.TestCase):
    def test_valid_event_is_accepted_but_not_approved(self):
        result = validate_candidate(make_candidate(), SOURCE_TEXT)

        self.assertFalse(result["needs_review"])
        self.assertEqual(result["issues"], [])
        self.assertFalse(result["approved"])
        self.assertEqual(result["candidate"]["title"], "Quiz 2")

    def test_missing_date_needs_review(self):
        result = validate_candidate(make_candidate(due_at=None), SOURCE_TEXT)

        self.assertTrue(result["needs_review"])
        self.assertIn("due_at) is missing", result["issues"][0])

    def test_invalid_date_needs_review(self):
        result = validate_candidate(make_candidate(due_at="September 17 at 11:59 PM"), SOURCE_TEXT)

        self.assertTrue(result["needs_review"])
        self.assertIn("due_at) is invalid", result["issues"][0])

    def test_missing_timezone_needs_review(self):
        result = validate_candidate(make_candidate(due_at="2026-09-17T23:59:00"), SOURCE_TEXT)

        self.assertTrue(result["needs_review"])
        self.assertIn("timezone information", result["issues"][0])

    def test_invented_evidence_needs_review(self):
        result = validate_candidate(
            make_candidate(source_excerpt="Quiz 2 is due Friday, September 18."),
            SOURCE_TEXT,
        )

        self.assertTrue(result["needs_review"])
        self.assertIn("does not appear exactly", result["issues"][0])

    def test_input_is_not_changed_and_unknown_values_are_preserved(self):
        candidate = make_candidate()
        original = copy.deepcopy(candidate)

        result = validate_candidate(candidate, SOURCE_TEXT)

        self.assertEqual(candidate, original)
        self.assertEqual(result["candidate"]["unknown_value"], {"kept": True})

    def test_malformed_inputs_do_not_crash(self):
        result = validate_candidate(["not", "an", "object"], None)

        self.assertTrue(result["needs_review"])
        self.assertFalse(result["approved"])
        self.assertEqual(result["candidate"], ["not", "an", "object"])


    def test_missing_or_blank_evidence_needs_review(self):
        for excerpt in ("", "   ", None, 123):
            with self.subTest(excerpt=excerpt):
                result = validate_candidate(
                    make_candidate(source_excerpt=excerpt),
                    SOURCE_TEXT,
                )

                self.assertTrue(result["needs_review"])
                self.assertIn(
                    "Source excerpt is missing or blank.",
                    result["issues"],
                )
                self.assertFalse(result["approved"])


if __name__ == "__main__":
    unittest.main()
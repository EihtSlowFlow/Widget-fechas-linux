import unittest
from datetime import date
from unittest.mock import patch

from backend.fechas_sync import generate_weekly_schedule, process_subjects
from backend.models import ClassScheduleEntry, SubjectSyllabus
from backend.subject_actions import virtual_class_url_for_subject
from backend.virtual_class import is_valid_virtual_class_url


class TestVirtualClassUrl(unittest.TestCase):
    def test_accepts_http_urls_and_preserves_meeting_tokens(self):
        url = "https://meet.example.edu/room?token=a&user=b#join=1"
        self.assertTrue(is_valid_virtual_class_url(url))
        subject = SubjectSyllabus.from_dict({
            "id": "subject-1",
            "name": "Redes",
            "start_date": "2026-08-01",
            "virtual_class_url": url,
        })
        self.assertEqual(subject.virtual_class_url, url)
        self.assertEqual(subject.to_dict()["virtual_class_url"], url)

    def test_rejects_non_web_relative_and_malformed_urls(self):
        invalid_urls = (
            "", "meet.example.edu/room", "/room", "javascript:alert(1)",
            "file:///tmp/room", "https://", "https://example.edu/room with space",
            " https://example.edu/room", "https://example.edu:bad/room",
        )
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(is_valid_virtual_class_url(url))

    def test_invalid_url_is_not_exposed_by_model(self):
        subject = SubjectSyllabus.from_dict({
            "name": "Seguridad",
            "start_date": "2026-08-01",
            "virtual_class_url": "bash -c whoami",
        })
        self.assertEqual(subject.virtual_class_url, "")

    def test_url_reaches_current_subject_and_schedule_cache(self):
        url = "https://class.example.edu/join?a=1&b=2#token=x=y"
        subject = SubjectSyllabus(
            id="subject_1", name="Bases", start_date="2026-08-01",
            virtual_class_url=url,
            class_schedule=[ClassScheduleEntry(1, "09:00", "11:00")],
        )
        current = process_subjects([subject], date(2026, 8, 24))
        schedule = generate_weekly_schedule([subject], date(2026, 8, 24))
        self.assertEqual(current[0].virtual_class_url, url)
        self.assertEqual(schedule[0]["virtual_class_url"], url)

    @patch("backend.subject_actions.read_subjects")
    def test_copy_lookup_uses_subject_id_and_returns_exact_url(self, read_subjects):
        url = "https://meet.example.edu/join?key=a&token=b=c#room"
        read_subjects.return_value = [SubjectSyllabus(
            id="safe-id", name="Datos", start_date="2026-08-01",
            virtual_class_url=url,
        )]
        self.assertEqual(virtual_class_url_for_subject("safe-id"), url)
        self.assertIsNone(virtual_class_url_for_subject("safe-id; bash -c whoami"))


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from datetime import date
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from backend.fechas_sync import (
    generate_virtual_classes, generate_weekly_schedule, process_subjects,
)
from backend.models import ClassScheduleEntry, SubjectSyllabus
from backend.subject_actions import copy_virtual_class_link, virtual_class_url_for_subject
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
            "virtual_class_platform": "google_meet",
        })
        self.assertEqual(subject.virtual_class_url, url)
        self.assertEqual(subject.to_dict()["virtual_class_url"], url)
        self.assertEqual(subject.virtual_class_platform, "google_meet")

    def test_model_normalizes_legacy_url_whitespace(self):
        subject = SubjectSyllabus.from_dict({
            "name": "Redes", "start_date": "2026-08-01",
            "virtual_class_url": "  https://meet.example.edu/room?a=1&b=2  ",
            "virtual_class_platform": "google_meet",
        })
        self.assertEqual(
            subject.virtual_class_url, "https://meet.example.edu/room?a=1&b=2"
        )

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
            virtual_class_platform="zoom",
            class_schedule=[ClassScheduleEntry(1, "09:00", "11:00")],
        )
        current = process_subjects([subject], date(2026, 8, 24))
        schedule = generate_weekly_schedule([subject], date(2026, 8, 24))
        self.assertEqual(current[0].virtual_class_url, url)
        self.assertEqual(schedule[0]["virtual_class_url"], url)
        self.assertEqual(current[0].virtual_class_platform, "zoom")
        self.assertEqual(schedule[0]["virtual_class_platform"], "zoom")

    def test_virtual_classes_are_unique_today_first_and_exclude_invalid(self):
        url = "https://meet.example.edu/class"
        today = date(2026, 8, 24)  # lunes
        subjects = [
            SubjectSyllabus(
                id="later", name="Análisis", start_date="2026-08-01",
                virtual_class_url=url,
                class_schedule=[ClassScheduleEntry(5, "08:00", "10:00")],
            ),
            SubjectSyllabus(
                id="sooner", name="Zzz del martes", start_date="2026-08-01",
                virtual_class_url=url,
                class_schedule=[ClassScheduleEntry(2, "08:00", "10:00")],
            ),
            SubjectSyllabus(
                id="same-day-later", name="Aaa del martes", start_date="2026-08-01",
                virtual_class_url=url,
                class_schedule=[ClassScheduleEntry(2, "18:00", "20:00")],
            ),
            SubjectSyllabus(
                id="today", name="Zoología", start_date="2026-08-01",
                virtual_class_url=url,
                class_schedule=[
                    ClassScheduleEntry(1, "09:00", "10:00"),
                    ClassScheduleEntry(1, "18:00", "20:00"),
                    ClassScheduleEntry(3, "10:00", "12:00"),
                ],
            ),
            SubjectSyllabus(
                id="no-link", name="Sin enlace", start_date="2026-08-01"
            ),
            SubjectSyllabus(
                id="ended", name="Finalizada", start_date="2026-01-01",
                end_date="2026-02-01", virtual_class_url=url,
            ),
        ]
        # Una entrada duplicada con el mismo ID simula datos heredados corruptos.
        subjects.append(subjects[1])

        classes = generate_virtual_classes(subjects, today)
        self.assertEqual(
            [item["subject_id"] for item in classes],
            ["today", "sooner", "same-day-later", "later"]
        )
        self.assertEqual(classes[0]["today_times"], ["09:00–10:00", "18:00–20:00"])
        self.assertEqual(classes[1]["next_day_offset"], 1)
        self.assertEqual(classes[1]["next_start_time"], "08:00")
        self.assertEqual(classes[2]["next_start_time"], "18:00")
        self.assertEqual(classes[3]["next_day_offset"], 4)

    @patch("backend.subject_actions.read_subjects")
    def test_copy_lookup_uses_subject_id_and_returns_exact_url(self, read_subjects):
        url = "https://meet.example.edu/join?key=a&token=b=c#room"
        read_subjects.return_value = [SubjectSyllabus(
            id="safe-id", name="Datos", start_date="2026-08-01",
            virtual_class_url=url,
        )]
        self.assertEqual(virtual_class_url_for_subject("safe-id"), url)
        self.assertIsNone(virtual_class_url_for_subject("safe-id; bash -c whoami"))

    @patch("backend.subject_actions.read_subjects")
    def test_copy_writes_exact_url_to_real_qt_clipboard(self, read_subjects):
        from PyQt6.QtGui import QGuiApplication

        url = "https://meet.example.edu/join?key=a&token=b=c#room"
        read_subjects.return_value = [SubjectSyllabus(
            id="safe-id", name="Datos", start_date="2026-08-01",
            virtual_class_url=url,
        )]
        qt_app = QGuiApplication.instance() or QGuiApplication(["clipboard-test"])
        self.assertEqual(copy_virtual_class_link("safe-id"), 0)
        self.assertEqual(qt_app.clipboard().text(), url)


if __name__ == "__main__":
    unittest.main()

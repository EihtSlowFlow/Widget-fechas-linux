import unittest
from datetime import date
from backend.models import SubjectSyllabus, ClassScheduleEntry
from backend.fechas_sync import is_subject_active, generate_weekly_schedule

class TestWeeklySchedule(unittest.TestCase):

    def test_is_subject_active(self):
        # Active subject, no syllabus, fallback 16 weeks
        subj1 = SubjectSyllabus(name="Subj 1", start_date="2026-06-01")
        self.assertTrue(is_subject_active(subj1, date(2026, 6, 1)))
        self.assertTrue(is_subject_active(subj1, date(2026, 9, 15))) # ~15 weeks
        self.assertFalse(is_subject_active(subj1, date(2026, 12, 1))) # >16 weeks

        # Future subject
        subj2 = SubjectSyllabus(name="Subj 2", start_date="2026-12-01")
        self.assertFalse(is_subject_active(subj2, date(2026, 6, 1)))

        # Finished subject (using end_date)
        subj3 = SubjectSyllabus(name="Subj 3", start_date="2026-01-01", end_date="2026-03-01")
        self.assertTrue(is_subject_active(subj3, date(2026, 2, 1)))
        self.assertFalse(is_subject_active(subj3, date(2026, 4, 1)))

    def test_generate_weekly_schedule(self):
        subj_a = SubjectSyllabus(
            name="Materia A",
            start_date="2026-06-01",
            id="a",
            class_schedule=[
                ClassScheduleEntry(day_of_week=1, start_time="10:00", end_time="12:00", location="Aula 1"),
                ClassScheduleEntry(day_of_week=3, start_time="14:00", end_time="16:00", location="Aula 2")
            ]
        )
        subj_b = SubjectSyllabus(
            name="Materia B",
            start_date="2026-06-01",
            id="b",
            class_schedule=[
                ClassScheduleEntry(day_of_week=1, start_time="08:00", end_time="10:00", location="")
            ]
        )
        
        # Materia inactiva no debe aparecer
        subj_c = SubjectSyllabus(
            name="Materia C",
            start_date="2026-12-01",
            id="c",
            class_schedule=[
                ClassScheduleEntry(day_of_week=1, start_time="18:00", end_time="20:00", location="")
            ]
        )

        today = date(2026, 6, 15)
        schedule = generate_weekly_schedule([subj_a, subj_b, subj_c], today)
        
        self.assertEqual(len(schedule), 3) # A (Monday), B (Monday), A (Wednesday)
        
        # Ordenamiento: dia 1, luego 08:00 (B) antes que 10:00 (A)
        self.assertEqual(schedule[0]["subject_id"], "b")
        self.assertEqual(schedule[0]["start_time"], "08:00")
        
        self.assertEqual(schedule[1]["subject_id"], "a")
        self.assertEqual(schedule[1]["start_time"], "10:00")
        self.assertEqual(schedule[1]["day_of_week"], 1)

        self.assertEqual(schedule[2]["subject_id"], "a")
        self.assertEqual(schedule[2]["day_of_week"], 3)

if __name__ == "__main__":
    unittest.main()

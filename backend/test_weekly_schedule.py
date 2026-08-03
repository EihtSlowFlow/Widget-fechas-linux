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

    def test_find_schedule_overlaps(self):
        from backend.fechas_sync import find_schedule_overlaps
        
        entries = [
            {"day_of_week": 1, "start_time": "08:00", "end_time": "10:00", "subject_name": "A", "subject_id": "a"},
            {"day_of_week": 1, "start_time": "09:00", "end_time": "11:00", "subject_name": "B", "subject_id": "b"}, # Overlaps with A
            {"day_of_week": 1, "start_time": "10:00", "end_time": "12:00", "subject_name": "C", "subject_id": "c"}, # Contiguous with A, overlaps with B
            {"day_of_week": 1, "start_time": "13:00", "end_time": "15:00", "subject_name": "D", "subject_id": "d"},
            {"day_of_week": 2, "start_time": "08:00", "end_time": "10:00", "subject_name": "E", "subject_id": "e"}, # Different day
            {"day_of_week": 1, "start_time": "13:30", "end_time": "14:30", "subject_name": "F", "subject_id": "f"}  # Contained in D
        ]
        
        overlaps = find_schedule_overlaps(entries)
        
        # A and B overlap
        self.assertTrue(any(e1["subject_id"] == "a" and e2["subject_id"] == "b" for e1, e2 in overlaps))
        # B and C overlap
        self.assertTrue(any(e1["subject_id"] == "b" and e2["subject_id"] == "c" for e1, e2 in overlaps))
        # A and C do NOT overlap (contiguous: 10:00 <= 10:00)
        self.assertFalse(any((e1["subject_id"] == "a" and e2["subject_id"] == "c") or (e1["subject_id"] == "c" and e2["subject_id"] == "a") for e1, e2 in overlaps))
        # D and F overlap (contained)
        self.assertTrue(any(e1["subject_id"] == "d" and e2["subject_id"] == "f" for e1, e2 in overlaps))
        
        # E has no overlaps
        self.assertFalse(any(e1["subject_id"] == "e" or e2["subject_id"] == "e" for e1, e2 in overlaps))

    def test_future_subject_internal_overlap(self):
        from backend.fechas_sync import find_schedule_overlaps, generate_weekly_schedule
        
        # Simula una materia futura (inactiva) que el usuario está editando
        # y le asigna dos horarios que se superponen entre sí.
        subj_future = SubjectSyllabus(
            name="Futura",
            start_date="2026-12-01",
            id="fut",
            class_schedule=[
                ClassScheduleEntry(day_of_week=1, start_time="08:00", end_time="10:00", location=""),
                ClassScheduleEntry(day_of_week=1, start_time="09:00", end_time="11:00", location="")
            ]
        )
        
        today = date(2026, 6, 1)
        
        # generate_weekly_schedule ignora las materias futuras
        schedule_list = generate_weekly_schedule([subj_future], today)
        self.assertEqual(len(schedule_list), 0)
        
        # Pero la lógica de validación (del diálogo) fuerza la inserción de los horarios editados
        for entry in subj_future.class_schedule:
            schedule_list.append({
                "day_of_week": entry.day_of_week,
                "start_time": entry.start_time,
                "end_time": entry.end_time,
                "subject_id": subj_future.id,
                "subject_name": subj_future.name,
            })
            
        overlaps = find_schedule_overlaps(schedule_list)
        self.assertEqual(len(overlaps), 1)
        
if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date
from backend.models import AcademicPeriod, SubjectSyllabus, SyllabusUnit
from backend.academic_weeks import (
    academic_week_number,
    academic_week_range,
    subjects_for_academic_week,
    events_for_date_range
)

class TestAcademicPeriod(unittest.TestCase):
    def test_invalid_name(self):
        with self.assertRaises(ValueError):
            AcademicPeriod.from_dict({"name": "", "start_date": "2026-03-09"})
        with self.assertRaises(ValueError):
            AcademicPeriod.from_dict({"name": None, "start_date": "2026-03-09"})

    def test_unknown_fields_tolerance(self):
        # El modelo debe ignorar campos adicionales no esperados
        data = {
            "name": "Test Extra Fields",
            "start_date": "2026-03-09",
            "campo_fantasma": "valor_ignorado",
            "otro_mas": 123
        }
        period = AcademicPeriod.from_dict(data)
        self.assertEqual(period.name, "Test Extra Fields")
        self.assertEqual(period.start_date, "2026-03-09")

    def test_invalid_start_date(self):
        # Martes 2026-03-10
        with self.assertRaises(ValueError):
            AcademicPeriod.from_dict({"name": "Test", "start_date": "2026-03-10"})

    def test_invalid_end_date(self):
        # End date < start date
        with self.assertRaises(ValueError):
            AcademicPeriod.from_dict({
                "name": "Test",
                "start_date": "2026-03-09",
                "end_date": "2026-03-08"
            })


class TestAcademicWeeks(unittest.TestCase):
    def setUp(self):
        self.period = AcademicPeriod(
            name="1er Cuatrimestre 2026",
            start_date="2026-03-09", # Lunes
            end_date="2026-06-28"
        )
        self.period_no_end = AcademicPeriod(
            name="1er Cuatrimestre 2026 (sin fin)",
            start_date="2026-03-09"
        )

    def test_academic_week_number(self):
        # Mismo dia que inicia
        self.assertEqual(academic_week_number(date(2026, 3, 9), self.period), 1)
        # Final de la semana 1
        self.assertEqual(academic_week_number(date(2026, 3, 15), self.period), 1)
        # Principio de semana 2
        self.assertEqual(academic_week_number(date(2026, 3, 16), self.period), 2)
        # Antes del inicio
        self.assertIsNone(academic_week_number(date(2026, 3, 8), self.period))
        # Despues del fin
        self.assertIsNone(academic_week_number(date(2026, 6, 29), self.period))

    def test_academic_week_number_no_end(self):
        # 16 weeks * 7 = 112 days. 112 - 1 = 111 days.
        # start: 2026-03-09. +111 days = 2026-06-28.
        self.assertEqual(academic_week_number(date(2026, 6, 28), self.period_no_end), 16)
        self.assertIsNone(academic_week_number(date(2026, 6, 29), self.period_no_end))

    def test_leap_year(self):
        # 2024 es bisiesto, 26 de feb es lunes
        period_leap = AcademicPeriod("Bisiesto", "2024-02-26")
        self.assertEqual(academic_week_number(date(2024, 2, 29), period_leap), 1)
        self.assertEqual(academic_week_number(date(2024, 3, 1), period_leap), 1)
        self.assertEqual(academic_week_number(date(2024, 3, 4), period_leap), 2)

    def test_cross_month_and_year(self):
        # Inicia 28 de dic 2026 (lunes)
        period_ny = AcademicPeriod("Fin de año", "2026-12-28")
        self.assertEqual(academic_week_number(date(2026, 12, 31), period_ny), 1)
        self.assertEqual(academic_week_number(date(2027, 1, 1), period_ny), 1)
        self.assertEqual(academic_week_number(date(2027, 1, 4), period_ny), 2)

    def test_academic_week_range(self):
        self.assertEqual(
            academic_week_range(1, self.period),
            (date(2026, 3, 9), date(2026, 3, 15))
        )
        self.assertEqual(
            academic_week_range(2, self.period),
            (date(2026, 3, 16), date(2026, 3, 22))
        )
        self.assertIsNone(academic_week_range(0, self.period))

        # Out of bounds (period has 16 weeks max)
        self.assertIsNone(academic_week_range(17, self.period))
        # 16th week should be fine (ends June 28)
        self.assertIsNotNone(academic_week_range(16, self.period))

    def test_academic_week_range_clamps_partial_final_week(self):
        partial_period = AcademicPeriod(
            name="Período parcial",
            start_date="2026-03-09",
            end_date="2026-03-18",
        )
        self.assertEqual(
            academic_week_range(2, partial_period),
            (date(2026, 3, 16), date(2026, 3, 22)),
        )

    def test_subjects_for_academic_week(self):
        subjects = [
            SubjectSyllabus(
                name="Matemática",
                start_date="2026-03-09",
                units=[
                    SyllabusUnit(name="Unidad 1", weeks=[1, 2], contents=["A", "B"]),
                    SyllabusUnit(name="Unidad 2", weeks=[3], contents=["C"])
                ]
            ),
            SubjectSyllabus(
                name="Física",
                start_date="2026-03-09",
                units=[
                    SyllabusUnit(name="Cinemática", weeks=[1], contents=["D"])
                ]
            ),
            SubjectSyllabus(
                name="Química",
                start_date="2026-03-09",
                units=[
                    SyllabusUnit(name="Orgánica", weeks=[1], contents=["C1", "C2"]),
                    SyllabusUnit(name="Inorgánica", weeks=[1], contents=[]), # Misma semana, sin contenidos
                    SyllabusUnit(name="No consecutiva", weeks=[1, 5], contents=["C3"])
                ]
            )
        ]

        w1 = subjects_for_academic_week(subjects, 1)
        self.assertEqual(len(w1), 3)
        self.assertEqual(w1[0]["subject_name"], "Matemática")
        self.assertEqual(len(w1[0]["units"]), 1)
        self.assertEqual(w1[0]["units"][0]["name"], "Unidad 1")
        self.assertEqual(w1[1]["subject_name"], "Física")

        # Test Química (multiple units in same week, empty contents)
        quimica_w1 = w1[2]["units"]
        self.assertEqual(len(quimica_w1), 3)
        self.assertEqual(quimica_w1[0]["name"], "Orgánica")
        self.assertEqual(quimica_w1[1]["name"], "Inorgánica")
        self.assertEqual(len(quimica_w1[1]["contents"]), 0)
        self.assertEqual(quimica_w1[2]["name"], "No consecutiva")

        w2 = subjects_for_academic_week(subjects, 2)
        self.assertEqual(len(w2), 1)
        self.assertEqual(w2[0]["subject_name"], "Matemática")
        self.assertEqual(w2[0]["units"][0]["name"], "Unidad 1")

        w4 = subjects_for_academic_week(subjects, 4)
        self.assertEqual(len(w4), 0)

    def test_events_for_date_range(self):
        events = [
            {"title": "Examen 1", "due_date": "2026-03-15T10:00:00", "is_manual": False, "is_completed": True},
            {"title": "Entrega", "due_date": "2026-03-18T23:59:00", "is_manual": True},
            {"title": "Inscripciones", "start_date": "2026-03-10T00:00:00", "due_date": "2026-03-16T23:59:00", "is_manual": False},
            {"title": "Fuera de rango", "due_date": "2026-04-01T10:00:00"},
            {"title": "Sin due_date", "start_date": "2026-03-15T10:00:00"}, # ignorado
            {"title": "Fecha inválida", "due_date": "invalid"} # ignorado
        ]

        # Semana 1: 09 al 15
        w1 = events_for_date_range(events, date(2026, 3, 9), date(2026, 3, 15))
        titles_w1 = [e["title"] for e in w1]
        self.assertIn("Examen 1", titles_w1)
        self.assertIn("Inscripciones", titles_w1) # del 10 al 16, choca con [09, 15]
        self.assertNotIn("Entrega", titles_w1)

        # Test order
        # due_dates: Inscripciones (16) vs Examen 1 (15) -> Examen 1 comes first
        self.assertEqual(titles_w1[0], "Examen 1")
        self.assertEqual(titles_w1[1], "Inscripciones")

        # Semana 2: 16 al 22
        w2 = events_for_date_range(events, date(2026, 3, 16), date(2026, 3, 22))
        titles_w2 = [e["title"] for e in w2]
        self.assertNotIn("Examen 1", titles_w2)
        self.assertIn("Inscripciones", titles_w2)
        self.assertIn("Entrega", titles_w2)

        # Test order: Inscripciones (due 16) vs Entrega (due 18) -> Inscripciones first
        self.assertEqual(titles_w2[0], "Inscripciones")
        self.assertEqual(titles_w2[1], "Entrega")

if __name__ == '__main__':
    unittest.main()

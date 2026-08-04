import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from datetime import date, timedelta
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QDate
import sys

# QApplication is needed for PyQt testing, using offscreen to avoid CI errors
app = QApplication.instance() or QApplication(sys.argv)

from app.views.academic_calendar_widget import AcademicCalendarWidget
from app.views.calendar_view import CalendarView
from backend.models import AcademicPeriod, SubjectSyllabus, SyllabusUnit

class TestAcademicCalendarWidget(unittest.TestCase):
    def setUp(self):
        self.widget = AcademicCalendarWidget()
        self.period = AcademicPeriod(
            name="Test",
            start_date="2026-08-03", # Lunes
            end_date="2026-11-22"
        )
        
    def test_grid_elements(self):
        """Verifica 42 días y 6 botones de semana"""
        self.assertEqual(len(self.widget._week_buttons), 6)
        self.assertEqual(len(self.widget._day_buttons), 42)

    def test_month_transition(self):
        """Prueba de inicialización y cambio de mes dic -> ene"""
        self.widget.show_month(2025, 12)
        
        # El 1 de dic 2025 es Lunes
        # La primer fila empieza el 1 de dic
        first_btn = self.widget._day_buttons[0]
        self.assertEqual(first_btn.property("cell_date"), date(2025, 12, 1))
        
        self.widget._next_month() # Ene 2026
        # El 1 de ene 2026 es Jueves. Lunes anterior es 29 de dic 2025.
        first_btn_ene = self.widget._day_buttons[0]
        self.assertEqual(first_btn_ene.property("cell_date"), date(2025, 12, 29))

    def test_out_of_bounds_week(self):
        """Verifica que la semana quede deshabilitada fuera del período."""
        self.widget.set_academic_period(self.period)
        
        # Agosto 2026: primer semana es la del 27 de julio (fuera de periodo)
        self.widget.show_month(2026, 8)
        
        first_week_btn = self.widget._week_buttons[0]
        self.assertEqual(first_week_btn.text(), "S -")
        self.assertFalse(first_week_btn.isEnabled())
        
        second_week_btn = self.widget._week_buttons[1] # 3 de Agosto
        self.assertEqual(second_week_btn.text(), "Sem 1")
        self.assertTrue(second_week_btn.isEnabled())


class TestCalendarViewIntegration(unittest.TestCase):
    def setUp(self):
        self.view = CalendarView()
        self.period = AcademicPeriod(
            name="Test",
            start_date="2026-08-03",
        )
        self.subjects = [
            SubjectSyllabus(
                name="Bases de Datos",
                start_date="2026-08-03",
                units=[
                    SyllabusUnit(name="Unidad 1", weeks=[1], contents=["Triggers", "Vistas"])
                ]
            )
        ]

    def test_set_data_integration(self):
        # Asegurar que empezamos la vista en la semana 1
        self.view._selected_monday = date(2026, 8, 3)
        self.view.set_data([], self.subjects, self.period)
        
        # Comprobar el texto renderizado en el panel de detalle
        # Buscamos en el _detail_layout los QLabels
        rendered_texts = []
        for i in range(self.view._detail_layout.count()):
            item = self.view._detail_layout.itemAt(i)
            if item and item.widget():
                try:
                    rendered_texts.append(item.widget().text())
                except AttributeError:
                    pass
                    
        full_text = "\n".join(rendered_texts)
        
        self.assertIn("Bases de Datos", full_text)
        self.assertIn("• Triggers", full_text)
        self.assertIn("• Vistas", full_text)
        self.assertNotIn("\\n", full_text)

if __name__ == '__main__':
    unittest.main()

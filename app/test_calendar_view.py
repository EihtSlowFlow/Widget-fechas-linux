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

    def test_day_click_updates_selected_week(self):
        self.view.set_data([], self.subjects, self.period)
        self.view._calendar.show_month(2026, 8)
        
        # Click on 7th cell (which should be August 2nd, Sunday. Actually, grid starts July 27)
        # The 7th cell is index 6. July 27 + 6 days = Aug 2 (Sunday).
        # Week starts on July 27.
        # But wait, let's click on index 7 (Aug 3, Monday).
        self.view._calendar._on_day_clicked(7)

        self.assertEqual(
            self.view._selected_monday,
            date(2026, 8, 3),
        )
        
    def test_events_spanning_multiple_weeks(self):
        events = [
            {"title": "Largo", "start_date": "2026-08-04T00:00:00", "due_date": "2026-08-14T23:59:00"}
        ]
        # Set to week 1 (Aug 3 - Aug 9)
        self.view._selected_monday = date(2026, 8, 3)
        self.view.set_data(events, [], self.period)
        
        def get_all_texts(layout):
            texts = []
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    w = item.widget()
                    try:
                        texts.append(w.text())
                    except AttributeError:
                        pass
                    # If it's an EventCard or similar, check children
                    from PyQt6.QtWidgets import QLabel
                    for child in w.findChildren(QLabel):
                        texts.append(child.text())
            return "\n".join(texts)
            
        texts_w1 = get_all_texts(self.view._detail_layout)
        self.assertIn("Largo", texts_w1)
        self.assertIn("Rango: 4/08 al 14/08", texts_w1)
        
        # Switch to week 2 (Aug 10 - Aug 16)
        self.view._on_week_clicked(date(2026, 8, 10), date(2026, 8, 16))
        
        texts_w2 = get_all_texts(self.view._detail_layout)
        self.assertIn("Largo", texts_w2)
        # Rango should still be there
        self.assertIn("Rango: 4/08 al 14/08", texts_w2)

if __name__ == '__main__':
    unittest.main()

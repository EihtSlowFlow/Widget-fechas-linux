import unittest
from datetime import date, timedelta
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QDate
import sys

# QApplication is needed for PyQt testing
app = QApplication(sys.argv)

from app.views.academic_calendar_widget import AcademicCalendarWidget
from app.views.calendar_view import CalendarView
from backend.models import AcademicPeriod

class TestAcademicCalendarWidget(unittest.TestCase):
    def setUp(self):
        self.widget = AcademicCalendarWidget()
        
    def test_six_rows_visible(self):
        """Verifica que el widget crea exactamente 6 botones de semanas."""
        self.assertEqual(len(self.widget._week_buttons), 6)

    def test_grid_start_and_end(self):
        """Verifica el cálculo del lunes de la primera fila."""
        # Forzamos una fecha específica: Agosto 2026
        # Agosto 2026 empieza en sábado.
        # El lunes anterior a eso es 27 de julio de 2026.
        self.widget._update_weeks(2026, 8)
        
        first_btn = self.widget._week_buttons[0]
        first_monday = first_btn.property("row_monday")
        self.assertEqual(first_monday, date(2026, 7, 27))
        
        last_btn = self.widget._week_buttons[5]
        last_monday = last_btn.property("row_monday")
        self.assertEqual(last_monday, date(2026, 8, 31))

    def test_week_selection(self):
        """Verifica que hacer clic en una semana cambia la selección del calendario."""
        self.widget._update_weeks(2026, 8)
        
        # Simulamos clic en el segundo botón (semana del 3 de agosto)
        self.widget._on_week_clicked(1)
        
        # El calendario debería tener seleccionado el 3 de agosto
        sel_date = self.widget.selectedDate().toPyDate()
        self.assertEqual(sel_date, date(2026, 8, 3))


class TestCalendarView(unittest.TestCase):
    def setUp(self):
        self.view = CalendarView()

    def test_initialization(self):
        """Verifica que los paneles iniciales están presentes."""
        self.assertIsNotNone(self.view._calendar)
        self.assertIsNotNone(self.view._day_label)
        
    def test_empty_state_without_period(self):
        """Verifica el estado vacío cuando no hay período configurado."""
        self.view.set_data([], [], None)
        text = self.view._day_label.text()
        self.assertIn("Configurá el período académico", text)

if __name__ == '__main__':
    unittest.main()

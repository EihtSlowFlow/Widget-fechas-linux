import unittest
from app.views.calendar_view import highest_incomplete_urgency

class TestCalendarView(unittest.TestCase):
    def test_highest_incomplete_urgency(self):
        # Todos completados -> None
        events_completed = [
            {"is_completed": True, "urgency": "red"},
            {"is_completed": True, "urgency": "orange"}
        ]
        self.assertIsNone(highest_incomplete_urgency(events_completed))

        # Mezcla de completados e incompletos
        events_mixed = [
            {"is_completed": True, "urgency": "red"},
            {"is_completed": False, "urgency": "green"},
            {"is_completed": False, "urgency": "yellow"}
        ]
        # El mayor de los no completados es yellow
        self.assertEqual(highest_incomplete_urgency(events_mixed), "yellow")

        # Prioridad correcta: red > orange > yellow > green
        events_priority = [
            {"is_completed": False, "urgency": "green"},
            {"is_completed": False, "urgency": "orange"},
            {"is_completed": False, "urgency": "yellow"}
        ]
        self.assertEqual(highest_incomplete_urgency(events_priority), "orange")
        
        # Con red
        events_red = [
            {"is_completed": False, "urgency": "green"},
            {"is_completed": False, "urgency": "red"}
        ]
        self.assertEqual(highest_incomplete_urgency(events_red), "red")
        
        # Lista vacía -> None
        self.assertIsNone(highest_incomplete_urgency([]))

if __name__ == "__main__":
    unittest.main()

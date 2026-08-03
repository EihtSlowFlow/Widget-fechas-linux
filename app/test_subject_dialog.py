import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication

# Set offscreen platform for CI environments before creating QApplication
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
app = QApplication.instance() or QApplication(sys.argv)

from app.dialogs.subject_dialog import SubjectDialog

class TestSubjectDialog(unittest.TestCase):
    def test_legacy_visibility(self):
        # Without legacy syllabus
        data_new = {
            "name": "Test",
            "start_date": "2026-06-01",
            "units": [{"name": "U1", "weeks": [1], "contents": ["A"]}]
        }
        dlg1 = SubjectDialog(subject_data=data_new)
        self.assertTrue(dlg1._legacy_container.isHidden(), "Contenedor legado debe estar oculto si no hay syllabus")
        
        # With legacy syllabus
        data_legacy = {
            "name": "Test",
            "start_date": "2026-06-01",
            "syllabus": [{"start_week": 1, "end_week": 1, "topic": "Legacy"}]
        }
        dlg2 = SubjectDialog(subject_data=data_legacy)
        self.assertFalse(dlg2._legacy_container.isHidden(), "Contenedor legado debe ser visible si hay syllabus")
        
    def test_preserve_syllabus_when_units_present(self):
        data = {
            "name": "Test",
            "start_date": "2026-06-01",
            "syllabus": [{"start_week": 1, "end_week": 1, "topic": "Legacy"}],
            "units": [{"name": "U1", "weeks": [1], "contents": ["New"]}]
        }
        dlg = SubjectDialog(subject_data=data)
        
        out = dlg.get_subject_data()
        
        # Ensure syllabus is preserved
        self.assertEqual(len(out["syllabus"]), 1)
        self.assertEqual(out["syllabus"][0]["topic"], "Legacy")

if __name__ == "__main__":
    unittest.main()

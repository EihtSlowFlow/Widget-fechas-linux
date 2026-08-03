import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication

# Set offscreen platform for CI environments before creating QApplication
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
app = QApplication.instance() or QApplication(sys.argv)

from app.dialogs.subject_dialog import SubjectDialog

class TestSubjectDialog(unittest.TestCase):
    def test_ui_initialization(self):
        data_new = {
            "name": "Test",
            "start_date": "2026-06-01",
            "units": [{"name": "U1", "weeks": [1], "contents": ["A"]}]
        }
        dlg1 = SubjectDialog(subject_data=data_new)
        self.assertEqual(dlg1._name_edit.text(), "Test")

        output = dlg1.get_subject_data()
        self.assertNotIn("syllabus", output)
        self.assertEqual(len(output["units"]), 1)

if __name__ == "__main__":
    unittest.main()

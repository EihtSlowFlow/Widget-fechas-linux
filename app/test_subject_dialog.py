import os
import sys
import unittest
from unittest.mock import patch
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

    def test_virtual_class_url_round_trip(self):
        url = "https://meet.example.edu/join?token=a&room=b=c#start"
        dialog = SubjectDialog(subject_data={
            "name": "Test", "start_date": "2026-06-01",
            "virtual_class_url": url,
            "virtual_class_platform": "google_meet",
        })
        self.assertEqual(dialog._virtual_class_url_edit.text(), url)
        self.assertEqual(dialog.get_subject_data()["virtual_class_url"], url)
        self.assertEqual(
            dialog.get_subject_data()["virtual_class_platform"], "google_meet"
        )

    @patch("app.dialogs.subject_dialog.QMessageBox.warning")
    @patch("app.dialogs.subject_dialog.QDesktopServices.openUrl", return_value=False)
    def test_try_link_reports_desktop_open_failure(self, open_url, warning):
        dialog = SubjectDialog(subject_data={
            "name": "Test", "start_date": "2026-06-01",
            "virtual_class_url": "https://meet.example.edu/room",
            "virtual_class_platform": "google_meet",
        })
        dialog._test_virtual_link()
        open_url.assert_called_once()
        warning.assert_called_once()

if __name__ == "__main__":
    unittest.main()

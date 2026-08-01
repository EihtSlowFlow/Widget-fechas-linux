import unittest
from datetime import date
from unittest.mock import patch

from backend.models import SubjectSyllabus, SyllabusEntry
from backend.fechas_sync import process_subjects


class TestSubjectSyllabus(unittest.TestCase):

    def setUp(self):
        self.syllabus = [
            SyllabusEntry(start_week=1, end_week=2, topic="Tema 1: Intro"),
            SyllabusEntry(start_week=2, end_week=4, topic="Tema 2: Bases"),
            SyllabusEntry(start_week=5, end_week=5, topic="Tema 3: Avanzado"),
        ]
        self.subject = SubjectSyllabus(
            name="Matemática",
            start_date="2026-06-01",
            id="test-id-123",
            syllabus=self.syllabus
        )

    @patch("backend.fechas_sync.read_subjects")
    def test_day_1_week_1(self, mock_read):
        mock_read.return_value = [self.subject]
        today = date(2026, 6, 1)
        results = process_subjects(today)
        
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.week_number, 1)
        self.assertEqual(res.day_of_week, 1)
        self.assertEqual(res.topics, ["Tema 1: Intro"])
        self.assertEqual(res.week_start, "2026-06-01")

    @patch("backend.fechas_sync.read_subjects")
    def test_day_6_week_1(self, mock_read):
        mock_read.return_value = [self.subject]
        today = date(2026, 6, 6) # elapsed=5 -> day_of_week=6
        results = process_subjects(today)
        
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.week_number, 1)
        self.assertEqual(res.day_of_week, 6)
        self.assertEqual(res.topics, ["Tema 1: Intro"])

    @patch("backend.fechas_sync.read_subjects")
    def test_day_7_week_1(self, mock_read):
        mock_read.return_value = [self.subject]
        today = date(2026, 6, 7) # elapsed=6 -> day_of_week=7
        results = process_subjects(today)
        
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.week_number, 1)
        self.assertEqual(res.day_of_week, 7)
        self.assertEqual(res.topics, ["Tema 1: Intro"])

    @patch("backend.fechas_sync.read_subjects")
    def test_day_8_week_2(self, mock_read):
        mock_read.return_value = [self.subject]
        today = date(2026, 6, 8) # elapsed=7 -> week=2, day=1
        results = process_subjects(today)
        
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.week_number, 2)
        self.assertEqual(res.day_of_week, 1)
        # Week 2 has both Tema 1 and Tema 2 due to overlap
        self.assertEqual(res.topics, ["Tema 1: Intro", "Tema 2: Bases"])

    @patch("backend.fechas_sync.read_subjects")
    def test_before_start_date(self, mock_read):
        mock_read.return_value = [self.subject]
        today = date(2026, 5, 30) # 2 days before start
        results = process_subjects(today)
        self.assertEqual(len(results), 0)

    @patch("backend.fechas_sync.read_subjects")
    def test_first_last_day_last_week(self, mock_read):
        mock_read.return_value = [self.subject]
        # max_end_week is 5 (starts at day 29 of course)
        # Week 5 start day (elapsed_days = 28)
        today = date(2026, 6, 29) 
        res1 = process_subjects(today)
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0].week_number, 5)
        self.assertEqual(res1[0].day_of_week, 1)

        # Week 5 end day (elapsed_days = 34)
        today = date(2026, 7, 5)
        res2 = process_subjects(today)
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0].week_number, 5)
        self.assertEqual(res2[0].day_of_week, 7)

    @patch("backend.fechas_sync.read_subjects")
    def test_after_last_topic(self, mock_read):
        mock_read.return_value = [self.subject]
        today = date(2026, 7, 6) # elapsed_days = 35 -> week 6
        results = process_subjects(today)
        self.assertEqual(len(results), 0)

    @patch("backend.fechas_sync.read_subjects")
    def test_empty_syllabus(self, mock_read):
        subject_empty = SubjectSyllabus(name="Empty", start_date="2026-06-01", id="empty", syllabus=[])
        mock_read.return_value = [subject_empty]
        today = date(2026, 6, 1)
        results = process_subjects(today)
        self.assertEqual(len(results), 0)

    @patch("backend.fechas_sync.read_subjects")
    def test_corrupt_entry_valid_kept(self, mock_read):
        data = {
            "name": "Corrupt",
            "start_date": "2026-06-01",
            "id": "1",
            "syllabus": [
                {"start_week": "hola", "end_week": 2, "topic": "bad"},
                {"start_week": 1, "end_week": 1, "topic": "good"}
            ]
        }
        subj = SubjectSyllabus.from_dict(data)
        mock_read.return_value = [subj]
        today = date(2026, 6, 1)
        results = process_subjects(today)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].topics, ["good"])

    @patch("backend.fechas_sync.read_subjects")
    def test_corrupt_subject_valid_kept(self, mock_read):
        import backend.cache
        from unittest.mock import patch
        
        # Test full chain starting from cache
        with patch("backend.cache._read_json") as mock_json:
            mock_json.return_value = [
                {"name": "", "start_date": "bad-date"}, # Corrupt
                {"name": "Valid", "start_date": "2026-06-01", "syllabus": [{"start_week": 1, "end_week": 1, "topic": "a"}]}
            ]
            subjects = backend.cache.read_subjects()
            self.assertEqual(len(subjects), 1)
            self.assertEqual(subjects[0].name, "Valid")

    def test_pipeline_integration(self):
        import json
        from backend.fechas_sync import sync
        import backend.config
        import tempfile
        import os
        from pathlib import Path
        from unittest.mock import patch
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            data_dir = tmp_path / "data"
            config_dir = tmp_path / "config"
            
            # Use patch to properly override the constants imported into backend.cache
            with patch("backend.config.DATA_DIR", data_dir), \
                 patch("backend.config.CONFIG_DIR", config_dir), \
                 patch("backend.cache.CACHE_FILE", data_dir / "cache.json"), \
                 patch("backend.cache.KNOWN_EVENTS_FILE", data_dir / "known_events.json"), \
                 patch("backend.cache.SEEN_EVENTS_FILE", data_dir / "seen_events.json"), \
                 patch("backend.cache.COMPLETED_EVENTS_FILE", data_dir / "completed_events.json"), \
                 patch("backend.cache.SOURCES_FILE", config_dir / "sources.json"), \
                 patch("backend.cache.MANUAL_EVENTS_FILE", config_dir / "manual_events.json"), \
                 patch("backend.cache.SUBJECTS_FILE", config_dir / "subjects.json"), \
                 patch("backend.config.SUBJECTS_FILE", config_dir / "subjects.json"):
                 
                backend.config.ensure_dirs()
                
                # 1. Write subjects.json
                test_subj = [
                    {
                        "name": "Integration Subject",
                        "start_date": str(date.today()), # Starts today, so week 1
                        "id": "int1",
                        "syllabus": [{"start_week": 1, "end_week": 1, "topic": "Integración"}]
                    }
                ]
                with open(config_dir / "subjects.json", 'w', encoding='utf-8') as f:
                    json.dump(test_subj, f)
                    
                # 2. Provide empty files to avoid external requests or pollution
                with open(config_dir / "sources.json", 'w', encoding='utf-8') as f:
                    json.dump([], f)
                with open(config_dir / "manual_events.json", 'w', encoding='utf-8') as f:
                    json.dump([], f)
                    
                # 3. Run sync
                sync()
                
                # 4. Verify cache.json
                cache_file = data_dir / "cache.json"
                self.assertTrue(cache_file.exists())
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                self.assertIn("current_subjects", cache_data)
                self.assertEqual(len(cache_data["current_subjects"]), 1)
                self.assertEqual(cache_data["current_subjects"][0]["subject_id"], "int1")
                self.assertEqual(cache_data["current_subjects"][0]["week_number"], 1)
                self.assertEqual(cache_data["current_subjects"][0]["topics"], ["Integración"])


if __name__ == "__main__":
    unittest.main()

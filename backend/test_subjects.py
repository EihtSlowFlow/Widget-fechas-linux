import unittest
from datetime import date
from unittest.mock import patch

from backend.models import SubjectSyllabus, SyllabusUnit
from backend.fechas_sync import process_subjects


class TestSubjectSyllabus(unittest.TestCase):

    def setUp(self):
        self.units = [
            SyllabusUnit(name="Unidad 1", weeks=[1, 2], contents=["Tema 1: Intro"]),
            SyllabusUnit(name="Unidad 2", weeks=[2, 3, 4], contents=["Tema 2: Bases"]),
            SyllabusUnit(name="Unidad 3", weeks=[5], contents=["Tema 3: Avanzado"]),
        ]
        self.subject = SubjectSyllabus(
            name="Matemática",
            start_date="2026-06-01",
            id="test-id-123",
            units=self.units
        )

    def test_day_1_week_1(self):
        today = date(2026, 6, 1)
        results = process_subjects([self.subject], today)
        
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.week_number, 1)
        self.assertEqual(res.day_of_week, 1)
        self.assertEqual(res.topics, ["Tema 1: Intro"])
        self.assertEqual(res.week_start, "2026-06-01")

    def test_day_6_week_1(self):
        today = date(2026, 6, 6) # elapsed=5 -> day_of_week=6
        results = process_subjects([self.subject], today)
        
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.week_number, 1)
        self.assertEqual(res.day_of_week, 6)
        self.assertEqual(res.topics, ["Tema 1: Intro"])

    def test_day_7_week_1(self):
        today = date(2026, 6, 7) # elapsed=6 -> day_of_week=7
        results = process_subjects([self.subject], today)
        
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.week_number, 1)
        self.assertEqual(res.day_of_week, 7)
        self.assertEqual(res.topics, ["Tema 1: Intro"])

    def test_day_8_week_2(self):
        today = date(2026, 6, 8) # elapsed=7 -> week=2, day=1
        results = process_subjects([self.subject], today)
        
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.week_number, 2)
        self.assertEqual(res.day_of_week, 1)
        # Week 2 has both Tema 1 and Tema 2 due to overlap
        self.assertEqual(res.topics, ["Tema 1: Intro", "Tema 2: Bases"])

    def test_before_start_date(self):
        today = date(2026, 5, 30) # 2 days before start
        results = process_subjects([self.subject], today)
        self.assertEqual(len(results), 0)

    def test_first_last_day_last_week(self):
        # max_end_week is 5 (starts at day 29 of course)
        # Week 5 start day (elapsed_days = 28)
        today = date(2026, 6, 29) 
        res1 = process_subjects([self.subject], today)
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0].week_number, 5)
        self.assertEqual(res1[0].day_of_week, 1)

        # Week 5 end day (elapsed_days = 34)
        today = date(2026, 7, 5)
        res2 = process_subjects([self.subject], today)
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0].week_number, 5)
        self.assertEqual(res2[0].day_of_week, 7)

    def test_after_last_topic(self):
        today = date(2026, 7, 6) # elapsed_days = 35 -> week 6
        results = process_subjects([self.subject], today)
        self.assertEqual(len(results), 0)

    def test_empty_units(self):
        subject_empty = SubjectSyllabus(name="Empty", start_date="2026-06-01", id="empty", units=[])
        today = date(2026, 6, 1)
        results = process_subjects([subject_empty], today)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].topics, [])

    def test_corrupt_unit_valid_kept(self):
        data = {
            "name": "Corrupt",
            "start_date": "2026-06-01",
            "id": "1",
            "units": [
                {"name": 123, "weeks": [1], "contents": ["bad"]},
                {"name": "Valid", "weeks": [1], "contents": ["good"]}
            ]
        }
        subj = SubjectSyllabus.from_dict(data)
        today = date(2026, 6, 1)
        results = process_subjects([subj], today)
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
                {"name": "Valid", "start_date": "2026-06-01", "units": [{"name": "U1", "weeks": [1], "contents": ["a"]}]}
            ]
            subjects = backend.cache.read_subjects()
            self.assertEqual(len(subjects), 1)
            self.assertEqual(subjects[0].name, "Valid")

    def test_class_schedule_entry_valid(self):
        from backend.models import ClassScheduleEntry
        data = {"day_of_week": 1, "start_time": "08:00", "end_time": "10:00", "location": "Aula 1"}
        entry = ClassScheduleEntry.from_dict(data)
        self.assertEqual(entry.day_of_week, 1)
        self.assertEqual(entry.start_time, "08:00")
        self.assertEqual(entry.end_time, "10:00")
        self.assertEqual(entry.location, "Aula 1")

    def test_class_schedule_entry_invalid_day(self):
        from backend.models import ClassScheduleEntry
        data = {"day_of_week": 8, "start_time": "08:00", "end_time": "10:00"}
        with self.assertRaises(ValueError):
            ClassScheduleEntry.from_dict(data)

    def test_class_schedule_entry_invalid_time(self):
        from backend.models import ClassScheduleEntry
        data = {"day_of_week": 1, "start_time": "25:70", "end_time": "10:00"}
        with self.assertRaises(ValueError):
            ClassScheduleEntry.from_dict(data)

    def test_class_schedule_entry_end_before_start(self):
        from backend.models import ClassScheduleEntry
        data = {"day_of_week": 1, "start_time": "10:00", "end_time": "08:00"}
        with self.assertRaises(ValueError):
            ClassScheduleEntry.from_dict(data)
            
    def test_subject_serialization_with_schedule(self):
        data = {
            "name": "Matemática",
            "start_date": "2026-06-01",
            "id": "test-id-123",
            "end_date": "2026-10-01",
            "class_schedule": [{"day_of_week": 1, "start_time": "08:00", "end_time": "10:00", "location": "Aula 1"}]
        }
        subj = SubjectSyllabus.from_dict(data)
        self.assertEqual(subj.end_date, "2026-10-01")
        self.assertEqual(len(subj.class_schedule), 1)
        
        serialized = subj.to_dict()
        self.assertEqual(serialized["class_schedule"][0]["start_time"], "08:00")

    def test_subject_with_units(self):
        data = {
            "name": "Base de Datos",
            "start_date": "2026-06-01",
            "id": "bd1",
            "units": [
                {"name": "Unidad 1", "weeks": [1, 2, 3], "contents": ["Diseño", "Normalización"]},
                {"name": "Unidad 2", "weeks": [4, 5], "contents": ["Índices"]}
            ]
        }
        subj = SubjectSyllabus.from_dict(data)
        self.assertEqual(len(subj.units), 2)
        self.assertEqual(subj.units[0].name, "Unidad 1")
        self.assertEqual(subj.units[1].weeks, [4, 5])

        serialized = subj.to_dict()
        self.assertEqual(len(serialized["units"]), 2)
        self.assertEqual(serialized["units"][0]["contents"], ["Diseño", "Normalización"])

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
                 patch("backend.config.SUBJECTS_FILE", config_dir / "subjects.json"), \
                 patch("backend.cache.CACHE_LOCK_FILE", data_dir / "cache.lock"):
                 
                backend.config.ensure_dirs()
                
                # 1. Write subjects.json
                test_subj = [
                    {
                        "name": "Integration Subject",
                        "start_date": str(date.today()), # Starts today, so week 1
                        "id": "int1",
                        "units": [{"name": "Unidad 1", "weeks": [1], "contents": ["Integración"]}]
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
                self.assertIn("units", cache_data["current_subjects"][0])
                self.assertEqual(len(cache_data["current_subjects"][0]["units"]), 1)
                self.assertEqual(cache_data["current_subjects"][0]["units"][0]["name"], "Unidad 1")

    def test_cachedata_legacy_format(self):
        from backend.models import CacheData
        # Simulated old cache.json contents without weekly_schedule
        legacy_data = {
            "last_sync": "2026-08-01T10:00:00",
            "sync_status": "ok",
            "events": [{"title": "Examen"}],
            "current_subjects": [{"subject_id": "1"}]
        }
        
        cache = CacheData.from_dict(legacy_data)
        self.assertEqual(cache.last_sync, "2026-08-01T10:00:00")
        self.assertEqual(cache.sync_status, "ok")
        self.assertEqual(len(cache.events), 1)
        self.assertEqual(len(cache.current_subjects), 1)
        # Should gracefully default to empty list instead of failing
        self.assertEqual(cache.weekly_schedule, [])

class TestSyllabusUnit(unittest.TestCase):

    def test_basic_serialization(self):
        data = {
            "name": "1. Nociones avanzadas",
            "weeks": [1, 2, 3, 4],
            "contents": ["Diseño de DB", "Procedimientos almacenados"]
        }
        unit = SyllabusUnit.from_dict(data)
        self.assertEqual(unit.name, "1. Nociones avanzadas")
        self.assertEqual(unit.weeks, [1, 2, 3, 4])
        self.assertEqual(unit.contents, ["Diseño de DB", "Procedimientos almacenados"])
        d = unit.to_dict()
        self.assertEqual(d["name"], "1. Nociones avanzadas")

    def test_name_normalization(self):
        unit = SyllabusUnit.from_dict({"name": "  Unidad 1  ", "weeks": [1]})
        self.assertEqual(unit.name, "Unidad 1")

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            SyllabusUnit.from_dict({"name": "", "weeks": [1]})
        with self.assertRaises(ValueError):
            SyllabusUnit.from_dict({"name": "   ", "weeks": [1]})

    def test_name_none_raises(self):
        with self.assertRaises(ValueError):
            SyllabusUnit.from_dict({"name": None, "weeks": [1]})

    def test_name_int_raises(self):
        with self.assertRaises(ValueError):
            SyllabusUnit.from_dict({"name": 123, "weeks": [1]})

    def test_weeks_deduplication_and_sorting(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": [3, 1, 2, 1, 3]})
        self.assertEqual(unit.weeks, [1, 2, 3])

    def test_weeks_invalid_values_ignored(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": [1, "hola", -1, 0, 2]})
        self.assertEqual(unit.weeks, [1, 2])

    def test_weeks_float_ignored(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": [1, 1.5, 2.9, 3]})
        self.assertEqual(unit.weeks, [1, 3])

    def test_weeks_boolean_rejected(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": [True, False, 2]})
        self.assertEqual(unit.weeks, [2])

    def test_weeks_not_a_list(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": "123"})
        self.assertEqual(unit.weeks, [])

    def test_contents_normalization(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": [1], "contents": ["  Tema 1  ", "", "Tema 2", "  "]})
        self.assertEqual(unit.contents, ["Tema 1", "Tema 2"])

    def test_contents_deduplication(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": [1], "contents": ["A", "B", "A", "C", "B"]})
        self.assertEqual(unit.contents, ["A", "B", "C"])

    def test_contents_not_a_list(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": [1], "contents": "string"})
        self.assertEqual(unit.contents, [])

    def test_contents_non_string_ignored(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": [1], "contents": ["A", 123, None, "B"]})
        self.assertEqual(unit.contents, ["A", "B"])

    def test_unit_without_contents(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": [1]})
        self.assertEqual(unit.contents, [])

    def test_unit_empty_weeks_tolerated(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": []})
        self.assertEqual(unit.weeks, [])

    def test_unknown_fields_tolerated(self):
        unit = SyllabusUnit.from_dict({"name": "U", "weeks": [1], "foo": "bar", "extra": 42})
        self.assertEqual(unit.name, "U")
        self.assertEqual(unit.weeks, [1])

if __name__ == "__main__":
    unittest.main()

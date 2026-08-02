import unittest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from backend.cache import toggle_completed, CACHE_FILE, COMPLETED_EVENTS_FILE
from backend.models import CacheData, AcademicEvent

class TestCacheCompleted(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        
        # Files in the temp dir
        self.cache_file = Path(self.test_dir.name) / "cache.json"
        self.completed_file = Path(self.test_dir.name) / "completed_events.json"
        
        self.patcher_cache_file = patch('backend.cache.CACHE_FILE', self.cache_file)
        self.patcher_cache_file.start()
        
        self.patcher_completed_file = patch('backend.cache.COMPLETED_EVENTS_FILE', self.completed_file)
        self.patcher_completed_file.start()

    def tearDown(self):
        patch.stopall()
        self.test_dir.cleanup()

    def test_toggle_completed_updates_cache_immediately(self):
        # 1. Setup initial cache state with an uncompleted event
        event_id = "test_event_1"
        initial_cache = CacheData(
            events=[
                AcademicEvent(id=event_id, title="Test", due_date="2099-01-01", is_completed=False, source_id="mock", source_name="Mock").to_dict()
            ]
        )
        
        with open(self.cache_file, "w") as f:
            json.dump(initial_cache.to_dict(), f)
            
        with open(self.completed_file, "w") as f:
            json.dump([], f)

        # 2. Toggle completion ON
        result = toggle_completed(event_id)
        self.assertTrue(result, "Event should be marked as completed")
        
        # Verify completed_events.json
        with open(self.completed_file, "r") as f:
            completed_list = json.load(f)
        self.assertIn(event_id, completed_list)
        
        # Verify cache.json is updated immediately
        with open(self.cache_file, "r") as f:
            cache_data = json.load(f)
        self.assertTrue(cache_data["events"][0]["is_completed"])
        
        # 3. Toggle completion OFF
        result = toggle_completed(event_id)
        self.assertFalse(result, "Event should be marked as not completed")
        
        # Verify completed_events.json
        with open(self.completed_file, "r") as f:
            completed_list = json.load(f)
        self.assertNotIn(event_id, completed_list)
        
        # Verify cache.json is updated immediately
        with open(self.cache_file, "r") as f:
            cache_data = json.load(f)
        self.assertFalse(cache_data["events"][0]["is_completed"])

if __name__ == "__main__":
    unittest.main()

import unittest
import os
import json
import tempfile
from pathlib import Path
from backend.cache import (
    delete_manual_event,
    write_manual_events,
    MANUAL_EVENTS_FILE,
    COMPLETED_EVENTS_FILE,
    SEEN_EVENTS_FILE,
    KNOWN_EVENTS_FILE,
    _atomic_write_json
)
from backend.models import AcademicEvent

class TestDeletion(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        # Override paths for testing
        self.original_manual = MANUAL_EVENTS_FILE
        self.original_completed = COMPLETED_EVENTS_FILE
        self.original_seen = SEEN_EVENTS_FILE
        self.original_known = KNOWN_EVENTS_FILE
        
        import backend.cache as cache_module
        cache_module.MANUAL_EVENTS_FILE = Path(os.path.join(self.test_dir.name, "manual_events.json"))
        cache_module.COMPLETED_EVENTS_FILE = Path(os.path.join(self.test_dir.name, "completed_events.json"))
        cache_module.SEEN_EVENTS_FILE = Path(os.path.join(self.test_dir.name, "seen_events.json"))
        cache_module.KNOWN_EVENTS_FILE = Path(os.path.join(self.test_dir.name, "known_events.json"))
        
        # Setup initial state
        events = [
            AcademicEvent(id="ev1", title="Event 1", due_date="2026-08-01", source_id="manual", source_name="Eventos Manuales"),
            AcademicEvent(id="ev2", title="Event 2", due_date="2026-08-02", source_id="manual", source_name="Eventos Manuales")
        ]
        write_manual_events(events)
        
        _atomic_write_json(cache_module.COMPLETED_EVENTS_FILE, ["ev1", "ev3"])
        _atomic_write_json(cache_module.SEEN_EVENTS_FILE, ["ev1", "ev2"])
        _atomic_write_json(cache_module.KNOWN_EVENTS_FILE, {"ev1": "2026-08-01", "ev2": "2026-08-02"})

    def tearDown(self):
        import backend.cache as cache_module
        cache_module.MANUAL_EVENTS_FILE = self.original_manual
        cache_module.COMPLETED_EVENTS_FILE = self.original_completed
        cache_module.SEEN_EVENTS_FILE = self.original_seen
        cache_module.KNOWN_EVENTS_FILE = self.original_known
        self.test_dir.cleanup()

    def test_delete_existing_event(self):
        result = delete_manual_event("ev1")
        self.assertTrue(result)
        
        # Verify it's gone from manual events
        import backend.cache as cache_module
        with open(cache_module.MANUAL_EVENTS_FILE, 'r') as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["id"], "ev2")
            
        # Verify states are cleaned up
        with open(cache_module.COMPLETED_EVENTS_FILE, 'r') as f:
            self.assertNotIn("ev1", json.load(f))
        with open(cache_module.SEEN_EVENTS_FILE, 'r') as f:
            self.assertNotIn("ev1", json.load(f))
        with open(cache_module.KNOWN_EVENTS_FILE, 'r') as f:
            self.assertNotIn("ev1", json.load(f))
            
    def test_delete_nonexistent_event(self):
        with self.assertRaises(ValueError):
            delete_manual_event("ev99")

if __name__ == "__main__":
    unittest.main()

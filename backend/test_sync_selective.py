import unittest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock
from backend.fechas_sync import sync
from backend.models import AcademicEvent, DataSource

class TestSelectiveSync(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        
        # We need to mock caching and fetching to avoid side effects
        self.patcher_fetch = patch('backend.fechas_sync._fetch_events_from_source')
        self.mock_fetch = self.patcher_fetch.start()
        
        self.patcher_sources = patch('backend.fechas_sync.init_default_sources')
        self.mock_sources = self.patcher_sources.start()
        
        self.patcher_read_cache = patch('backend.cache.read_cache')
        self.mock_read_cache = self.patcher_read_cache.start()
        
        self.patcher_write_cache = patch('backend.fechas_sync.write_cache')
        self.mock_write_cache = self.patcher_write_cache.start()
        
        self.patcher_write_sources = patch('backend.fechas_sync.write_sources')
        self.mock_write_sources = self.patcher_write_sources.start()

    def tearDown(self):
        self.patcher_fetch.stop()
        self.patcher_sources.stop()
        self.patcher_read_cache.stop()
        self.patcher_write_cache.stop()
        self.patcher_write_sources.stop()
        self.test_dir.cleanup()

    def test_selective_sync_success(self):
        # Initial sources
        s1 = DataSource(id="moodle", name="Moodle", type="moodle", url="http://moodle", enabled=True)
        s2 = DataSource(id="unrn", name="UNRN", type="ical", url="http://unrn", enabled=True)
        self.mock_sources.return_value = [s1, s2]
        
        # Previous cache
        prev_events = [
            AcademicEvent(id="ev_moodle_1", title="M1", due_date="2026-08-01", source_id="moodle", source_name="Moodle").to_dict(),
            AcademicEvent(id="ev_unrn_1", title="U1", due_date="2026-08-01", source_id="unrn", source_name="UNRN").to_dict()
        ]
        mock_cache = MagicMock()
        mock_cache.events = prev_events
        mock_cache.sync_status = "ok"
        mock_cache.sync_error = None
        self.mock_read_cache.return_value = mock_cache
        
        # Fetch mock for unrn
        new_unrn_event = AcademicEvent(id="ev_unrn_2", title="U2", due_date="2026-08-02", source_id="unrn", source_name="UNRN")
        self.mock_fetch.return_value = ([new_unrn_event], None)
        
        # Execute selective sync
        cache = sync(dry_run=True, source_id="unrn")
        
        # Verify
        self.assertEqual(len(cache.events), 2)
        source_ids = {e["source_id"] for e in cache.events}
        self.assertIn("moodle", source_ids)
        self.assertIn("unrn", source_ids)
        
        # We should have M1 and U2 (U1 was replaced)
        titles = {e["title"] for e in cache.events}
        self.assertIn("M1", titles)
        self.assertIn("U2", titles)
        self.assertNotIn("U1", titles)

if __name__ == "__main__":
    unittest.main()

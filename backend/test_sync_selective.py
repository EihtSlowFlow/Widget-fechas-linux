import unittest
import os
import json
import sys
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
        self.patcher_read_sources = patch('backend.fechas_sync.read_sources')
        self.mock_read_sources = self.patcher_read_sources.start()
        self.mock_sources.return_value = []
        
        self.patcher_read_cache = patch('backend.cache.read_cache')
        self.mock_read_cache = self.patcher_read_cache.start()
        
        self.patcher_write_cache = patch('backend.fechas_sync.write_cache')
        self.mock_write_cache = self.patcher_write_cache.start()
        
        self.patcher_write_sources = patch('backend.fechas_sync.write_sources')
        self.mock_write_sources = self.patcher_write_sources.start()
        
        # Isolate update_novelty and process_subjects
        self.patcher_novelty = patch('backend.fechas_sync.update_novelty')
        self.mock_novelty = self.patcher_novelty.start()
        self.mock_novelty.side_effect = lambda events: events
        
        self.patcher_subjects = patch('backend.fechas_sync.process_subjects')
        self.mock_subjects = self.patcher_subjects.start()
        self.mock_subjects.return_value = []
        
        # Isolate manual events
        self.patcher_read_manual = patch('backend.fechas_sync.read_manual_events')
        self.mock_read_manual = self.patcher_read_manual.start()
        self.mock_read_manual.return_value = []
        
        # Disable completed statuses logic that writes to disk
        self.patcher_apply_completed = patch('backend.cache.apply_completed_status')
        self.mock_apply_completed = self.patcher_apply_completed.start()
        self.mock_apply_completed.side_effect = lambda events: events

    def tearDown(self):
        patch.stopall()
        self.test_dir.cleanup()

    def _setup_base_state(self):
        s1 = DataSource(id="moodle", name="Moodle", type="moodle", url="http://moodle", enabled=True)
        s2 = DataSource(id="unrn", name="UNRN", type="ical", url="http://unrn", enabled=True)
        self.mock_read_sources.return_value = [s1, s2]
        
        prev_events = [
            AcademicEvent(id="ev_moodle_1", title="M1", due_date="2099-08-01", source_id="moodle", source_name="Moodle").to_dict(),
            AcademicEvent(id="ev_unrn_1", title="U1", due_date="2099-08-01", source_id="unrn", source_name="UNRN").to_dict()
        ]
        mock_cache = MagicMock()
        mock_cache.events = prev_events
        mock_cache.sync_status = "ok"
        mock_cache.sync_error = None
        self.mock_read_cache.return_value = mock_cache
        return s1, s2

    def test_selective_sync_success(self):
        self._setup_base_state()
        
        # Fetch mock for unrn
        new_unrn_event = AcademicEvent(id="ev_unrn_2", title="U2", due_date="2099-08-02", source_id="unrn", source_name="UNRN")
        self.mock_fetch.return_value = ([new_unrn_event], None)
        
        # Execute selective sync
        cache = sync(dry_run=True, source_id="unrn")
        
        # Verify
        self.assertEqual(len(cache.events), 2)
        titles = {e["title"] for e in cache.events}
        self.assertIn("M1", titles)
        self.assertIn("U2", titles)
        self.assertNotIn("U1", titles)
        self.assertEqual(cache.sync_status, "ok")
        self.assertEqual(cache.sync_error, None)

    def test_selective_sync_network_error(self):
        self._setup_base_state()
        
        # Simulate network error
        self.mock_fetch.return_value = ([], "Timeout")
        
        cache = sync(dry_run=True, source_id="unrn")
        
        # Verify previous events are preserved
        self.assertEqual(len(cache.events), 2)
        titles = {e["title"] for e in cache.events}
        self.assertIn("M1", titles)
        self.assertIn("U1", titles) # Preserved!
        
        # Global error should be updated
        self.assertEqual(cache.sync_status, "partial")
        self.assertIn("UNRN: Timeout", cache.sync_error)

    def test_selective_sync_clears_previous_error(self):
        s1, s2 = self._setup_base_state()
        s2.sync_error = "Previous error"
        
        # Successful fetch
        new_unrn_event = AcademicEvent(id="ev_unrn_2", title="U2", due_date="2099-08-02", source_id="unrn", source_name="UNRN")
        self.mock_fetch.return_value = ([new_unrn_event], None)
        
        cache = sync(dry_run=True, source_id="unrn")
        
        # Should clear the error
        self.assertEqual(cache.sync_status, "ok")
        self.assertEqual(cache.sync_error, None)

    def test_selective_sync_disabled_source(self):
        s1, s2 = self._setup_base_state()
        s2.enabled = False
        
        # Should exit entirely
        with self.assertRaises(SystemExit) as cm:
            sync(dry_run=True, source_id="unrn")
        self.assertEqual(cm.exception.code, 1)

    def test_selective_sync_manual_source(self):
        s1, s2 = self._setup_base_state()
        s_manual = DataSource(id="manual", name="Manual", type="manual", enabled=True)
        self.mock_read_sources.return_value.append(s_manual)
        
        manual_ev = AcademicEvent(id="ev_manual", title="Manual1", due_date="2099-08-03", source_id="manual", source_name="Manual")
        self.mock_read_manual.return_value = [manual_ev]
        
        cache = sync(dry_run=True, source_id="manual")
        
        # Verify it loaded M1, U1 and Manual1
        self.assertEqual(len(cache.events), 3)
        titles = {e["title"] for e in cache.events}
        self.assertIn("M1", titles)
        self.assertIn("U1", titles)
        self.assertIn("Manual1", titles)

if __name__ == "__main__":
    unittest.main()

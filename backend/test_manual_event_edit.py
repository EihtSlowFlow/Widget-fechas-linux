import os
import tempfile
import sys
import unittest
from unittest import mock
from pathlib import Path
from datetime import datetime, date

from backend.models import AcademicEvent
from backend.cache import (
    read_manual_events,
    write_manual_events,
    update_manual_event,
    update_novelty,
    read_known_events,
    toggle_completed,
    read_completed_events,
    apply_completed_status,
    mark_event_seen,
)


class TestManualEventEdit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        self.patchers = [
            mock.patch('backend.cache.MANUAL_EVENTS_FILE', self.temp_path / "manual_events.json"),
            mock.patch('backend.cache.KNOWN_EVENTS_FILE', self.temp_path / "known_events.json"),
            mock.patch('backend.cache.SEEN_EVENTS_FILE', self.temp_path / "seen_events.json"),
            mock.patch('backend.cache.COMPLETED_EVENTS_FILE', self.temp_path / "completed_events.json"),
            mock.patch('backend.cache.CACHE_FILE', self.temp_path / "cache.json"),
        ]
        for p in self.patchers:
            p.start()
            
        # Limpiar eventos para cada test
        write_manual_events([])

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        self.temp_dir.cleanup()

    def test_update_manual_event_retains_id_and_updates_fields(self):
        # 1. Crear evento inicial
        evt = AcademicEvent(
            title="Título original",
            due_date="2026-10-10T10:00:00",
            category="otro",
            source_id="manual",
            source_name="Eventos Manuales",
            is_manual=True
        )
        evt.id = "uuid-test-123"
        write_manual_events([evt])
        
        # Otro evento que debe permanecer intacto
        evt2 = AcademicEvent(
            title="Otro evento",
            due_date="2026-10-10T10:00:00",
            category="otro",
            source_id="manual",
            source_name="Eventos Manuales",
            is_manual=True
        )
        evt2.id = "uuid-test-456"
        write_manual_events([evt, evt2])

        # 2. Actualizar el primero con fuente errónea maliciosa para comprobar que se fuerza
        updated = AcademicEvent(
            title="Título modificado",
            due_date="2026-11-11T11:00:00",
            category="entrega",
            source_id="malicioso",
            source_name="Malicioso",
            is_manual=False
        )
        
        result = update_manual_event("uuid-test-123", updated)
        self.assertTrue(result)

        # 3. Verificar
        events = read_manual_events()
        self.assertEqual(len(events), 2)
        mod_evt = next(e for e in events if e.id == "uuid-test-123")
        self.assertEqual(mod_evt.id, "uuid-test-123")  # Mantiene ID original
        self.assertEqual(mod_evt.title, "Título modificado")
        self.assertEqual(mod_evt.due_date, "2026-11-11T11:00:00")
        self.assertEqual(mod_evt.category, "entrega")
        self.assertEqual(mod_evt.source_id, "manual")  # Fue forzado
        self.assertEqual(mod_evt.is_manual, True)  # Fue forzado
        
        other_evt = next(e for e in events if e.id == "uuid-test-456")
        self.assertEqual(other_evt.title, "Otro evento")
        
    def test_update_inexistent_event_raises_error(self):
        updated = AcademicEvent(
            title="Fake",
            due_date="2026-10-10T10:00:00",
            source_id="manual",
            source_name="Eventos Manuales",
            is_manual=True
        )
        with self.assertRaises(ValueError):
            update_manual_event("no-existe", updated)
            
        self.assertEqual(len(read_manual_events()), 0)

    def test_completed_status_is_retained_after_edit(self):
        evt = AcademicEvent(
            title="Para completar",
            due_date="2026-10-10T10:00:00",
            source_id="manual",
            source_name="Eventos Manuales",
            is_manual=True
        )
        evt.id = "uuid-test-456"
        write_manual_events([evt])

        # Marcar como completado
        toggle_completed(evt.id)
        self.assertIn(evt.id, read_completed_events())

        # Editar evento
        updated = AcademicEvent(
            title="Editado",
            due_date="2026-10-10T10:00:00",
            source_id="manual",
            source_name="Eventos Manuales",
            is_manual=True
        )
        update_manual_event(evt.id, updated)

        # Cargar con apply_completed_status
        events = read_manual_events()
        events_dict = [e.to_dict() for e in events]
        events_dict = apply_completed_status(events_dict)
        
        self.assertTrue(events_dict[0]["is_completed"])

    def test_novelty_status_is_retained_after_edit(self):
        evt = AcademicEvent(
            title="Nuevo evento",
            due_date="2026-10-10T10:00:00",
            source_id="manual",
            source_name="Eventos Manuales",
            is_manual=True
        )
        evt.id = "uuid-test-789"
        
        # Primera pasada: debería registrarse en known_events con la fecha de hoy
        events = update_novelty([evt])
        self.assertTrue(events[0].is_new)
        
        # Lo marcamos como visto
        mark_event_seen(evt.id)
        
        # Segunda pasada, ya no debe ser nuevo
        events = update_novelty([evt])
        self.assertFalse(events[0].is_new)

        # Editamos el evento (cambia título, que afectaría a generate_stable_id)
        evt.title = "Título modificado que cambiaría stable_id"
        
        # Tercera pasada: update_novelty debería seguir sin marcarlo como nuevo
        events = update_novelty([evt])
        self.assertFalse(events[0].is_new)

if __name__ == '__main__':
    unittest.main()

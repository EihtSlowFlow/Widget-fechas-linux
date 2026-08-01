import os
import tempfile
import sys
from pathlib import Path

# 1. Configurar HOME temporal antes de importar CUALQUIER módulo del proyecto
temp_dir = tempfile.TemporaryDirectory()
os.environ["HOME"] = temp_dir.name

import unittest
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
)


class TestManualEventEdit(unittest.TestCase):
    def setUp(self):
        # Limpiar eventos para cada test, aunque estén en el dir temporal
        write_manual_events([])

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

        # 2. Actualizarlo
        updated = AcademicEvent(
            title="Título modificado",
            due_date="2026-11-11T11:00:00",
            category="entrega",
            source_id="manual",  # Esto debería ser forzado por cache de todos modos
            source_name="Eventos Manuales",
            is_manual=True
        )
        
        result = update_manual_event("uuid-test-123", updated)
        self.assertTrue(result)

        # 3. Verificar
        events = read_manual_events()
        self.assertEqual(len(events), 1)
        mod_evt = events[0]
        self.assertEqual(mod_evt.id, "uuid-test-123")  # Mantiene ID original
        self.assertEqual(mod_evt.title, "Título modificado")
        self.assertEqual(mod_evt.due_date, "2026-11-11T11:00:00")
        self.assertEqual(mod_evt.category, "entrega")
        
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
        
        today_str = date.today().isoformat()
        known = read_known_events()
        self.assertIn(evt.id, known)
        self.assertEqual(known[evt.id], today_str)

        # Editamos el evento (cambia título, que afectaría a generate_stable_id)
        evt.title = "Título modificado que cambiaría stable_id"
        
        # Segunda pasada: update_novelty debería usar el evt.id para manuales, encontrando el mismo first_seen
        events = update_novelty([evt])
        
        # Debería seguir estando (y no añadir uno nuevo por el cambio de título)
        known_after = read_known_events()
        self.assertIn(evt.id, known_after)
        self.assertEqual(len(known_after), 1)  # No se creó otro registro


if __name__ == '__main__':
    try:
        unittest.main(exit=False)
    finally:
        temp_dir.cleanup()

"""
Gestor de caché JSON para el sistema de Fechas Académicas.

Implementa escritura atómica (write-to-temp + rename) para evitar
corrupción si el widget lee mientras el servicio escribe.
"""

from __future__ import annotations

import json
import logging
import tempfile
import fcntl
import time
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from backend.config import (
    DATA_DIR,
    SOURCES_FILE,
    CACHE_FILE,
    CACHE_LOCK_FILE,
    KNOWN_EVENTS_FILE,
    SEEN_EVENTS_FILE,
    COMPLETED_EVENTS_FILE,
    MANUAL_EVENTS_FILE,
    SUBJECTS_FILE,
    ACADEMIC_PERIOD_FILE,
    ensure_dirs,
)
from backend.models import AcademicEvent, CacheData, DataSource, SubjectSyllabus, AcademicPeriod

logger = logging.getLogger("fechas.cache")


@contextmanager
def cache_lock(timeout: int = 5):
    """Context manager para asegurar escritura/lectura segura del cache.json."""
    ensure_dirs()
    f = open(CACHE_LOCK_FILE, "w")
    start = time.monotonic()
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() - start > timeout:
                f.close()
                raise TimeoutError("No se pudo obtener el lock del cache")
            time.sleep(0.1)
    try:
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def _atomic_write_json(path: Path, data: dict) -> None:
    """
    Escribe un JSON de forma atómica:
    1. Escribe a un archivo temporal en el mismo directorio
    2. Renombra (atómico en Linux) al archivo destino
    Esto garantiza que el widget nunca lea un archivo parcialmente escrito.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.stem}_",
        suffix=".tmp",
    )
    try:
        with open(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        Path(tmp_path).replace(path)
        logger.debug("Escritura atómica exitosa: %s", path)
    except Exception:
        # Limpieza en caso de error
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _read_json(path: Path, default: dict | list | None = None) -> dict | list:
    """Lee un archivo JSON, retornando un default si no existe o es inválido."""
    if not path.exists():
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Error leyendo %s: %s — usando default", path, e)
        return default if default is not None else {}


# ─── Cache principal (cache.json) ─────────────────────────────────

def read_cache() -> CacheData:
    """Lee el cache.json y retorna un CacheData."""
    ensure_dirs()
    data = _read_json(CACHE_FILE, default={})
    return CacheData.from_dict(data)


def write_cache(cache_data: CacheData) -> None:
    """Escribe el cache.json de forma atómica."""
    ensure_dirs()
    _atomic_write_json(CACHE_FILE, cache_data.to_dict())
    logger.info("Cache escrita: %d eventos", len(cache_data.events))


# ─── Known events (detección de novedades) ─────────────────────────

def read_known_events() -> dict[str, str]:
    """
    Lee known_events.json: mapea stable_id → first_seen date string.
    Ejemplo: {"a1b2c3d4": "2026-06-11", ...}
    """
    ensure_dirs()
    return _read_json(KNOWN_EVENTS_FILE, default={})


def write_known_events(known: dict[str, str]) -> None:
    """Escribe known_events.json de forma atómica."""
    ensure_dirs()
    _atomic_write_json(KNOWN_EVENTS_FILE, known)


def update_novelty(events: list[AcademicEvent]) -> list[AcademicEvent]:
    """
    Actualiza first_seen e is_new para cada evento.
    - Si el stable_id no estaba en known_events, es nuevo → first_seen = hoy
    - Si ya existía, conserva su first_seen original
    - is_new = True solo si first_seen == hoy Y no está en seen_events
    """
    known = read_known_events()
    seen = read_seen_events()
    today_str = date.today().isoformat()
    updated_known = dict(known)

    for event in events:
        novelty_id = event.id if event.is_manual else event.generate_stable_id()
        if novelty_id in known:
            event.first_seen = known[novelty_id]
        else:
            event.first_seen = today_str
            updated_known[novelty_id] = today_str

        # Nuevo = descubierto hoy Y no visto aún por el usuario
        event.is_new = (event.first_seen == today_str) and (novelty_id not in seen)

    # Limpiar eventos viejos (más de 90 días) para evitar crecimiento infinito
    cutoff = date.today().toordinal() - 90
    cleaned = {
        sid: fs for sid, fs in updated_known.items()
        if date.fromisoformat(fs).toordinal() > cutoff
    }

    write_known_events(cleaned)
    return events


# ─── Seen events (desmarcar badge "Nuevo" al hacer hover) ────────

def read_seen_events() -> set[str]:
    """Lee el set de event IDs que el usuario ya vio (hover)."""
    ensure_dirs()
    data = _read_json(SEEN_EVENTS_FILE, default=[])
    if isinstance(data, list):
        return set(data)
    return set()


def mark_event_seen(event_id: str) -> None:
    """Marca un evento como visto por el usuario (quita badge Nuevo)."""
    ensure_dirs()
    seen = read_seen_events()
    if event_id not in seen:
        seen.add(event_id)
        _atomic_write_json(SEEN_EVENTS_FILE, list(seen))


# ─── Completed events (marcar como entregado/completado) ─────────

def read_completed_events() -> set[str]:
    """Lee el set de event IDs marcados como completados."""
    ensure_dirs()
    data = _read_json(COMPLETED_EVENTS_FILE, default=[])
    if isinstance(data, list):
        return set(data)
    return set()


def toggle_completed(event_id: str) -> bool:
    """
    Alterna el estado de completado de un evento.
    Retorna True si quedó completado, False si se desmarcó.
    Ambas actualizaciones (lista de completados y cache.json) 
    se protegen bajo el mismo lock para evitar condiciones de carrera.
    """
    ensure_dirs()
    
    with cache_lock():
        completed = read_completed_events()
        if event_id in completed:
            completed.discard(event_id)
            result = False
        else:
            completed.add(event_id)
            result = True
        
        _atomic_write_json(COMPLETED_EVENTS_FILE, list(completed))

        # Actualizar cache.json inmediatamente para que el widget y la UI se sincronicen
        try:
            cache_data = read_cache()
            if cache_data and cache_data.events:
                updated = False
                for e in cache_data.events:
                    if e.get("id") == event_id:
                        e["is_completed"] = result
                        updated = True
                if updated:
                    write_cache(cache_data)
        except Exception as e:
            logger.warning("No se pudo actualizar cache.json al cambiar completado: %s", e)

    return result


def apply_completed_status(events: list[dict]) -> list[dict]:
    """Aplica is_completed a los eventos del cache basándose en completed_events.json."""
    completed = read_completed_events()
    for e in events:
        eid = e.get("id", "")
        e["is_completed"] = eid in completed
    return events


# ─── Fuentes de datos (sources.json) ──────────────────────────────

def read_sources() -> list[DataSource]:
    """Lee las fuentes de datos configuradas."""
    ensure_dirs()
    data = _read_json(SOURCES_FILE, default=[])
    if isinstance(data, list):
        return [DataSource.from_dict(s) for s in data]
    return []


def write_sources(sources: list[DataSource]) -> None:
    """Escribe las fuentes de datos de forma atómica."""
    ensure_dirs()
    _atomic_write_json(SOURCES_FILE, [s.to_dict() for s in sources])


def init_default_sources() -> list[DataSource]:
    """Crea las fuentes por defecto si sources.json no existe."""
    from backend.config import DEFAULT_MOODLE_ICAL_URL, UNRN_CALENDAR_URL

    if SOURCES_FILE.exists():
        return read_sources()

    defaults = [
        DataSource(
            id="moodle-unrn",
            name="Moodle Campus Bimodal UNRN",
            type="ical",
            url=DEFAULT_MOODLE_ICAL_URL,
            # Deshabilitada por defecto: cada usuario necesita su propia URL
            # con su authtoken personal. Configurar desde la app → Fuentes.
            enabled=bool(DEFAULT_MOODLE_ICAL_URL),
        ),
        DataSource(
            id="unrn-calendario",
            name="Calendario Académico UNRN",
            type="unrn_web",
            url=UNRN_CALENDAR_URL,
            enabled=True,
        ),
        DataSource(
            id="manual",
            name="Eventos Manuales",
            type="manual",
            url="",
            enabled=True,
        ),
    ]

    write_sources(defaults)
    logger.info("Fuentes por defecto creadas: %d fuentes", len(defaults))
    return defaults


# ─── Eventos manuales ─────────────────────────────────────────────

def read_manual_events() -> list[AcademicEvent]:
    """Lee eventos manuales del usuario."""
    ensure_dirs()
    data = _read_json(MANUAL_EVENTS_FILE, default=[])
    if isinstance(data, list):
        return [AcademicEvent.from_dict(e) for e in data]
    return []


def write_manual_events(events: list[AcademicEvent]) -> None:
    """Escribe eventos manuales de forma atómica."""
    ensure_dirs()
    _atomic_write_json(MANUAL_EVENTS_FILE, [e.to_dict() for e in events])


def update_manual_event(event_id: str, updated_event: AcademicEvent) -> bool:
    """
    Busca un evento manual por su ID y actualiza solo sus campos editables.
    Mantiene el ID y los metadatos de fuente, y lanza ValueError si no lo encuentra.
    """
    events = read_manual_events()
    for i, event in enumerate(events):
        if event.id == event_id:
            # Reemplazar campos editables
            event.title = updated_event.title
            event.description = updated_event.description
            event.due_date = updated_event.due_date
            event.category = updated_event.category
            
            # Forzar identidad de evento manual
            event.id = event_id
            event.source_id = "manual"
            event.source_name = "Eventos Manuales"
            event.is_manual = True
            
            events[i] = event
            write_manual_events(events)
            return True
            
    raise ValueError(f"El evento manual '{event_id}' ya no existe")


def delete_manual_event(event_id: str) -> bool:
    """
    Elimina un evento manual por su ID y limpia sus estados asociados.
    """
    events = read_manual_events()
    initial_count = len(events)
    events = [e for e in events if e.id != event_id]
    if len(events) == initial_count:
        raise ValueError(f"El evento manual '{event_id}' no existe")
        
    write_manual_events(events)
    
    # Limpiar estados asociados
    completed = read_completed_events()
    if event_id in completed:
        completed.discard(event_id)
        _atomic_write_json(COMPLETED_EVENTS_FILE, list(completed))
        
    seen = read_seen_events()
    if event_id in seen:
        seen.discard(event_id)
        _atomic_write_json(SEEN_EVENTS_FILE, list(seen))
        
    known = read_known_events()
    if event_id in known:
        del known[event_id]
        write_known_events(known)
        
    return True


# ─── Materias (subjects.json) ─────────────────────────────────────

def read_subjects() -> list[SubjectSyllabus]:
    """Lee las materias y temarios del usuario."""
    ensure_dirs()
    data = _read_json(SUBJECTS_FILE, default=[])
    
    subjects = []
    if isinstance(data, list):
        for s in data:
            if not isinstance(s, dict):
                continue
            try:
                subjects.append(SubjectSyllabus.from_dict(s))
            except Exception as e:
                logger.warning("Error leyendo materia: %s", e)
    return subjects


def write_subjects(subjects: list[SubjectSyllabus]) -> None:
    """Escribe las materias de forma atómica."""
    ensure_dirs()
    _atomic_write_json(SUBJECTS_FILE, [s.to_dict() for s in subjects])


# ─── Periodo Académico (academic_period.json) ─────────────────────

def read_academic_period() -> AcademicPeriod | None:
    """Lee el periodo académico."""
    ensure_dirs()
    data = _read_json(ACADEMIC_PERIOD_FILE, default={})
    if not data:
        return None
    try:
        return AcademicPeriod.from_dict(data)
    except Exception as e:
        logger.warning("Error leyendo periodo académico: %s", e)
        return None

def write_academic_period(period: AcademicPeriod) -> None:
    """Escribe el periodo académico de forma atómica."""
    ensure_dirs()
    _atomic_write_json(ACADEMIC_PERIOD_FILE, period.to_dict())

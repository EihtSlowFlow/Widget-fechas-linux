"""
Gestor de caché JSON para el sistema de Fechas Académicas.

Implementa escritura atómica (write-to-temp + rename) para evitar
corrupción si el widget lee mientras el servicio escribe.
"""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from backend.config import (
    CACHE_FILE,
    KNOWN_EVENTS_FILE,
    SEEN_EVENTS_FILE,
    COMPLETED_EVENTS_FILE,
    SOURCES_FILE,
    MANUAL_EVENTS_FILE,
    ensure_dirs,
)
from backend.models import AcademicEvent, CacheData, DataSource

logger = logging.getLogger("fechas.cache")


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
        stable_id = event.generate_stable_id()
        if stable_id in known:
            event.first_seen = known[stable_id]
        else:
            event.first_seen = today_str
            updated_known[stable_id] = today_str

        # Nuevo = descubierto hoy Y no visto aún por el usuario
        event.is_new = (event.first_seen == today_str) and (stable_id not in seen)

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
    """
    ensure_dirs()
    completed = read_completed_events()
    if event_id in completed:
        completed.discard(event_id)
        result = False
    else:
        completed.add(event_id)
        result = True
    _atomic_write_json(COMPLETED_EVENTS_FILE, list(completed))
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

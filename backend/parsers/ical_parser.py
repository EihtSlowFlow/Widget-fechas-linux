"""
Parser de feeds iCalendar para el sistema de Fechas Académicas.

Diseñado para consumir el export iCal de Moodle (Campus Bimodal UNRN).
La URL con authtoken autentica automáticamente sin intervención del usuario.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

import requests
from icalendar import Calendar
from dateutil.rrule import rrulestr

from backend.config import REQUEST_TIMEOUT, USER_AGENT, LOOKAHEAD_DAYS
from backend.models import AcademicEvent

logger = logging.getLogger("fechas.parsers.ical")


def _normalize_date(dt_prop) -> Optional[datetime]:
    """
    Normaliza un valor DTSTART/DTEND de icalendar a un datetime con timezone.
    Moodle puede devolver date o datetime, con o sin tzinfo.
    """
    if dt_prop is None:
        return None

    dt = dt_prop.dt if hasattr(dt_prop, "dt") else dt_prop

    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            # Asumir timezone local (Argentina UTC-3)
            from dateutil.tz import gettz
            dt = dt.replace(tzinfo=gettz("America/Argentina/Buenos_Aires"))
        return dt
    elif isinstance(dt, date):
        # Convertir date a datetime al inicio del día
        from dateutil.tz import gettz
        return datetime(
            dt.year, dt.month, dt.day,
            23, 59, 0,
            tzinfo=gettz("America/Argentina/Buenos_Aires"),
        )
    return None


def _categorize_event(summary: str, categories: str = "") -> str:
    """
    Intenta categorizar el evento basándose en su título y categorías.
    Moodle suele incluir indicadores como 'Tarea', 'Examen', etc.
    """
    text = f"{summary} {categories}".lower()

    if any(kw in text for kw in ["tarea", "entrega", "tp ", "trabajo práctico",
                                   "trabajo practico", "assignment", "actividad"]):
        return "entrega"
    elif any(kw in text for kw in ["examen", "parcial", "final", "quiz",
                                     "evaluación", "evaluacion", "recuperatorio"]):
        return "examen"
    elif any(kw in text for kw in ["inscripción", "inscripcion", "matrícula",
                                     "matricula", "registro"]):
        return "inscripcion"
    else:
        return "otro"


def fetch_ical_events(
    url: str,
    source_id: str,
    source_name: str,
) -> list[AcademicEvent]:
    """
    Descarga un feed iCal y extrae los eventos futuros como AcademicEvent.

    Args:
        url: URL completa del feed iCal (con authtoken para Moodle)
        source_id: ID de la fuente de datos
        source_name: Nombre legible de la fuente

    Returns:
        Lista de AcademicEvent extraídos del feed

    Raises:
        requests.RequestException: Si falla la descarga
        ValueError: Si el contenido no es iCal válido
    """
    logger.info("Descargando feed iCal: %s...", url[:80])

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    content = response.content
    if not content:
        raise ValueError("Feed iCal vacío")

    cal = Calendar.from_ical(content)
    events: list[AcademicEvent] = []

    today = date.today()
    cutoff = today.toordinal() + LOOKAHEAD_DAYS

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("summary", "Sin título"))
        description = str(component.get("description", ""))
        categories_raw = component.get("categories")

        categories_str = ""
        if categories_raw:
            if hasattr(categories_raw, "to_ical"):
                categories_str = categories_raw.to_ical().decode("utf-8", errors="replace")
            else:
                categories_str = str(categories_raw)

        # Obtener fecha de vencimiento (DTEND o DTSTART como fallback)
        dt_end = _normalize_date(component.get("dtend"))
        dt_start = _normalize_date(component.get("dtstart"))
        due_date = dt_end or dt_start

        if due_date is None:
            logger.debug("Evento sin fecha, omitido: %s", summary)
            continue

        # Filtrar: solo eventos futuros (o de hoy) dentro del lookahead
        event_ordinal = due_date.date().toordinal()
        if event_ordinal < today.toordinal():
            continue  # Ya pasó
        if event_ordinal > cutoff:
            continue  # Muy lejano

        category = _categorize_event(summary, categories_str)

        event = AcademicEvent(
            title=summary.strip(),
            description=description.strip()[:500],  # Limitar descripción
            due_date=due_date.isoformat(),
            source_id=source_id,
            source_name=source_name,
            category=category,
            is_manual=False,
        )
        # Usar ID estable para detección de novedades
        event.id = event.generate_stable_id()

        events.append(event)

    logger.info("Extraídos %d eventos del feed iCal", len(events))
    return events

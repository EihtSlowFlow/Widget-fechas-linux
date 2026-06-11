"""
Cliente REST genérico para el sistema de Fechas Académicas.

Esqueleto extensible para futuras APIs que proporcionen eventos
en formato JSON.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

import requests

from backend.config import REQUEST_TIMEOUT, USER_AGENT, LOOKAHEAD_DAYS
from backend.models import AcademicEvent

logger = logging.getLogger("fechas.parsers.rest")


def fetch_rest_events(
    url: str,
    source_id: str,
    source_name: str,
    events_path: str = "events",
    title_field: str = "title",
    date_field: str = "date",
    description_field: str = "description",
    headers: Optional[dict] = None,
) -> list[AcademicEvent]:
    """
    Obtiene eventos de una API REST genérica que devuelve JSON.

    Args:
        url: URL del endpoint
        source_id: ID de la fuente
        source_name: Nombre legible
        events_path: Key en el JSON donde están los eventos (dot notation)
        title_field: Campo del título en cada evento
        date_field: Campo de la fecha en cada evento (ISO 8601)
        description_field: Campo de la descripción
        headers: Headers adicionales para la petición

    Returns:
        Lista de AcademicEvent
    """
    logger.info("Obteniendo eventos REST: %s", url)

    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)

    response = requests.get(url, headers=req_headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    data = response.json()

    # Navegar por el path (e.g. "data.events" → data["data"]["events"])
    result = data
    for key in events_path.split("."):
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            logger.warning("Path '%s' no encontrado en la respuesta", events_path)
            return []

    if not isinstance(result, list):
        logger.warning("El resultado no es una lista de eventos")
        return []

    events: list[AcademicEvent] = []
    today = date.today()
    cutoff = today.toordinal() + LOOKAHEAD_DAYS

    for item in result:
        title = item.get(title_field, "Sin título")
        date_str = item.get(date_field, "")
        description = item.get(description_field, "")

        if not date_str:
            continue

        try:
            due_date = datetime.fromisoformat(date_str)
        except ValueError:
            logger.debug("Fecha inválida omitida: %s", date_str)
            continue

        event_ordinal = due_date.date().toordinal()
        if event_ordinal < today.toordinal() or event_ordinal > cutoff:
            continue

        event = AcademicEvent(
            title=str(title).strip(),
            description=str(description).strip()[:500],
            due_date=due_date.isoformat(),
            source_id=source_id,
            source_name=source_name,
            category="otro",
            is_manual=False,
        )
        event.id = event.generate_stable_id()
        events.append(event)

    logger.info("Extraídos %d eventos de la API REST", len(events))
    return events

"""
Scraper del Calendario Académico UNRN.

Extrae fechas institucionales de la página pública:
https://www.unrn.edu.ar/section/47/calendario-academico.html

La página usa tablas de 2 columnas: fecha | descripción.
Solo se extraen los 6 tipos de eventos relevantes (whitelist).
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from backend.config import REQUEST_TIMEOUT, USER_AGENT, LOOKAHEAD_DAYS
from backend.models import AcademicEvent

logger = logging.getLogger("fechas.parsers.unrn")

# Meses en español para parseo de fechas
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# Patrón rango: "dd/mm al dd/mm/yyyy" o "dd al dd/mm/yyyy"
RANGE_PATTERN = re.compile(
    r"(\d{1,2})(?:/(\d{1,2}))?(?:/(\d{4}))?\s+al\s+(\d{1,2})/(\d{1,2})/(\d{4})"
)

# Patrón fecha simple: "dd/mm/yyyy"
DATE_SIMPLE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


def _parse_date_cell(text: str) -> list[date]:
    """
    Extrae fechas de una celda de fecha de la tabla UNRN.
    Formatos: "09 al 14/02/2026", "02/02/2026", "25/02 al 13/03/2026"
    """
    dates = []
    text = text.strip()

    # Buscar rangos primero
    match = RANGE_PATTERN.search(text)
    if match:
        d1, m1, y1, d2, m2, y2 = match.groups()
        year2 = int(y2)
        month1 = int(m1) if m1 else int(m2)
        year1 = int(y1) if y1 else year2
        try:
            dates.append(date(year1, month1, int(d1)))
            dates.append(date(year2, int(m2), int(d2)))
        except ValueError:
            pass
        return dates

    # Buscar fecha simple
    match = DATE_SIMPLE.search(text)
    if match:
        d, m, y = match.groups()
        try:
            dates.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass

    return dates


# ─── Whitelist: solo estos tipos de eventos nos interesan ──────────
WHITELIST_PATTERNS = [
    # 1. Reinscripción Obligatoria y Censo
    (
        re.compile(r"reinscripci[oó]n\s+obligatoria", re.IGNORECASE),
        "inscripcion",
        "Reinscripción Obligatoria y Censo de Estudiantes",
    ),
    # 2. Inscripción a Exámenes Turno X - Llamado
    (
        re.compile(r"inscripci[oó]n(?:es)?\s+(?:a|al)\s+.*?ex[aá]menes.*turno", re.IGNORECASE),
        "inscripcion",
        None,
    ),
    # 3. Inscripciones a Asignaturas (no Medicina, no Vocacionales)
    (
        re.compile(
            r"inscripci[oó]n(?:es)?\s+a\s+asignaturas\s+"
            r"(?:primer\s+cuatrimestre|segundo\s+cuatrimestre|del\s+segundo)",
            re.IGNORECASE,
        ),
        "inscripcion",
        None,
    ),
    # 4. Llamado a Exámenes - Turno X (incluye "Primer llamado", "Segundo llamado")
    (
        re.compile(r"llamado\s+(?:a\s+)?ex[aá]menes.*turno", re.IGNORECASE),
        "examen",
        None,
    ),
    # 5. Inicio de ventana de dictado
    (
        re.compile(
            r"inicio\s+de\s+la\s+ventana\s+de\s+dictado.*?"
            r"(primer|segundo)\s+cuatrimestre",
            re.IGNORECASE,
        ),
        "otro",
        None,
    ),
    # 6. Fin de ventana de dictado
    (
        re.compile(
            r"fin\s+de\s+la\s+ventana\s+de\s+dictado.*?"
            r"(primer|segundo)\s+cuatrimestre",
            re.IGNORECASE,
        ),
        "otro",
        None,
    ),
]

# Patrones para descartar (adaptaciones de Medicina, Geología, etc.)
EXCLUDE_PATTERNS = [
    re.compile(r"medicina", re.IGNORECASE),
    re.compile(r"geolog[ií]a", re.IGNORECASE),
    re.compile(r"vocacional", re.IGNORECASE),
    re.compile(r"bimestre", re.IGNORECASE),
    re.compile(r"trimestre", re.IGNORECASE),
    re.compile(r"numerus\s+clausus", re.IGNORECASE),
]


def _match_whitelist(text: str) -> tuple[str, str] | None:
    """
    Verifica si un texto de evento coincide con el whitelist.
    Returns: (categoría, título_limpio) si coincide, None si no.
    """
    # Primero verificar exclusiones
    for excl in EXCLUDE_PATTERNS:
        if excl.search(text):
            return None

    for pattern, category, fixed_title in WHITELIST_PATTERNS:
        if pattern.search(text):
            if fixed_title:
                return category, fixed_title
            else:
                clean = re.sub(r'\s+', ' ', text).strip()
                # Quitar asteriscos y notas al pie
                clean = re.sub(r'\*+$', '', clean).strip()
                clean = re.sub(r'\.\s*$', '', clean).strip()
                if len(clean) > 100:
                    clean = clean[:97] + "..."
                return category, clean
    return None


def fetch_unrn_events(
    url: str,
    source_id: str,
    source_name: str,
) -> list[AcademicEvent]:
    """
    Scrapea el calendario académico de la UNRN.

    La página usa tablas HTML de 2 columnas:
      Columna 1: Fecha (ej: "09 al 14/02/2026")
      Columna 2: Descripción del evento

    Solo se conservan los 6 tipos de eventos relevantes (whitelist),
    descartando adaptaciones de Medicina/Geología y contenido general.
    """
    logger.info("Scrapeando calendario UNRN: %s", url)

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    events: list[AcademicEvent] = []

    today = date.today()
    cutoff = today.toordinal() + LOOKAHEAD_DAYS

    # Buscar todas las tablas de la página
    tables = soup.find_all("table")
    logger.debug("Encontradas %d tablas", len(tables))

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            # Columna 1: fecha, Columna 2: descripción
            date_text = cells[0].get_text(strip=True)
            desc_text = cells[1].get_text(strip=True)

            if not date_text or not desc_text:
                continue

            # Verificar whitelist
            result = _match_whitelist(desc_text)
            if result is None:
                continue

            category, title = result

            # Extraer fechas de la celda de fecha
            dates_found = _parse_date_cell(date_text)
            if not dates_found:
                continue

            # Usar la última fecha como deadline (fin del rango)
            event_date = dates_found[-1]
            event_ordinal = event_date.toordinal()

            if event_ordinal < today.toordinal():
                continue
            if event_ordinal > cutoff:
                continue

            from dateutil.tz import gettz
            tz = gettz("America/Argentina/Buenos_Aires")
            due_dt = datetime(
                event_date.year, event_date.month, event_date.day,
                23, 59, 0, tzinfo=tz,
            )

            # Si hay rango (2 fechas), guardar start_date
            start_iso = ""
            if len(dates_found) >= 2 and dates_found[0] != dates_found[-1]:
                start_d = dates_found[0]
                start_dt = datetime(
                    start_d.year, start_d.month, start_d.day,
                    0, 0, 0, tzinfo=tz,
                )
                start_iso = start_dt.isoformat()

            event = AcademicEvent(
                title=title,
                description="Fecha del calendario académico UNRN",
                due_date=due_dt.isoformat(),
                start_date=start_iso,
                source_id=source_id,
                source_name=source_name,
                category=category,
                is_manual=False,
            )
            event.id = event.generate_stable_id()
            events.append(event)

    # Deduplicar por stable_id
    seen_ids = set()
    unique_events = []
    for e in events:
        if e.id not in seen_ids:
            seen_ids.add(e.id)
            unique_events.append(e)

    logger.info("Extraídos %d eventos del calendario UNRN", len(unique_events))
    return unique_events

#!/usr/bin/env python3
"""
Motor de sincronización de Fechas Académicas.

Script principal ejecutado por systemd cada 30 minutos.
Lee las fuentes configuradas, descarga eventos, calcula urgencia,
detecta novedades y escribe el cache.json que lee el widget.

Uso:
    python3 fechas_sync.py              # Sincronización normal
    python3 fechas_sync.py --dry-run    # Solo muestra, no escribe
    python3 fechas_sync.py --verbose    # Logging detallado
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta

# Agregar el directorio padre al path para imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import (
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    MAX_RETRIES,
    ensure_dirs,
)
from backend.models import AcademicEvent, CacheData, CurrentSubjectWeek
from backend.cache import (
    init_default_sources,
    read_sources,
    write_sources,
    read_manual_events,
    read_subjects,
    update_novelty,
    write_cache,
)

logger = logging.getLogger("fechas.sync")


def _fetch_events_from_source(source) -> tuple[list[AcademicEvent], str | None]:
    """
    Obtiene eventos de una fuente específica.
    Retorna (eventos, error_message).
    """
    if not source.enabled:
        return [], None

    try:
        if source.type == "ical":
            from backend.parsers.ical_parser import fetch_ical_events
            events = fetch_ical_events(source.url, source.id, source.name)
            return events, None

        elif source.type == "unrn_web":
            from backend.parsers.unrn_scraper import fetch_unrn_events
            events = fetch_unrn_events(source.url, source.id, source.name)
            return events, None

        elif source.type == "rest":
            from backend.parsers.rest_parser import fetch_rest_events
            events = fetch_rest_events(source.url, source.id, source.name)
            return events, None

        elif source.type == "manual":
            # Los eventos manuales se cargan por separado
            return [], None

        else:
            logger.warning("Tipo de fuente desconocido: %s", source.type)
            return [], f"Tipo desconocido: {source.type}"

    except Exception as e:
        logger.error("Error procesando fuente '%s': %s", source.name, e)
        return [], str(e)


def process_subjects(today: date) -> list[CurrentSubjectWeek]:
    """
    Procesa las materias configuradas y calcula su semana actual y temario.
    """
    subjects = read_subjects()
    current_subjects = []

    for subj in subjects:
        try:
            start_date = date.fromisoformat(subj.start_date)
        except ValueError:
            logger.error("Fecha de inicio inválida para la materia '%s': %s", subj.name, subj.start_date)
            continue
            
        elapsed_days = (today - start_date).days
        week_number = elapsed_days // 7 + 1
        day_of_week = elapsed_days % 7 + 1
        
        week_start = start_date + timedelta(days=(week_number - 1) * 7)
        week_end = week_start + timedelta(days=6)
        
        topics = []
        for entry in subj.syllabus:
            if entry.start_week <= week_number <= entry.end_week:
                if entry.topic and entry.topic.strip():
                    topics.append(entry.topic.strip())
                    
        current_subjects.append(CurrentSubjectWeek(
            subject_id=subj.id,
            subject_name=subj.name,
            week_number=week_number,
            day_of_week=day_of_week,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            topics=topics
        ))
        
    return current_subjects


def sync(dry_run: bool = False) -> CacheData:
    """
    Ejecuta el ciclo completo de sincronización.

    1. Lee/inicializa fuentes
    2. Descarga eventos de cada fuente
    3. Agrega eventos manuales
    4. Calcula urgencia
    5. Detecta novedades
    6. Escribe cache.json

    Args:
        dry_run: Si True, no escribe al disco

    Returns:
        CacheData con todos los eventos procesados
    """
    ensure_dirs()
    today = date.today()
    now_iso = datetime.now().astimezone().isoformat()

    logger.info("═══ Inicio de sincronización: %s ═══", now_iso)

    # 1. Cargar fuentes
    sources = init_default_sources()
    if not sources:
        sources = read_sources()

    all_events: list[AcademicEvent] = []
    sync_errors: list[str] = []

    # 2. Descargar eventos de cada fuente
    for source in sources:
        if source.type == "manual":
            continue  # Se procesan después

        if not source.enabled:
            logger.info("Fuente deshabilitada, omitida: %s", source.name)
            continue

        logger.info("─── Procesando fuente: %s (%s) ───", source.name, source.type)

        events, error = _fetch_events_from_source(source)

        # Actualizar estado de la fuente
        source.last_sync = now_iso
        source.sync_error = error
        source.event_count = len(events)

        if error:
            sync_errors.append(f"{source.name}: {error}")
            logger.error("  ✗ Error: %s", error)
        else:
            logger.info("  ✓ %d eventos obtenidos", len(events))

        all_events.extend(events)

    # 3. Agregar eventos manuales
    manual_events = read_manual_events()
    for me in manual_events:
        me.source_id = "manual"
        me.source_name = "Eventos Manuales"
        me.is_manual = True
    all_events.extend(manual_events)
    logger.info("─── Eventos manuales: %d ───", len(manual_events))

    # 4. Calcular urgencia para todos
    for event in all_events:
        event.compute_urgency(today)

    # 5. Filtrar eventos ya vencidos (más de 3 días pasados)
    all_events = [e for e in all_events if e.days_remaining >= -3]

    # 6. Detectar novedades
    all_events = update_novelty(all_events)
    new_count = sum(1 for e in all_events if e.is_new)
    if new_count > 0:
        logger.info("🆕 %d eventos nuevos detectados hoy", new_count)

    # 7. Ordenar por fecha
    all_events.sort(key=lambda e: e.due_date)

    # 8. Deduplicar por ID estable
    seen_ids = set()
    unique_events = []
    for e in all_events:
        if e.id not in seen_ids:
            seen_ids.add(e.id)
            unique_events.append(e)

    # 9. Procesar materias
    current_subjects = process_subjects(today)
    
    # 10. Construir cache
    global_status = "ok" if not sync_errors else "partial"
    global_error = "; ".join(sync_errors) if sync_errors else None

    event_dicts = [e.to_dict() for e in unique_events]
    subject_dicts = [cs.to_dict() for cs in current_subjects]

    # 10. Aplicar estado de completado (entregados por el usuario)
    from backend.cache import apply_completed_status
    event_dicts = apply_completed_status(event_dicts)

    cache = CacheData(
        last_sync=now_iso,
        sync_status=global_status,
        sync_error=global_error,
        events=event_dicts,
        current_subjects=subject_dicts,
    )

    # 11. Escribir
    if not dry_run:
        write_cache(cache)
        write_sources(sources)
        logger.info(
            "═══ Sincronización completada: %d eventos, estado: %s ═══",
            len(unique_events), global_status,
        )
    else:
        logger.info(
            "═══ DRY RUN: %d eventos procesados (no se escribió al disco) ═══",
            len(unique_events),
        )
        for e in unique_events:
            flag = "🆕" if e.is_new else "  "
            color = {"red": "🔴", "orange": "🟠", "yellow": "🟡", "green": "🟢"}
            urgency_icon = color.get(e.urgency, "⚪")
            logger.info(
                "  %s %s %3dd │ %s │ %s",
                flag, urgency_icon, e.days_remaining, e.title[:50], e.source_name,
            )
        
        logger.info("─── Materias Actuales ───")
        for cs in current_subjects:
            logger.info("  📚 %s: Semana %d (Día %d/7)", cs.subject_name, cs.week_number, cs.day_of_week)
            for t in cs.topics:
                logger.info("      - %s", t)

    return cache


def main():
    parser = argparse.ArgumentParser(
        description="Sincronización de Fechas Académicas",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecutar sin escribir al disco",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar logging detallado",
    )
    args = parser.parse_args()

    # Configurar logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    try:
        cache = sync(dry_run=args.dry_run)
        sys.exit(0)
    except Exception as e:
        logger.critical("Error fatal en sincronización: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

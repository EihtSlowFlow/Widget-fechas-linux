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
import fcntl
from datetime import date, datetime, timedelta

# Agregar el directorio padre al path para imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import (
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    MAX_RETRIES,
    SYNC_LOCK_FILE,
    ensure_dirs,
)
from backend.models import AcademicEvent, CacheData, CurrentSubjectWeek, SubjectSyllabus
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


def is_subject_active(subj: SubjectSyllabus, today: date) -> bool:
    """Verifica si una materia se encuentra en curso."""
    try:
        start_date = date.fromisoformat(subj.start_date)
    except ValueError:
        return False
        
    if today < start_date:
        return False

    elapsed_days = (today - start_date).days
    week_number = elapsed_days // 7 + 1

    # Prioridades de finalización: end_date -> units -> 16 semanas
    if subj.end_date:
        try:
            ed = date.fromisoformat(subj.end_date)
            return today <= ed
        except ValueError:
            pass

    unit_weeks = [
        week
        for unit in getattr(subj, 'units', [])
        for week in unit.weeks
    ]

    if unit_weeks:
        max_week = max(unit_weeks)
    else:
        max_week = 16

    fallback_end = start_date + timedelta(weeks=max_week) - timedelta(days=1)
    return today <= fallback_end

def process_subjects(subjects: list[SubjectSyllabus], today: date) -> list[CurrentSubjectWeek]:
    """
    Procesa las materias configuradas y calcula su semana actual y temario.
    """
    current_subjects = []

    for subj in subjects:
        if not is_subject_active(subj, today):
            continue

        try:
            start_date = date.fromisoformat(subj.start_date)
        except ValueError:
            continue
            
        elapsed_days = (today - start_date).days
        week_number = elapsed_days // 7 + 1
        
        # day_of_week relativo a la cursada, usado por el temario, no por agenda
        day_of_week = elapsed_days % 7 + 1
        
        week_start = start_date + timedelta(days=(week_number - 1) * 7)
        week_end = week_start + timedelta(days=6)
        
        topics = []
        unit_dicts = []

        if subj.units:
            # Use units model exclusively when units exist
            for unit in subj.units:
                if week_number in unit.weeks:
                    unit_dicts.append({
                        "name": unit.name,
                        "contents": list(unit.contents)
                    })
                    for c in unit.contents:
                        if c not in topics:
                            topics.append(c)

        current_subjects.append(CurrentSubjectWeek(
            subject_id=subj.id,
            subject_name=subj.name,
            week_number=week_number,
            day_of_week=day_of_week,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            topics=topics,
            units=unit_dicts
        ))
        
    return current_subjects


def generate_weekly_schedule(subjects: list[SubjectSyllabus], today: date) -> list[dict]:
    """Genera la agenda semanal de clases para materias activas."""
    schedule = []
    
    for subj in subjects:
        if not is_subject_active(subj, today):
            continue
            
        if not hasattr(subj, 'class_schedule') or not subj.class_schedule:
            continue
            
        for entry in subj.class_schedule:
            schedule.append({
                "subject_id": subj.id,
                "subject_name": subj.name,
                "day_of_week": entry.day_of_week,
                "start_time": entry.start_time,
                "end_time": entry.end_time,
                "location": getattr(entry, 'location', "")
            })
            
    # Ordenar por día de la semana y hora de inicio
    schedule.sort(key=lambda x: (x["day_of_week"], x["start_time"]))
    return schedule

def find_schedule_overlaps(entries: list[dict]) -> list[tuple]:
    """
    Encuentra solapamientos entre entradas de la agenda semanal.
    entries es una lista de diccionarios, similar a la generada por generate_weekly_schedule.
    Retorna una lista de tuplas con los diccionarios de las entradas que se solapan.
    """
    overlaps = []
    # Agrupar por día
    by_day = {}
    for e in entries:
        day = e["day_of_week"]
        if day not in by_day:
            by_day[day] = []
        by_day[day].append(e)
        
    for day, day_entries in by_day.items():
        # Ordenar por hora de inicio
        day_entries.sort(key=lambda x: x["start_time"])
        for i in range(len(day_entries)):
            for j in range(i + 1, len(day_entries)):
                e1 = day_entries[i]
                e2 = day_entries[j]
                # Si e2 comienza antes que e1 termine, hay solapamiento
                if e2["start_time"] < e1["end_time"]:
                    overlaps.append((e1, e2))
                else:
                    # Como están ordenados, si e2 comienza después del fin de e1, 
                    # los siguientes también lo harán
                    break
    return overlaps


def sync(dry_run: bool = False, source_id: str = None) -> CacheData:
    """
    Ejecuta el ciclo completo de sincronización o sincronización selectiva.
    """
    ensure_dirs()
    today = date.today()
    now_iso = datetime.now().astimezone().isoformat()

    logger.info("═══ Inicio de sincronización: %s ═══", now_iso)

    # 1. Cargar fuentes
    sources = init_default_sources()
    if not sources:
        sources = read_sources()

    target_source = None
    if source_id:
        target_source = next((s for s in sources if s.id == source_id), None)
        if not target_source:
            logger.error("La fuente solicitada '%s' no existe.", source_id)
            import sys
            sys.exit(1)
        if not target_source.enabled:
            logger.warning("La fuente '%s' está deshabilitada, se ignorará.", source_id)
            import sys
            sys.exit(1)

    previous_cache = None
    all_events: list[AcademicEvent] = []
    
    if source_id:
        from backend.cache import read_cache
        try:
            previous_cache = read_cache()
            cached_events = [AcademicEvent.from_dict(e) for e in previous_cache.events]
            enabled_source_ids = {s.id for s in sources if s.enabled}
            # Filtrar fuentes deshabilitadas, y separar los de la fuente objetivo
            all_events = [e for e in cached_events if e.source_id in enabled_source_ids and e.source_id != source_id]
        except Exception as e:
            logger.warning("Error leyendo cache anterior para sync selectiva: %s", e)
            all_events = []

    sync_errors: list[str] = []

    # 2. Descargar eventos de cada fuente
    sources_to_sync = [target_source] if source_id else sources
    
    for source in sources_to_sync:
        if source.type == "manual":
            continue

        if not source.enabled:
            logger.info("Fuente deshabilitada, omitida: %s", source.name)
            continue

        logger.info("─── Procesando fuente: %s (%s) ───", source.name, source.type)

        events, error = _fetch_events_from_source(source)

        source.last_sync = now_iso
        source.sync_error = error

        if error:
            sync_errors.append(f"{source.name}: {error}")
            logger.error("  ✗ Error: %s", error)
            if source_id and previous_cache:
                prev_source_events = [AcademicEvent.from_dict(e) for e in previous_cache.events if e.get("source_id") == source_id]
                logger.info("  Manteniendo %d eventos anteriores de la fuente %s debido a error.", len(prev_source_events), source_id)
                all_events.extend(prev_source_events)
                source.event_count = len(prev_source_events)
            else:
                source.event_count = 0
        else:
            logger.info("  ✓ %d eventos obtenidos", len(events))
            all_events.extend(events)
            source.event_count = len(events)

    # 3. Agregar eventos manuales
    if not source_id or source_id == "manual":
        manual_source = next((s for s in sources if s.id == "manual" and s.enabled), None)
        if manual_source:
            manual_events = read_manual_events()
            for me in manual_events:
                me.source_id = "manual"
                me.source_name = "Eventos Manuales"
                me.is_manual = True
            all_events.extend(manual_events)
            logger.info("─── Eventos manuales: %d ───", len(manual_events))
            manual_source.last_sync = now_iso
            manual_source.sync_error = None
            manual_source.event_count = len(manual_events)

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
    subjects = read_subjects()
    current_subjects = process_subjects(subjects, today)
    weekly_schedule = generate_weekly_schedule(subjects, today)
    
    # 10. Construir cache y escribir bajo lock
    from backend.cache import apply_completed_status, cache_lock
    
    current_errors = [
        f"{s.name}: {s.sync_error}"
        for s in sources
        if s.enabled and s.sync_error
    ]
    global_status = "partial" if current_errors else "ok"
    global_error = "; ".join(current_errors) if current_errors else None
    
    event_dicts = [e.to_dict() for e in unique_events]
    subject_dicts = [cs.to_dict() for cs in current_subjects]
    
    if not dry_run:
        with cache_lock():
            event_dicts = apply_completed_status(event_dicts)
            cache = CacheData(
                last_sync=now_iso,
                sync_status=global_status,
                sync_error=global_error,
                events=event_dicts,
                current_subjects=subject_dicts,
                weekly_schedule=weekly_schedule,
            )
            write_cache(cache)
        write_sources(sources)
        logger.info(
            "═══ Sincronización completada: %d eventos, estado: %s ═══",
            len(unique_events), global_status,
        )
    else:
        event_dicts = apply_completed_status(event_dicts)
        cache = CacheData(
            last_sync=now_iso,
            sync_status=global_status,
            sync_error=global_error,
            events=event_dicts,
            current_subjects=subject_dicts,
            weekly_schedule=weekly_schedule,
        )
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
                
        logger.info("─── Agenda Semanal ───")
        for ws in weekly_schedule:
            days = ["", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            day_name = days[ws["day_of_week"]] if 1 <= ws["day_of_week"] <= 7 else "Desconocido"
            logger.info("  %s %s-%s: %s (Aula: %s)", day_name, ws["start_time"], ws["end_time"], ws["subject_name"], ws["location"])

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
    parser.add_argument(
        "--source",
        type=str,
        help="ID de la fuente para sincronizar selectivamente",
    )
    parser.add_argument(
        "--check-lock",
        action="store_true",
        help="Sólo comprueba si hay una sincronización en curso. Retorna 3 si está bloqueado, 0 si está libre.",
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
        ensure_dirs()
        lock_file = open(SYNC_LOCK_FILE, "w")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            if args.check_lock:
                sys.exit(3)
            logger.warning("Ya hay una sincronización en curso. Abortando.")
            print("ALREADY_RUNNING")
            sys.exit(3)
            
        if args.check_lock:
            # We acquired the lock successfully, so no sync is running.
            sys.exit(0)

        try:
            cache = sync(dry_run=args.dry_run, source_id=args.source)
            print("SYNC_SUCCESS")
            sys.exit(0)
        except Exception as e:
            logger.critical("Error fatal en sincronización: %s", e, exc_info=True)
            print("SYNC_ERROR")
            sys.exit(1)
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
    except SystemExit:
        raise
    except Exception as e:
        logger.critical("Error fatal: %s", e, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

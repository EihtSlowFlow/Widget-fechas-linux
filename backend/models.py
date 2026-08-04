"""
Modelos de datos del sistema de Fechas Académicas.
Usa dataclasses para representar eventos y fuentes de datos.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from typing import Optional
import re

@dataclass
class ClassScheduleEntry:
    """Representa un horario de cursada en la semana."""
    day_of_week: int  # 1 (Lunes) a 7 (Domingo)
    start_time: str   # "HH:mm"
    end_time: str     # "HH:mm"
    location: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ClassScheduleEntry:
        try:
            day = int(data.get("day_of_week", 0))
            if not 1 <= day <= 7:
                raise ValueError(f"Día inválido: {day}")
        except (ValueError, TypeError):
            raise ValueError("Día de la semana inválido")

        start_time = str(data.get("start_time", "")).strip()
        end_time = str(data.get("end_time", "")).strip()
        
        time_pattern = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
        if not time_pattern.match(start_time):
            raise ValueError(f"start_time inválido: {start_time}")
        if not time_pattern.match(end_time):
            raise ValueError(f"end_time inválido: {end_time}")
            
        if start_time >= end_time:
            raise ValueError(f"start_time debe ser menor a end_time ({start_time} >= {end_time})")

        location = str(data.get("location", "")).strip()[:100]

        # Filtrar campos desconocidos
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        
        # Sobreescribir con los valores parseados y validados
        filtered.update({
            "day_of_week": day,
            "start_time": start_time,
            "end_time": end_time,
            "location": location
        })
        
        return cls(**filtered)



@dataclass
class AcademicEvent:
    """Representa un evento académico (entrega, examen, fecha institucional, etc.)."""

    title: str
    due_date: str                       # ISO 8601: "2026-06-20T23:59:00-03:00"
    source_id: str                      # ID de la fuente que lo generó
    source_name: str                    # Nombre legible de la fuente
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    category: str = "otro"              # "entrega", "examen", "inscripcion", "receso", "otro"
    days_remaining: int = 0             # Calculado en cada sync
    urgency: str = "green"              # "green", "yellow", "orange", "red"
    start_date: str = ""                # ISO 8601: fecha de inicio para rangos (ej: inscripciones)
    is_manual: bool = False             # True si fue creado manualmente por el usuario
    is_completed: bool = False          # True si fue marcado como entregado/completado
    first_seen: str = ""                # Fecha ISO (YYYY-MM-DD) en que se descubrió
    is_new: bool = False                # True si first_seen == hoy y no fue visto aún
    days_until_start: int | None = None # Días hasta la fecha de inicio (None si no hay rango)

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AcademicEvent:
        """Crea una instancia desde un diccionario."""
        # Filtrar campos desconocidos para tolerancia a versiones futuras
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    def compute_urgency(self, today: date | None = None) -> None:
        """Recalcula days_remaining, days_until_start y urgency."""
        from backend.config import get_urgency

        if today is None:
            today = date.today()

        try:
            due = datetime.fromisoformat(self.due_date)
            delta = due.date() - today
            self.days_remaining = delta.days
        except (ValueError, TypeError):
            self.days_remaining = 999

        # Calcular días hasta inicio si hay fecha de inicio
        if self.start_date:
            try:
                start = datetime.fromisoformat(self.start_date)
                self.days_until_start = (start.date() - today).days
            except (ValueError, TypeError):
                self.days_until_start = None
        else:
            self.days_until_start = None

        self.urgency = get_urgency(self.days_remaining)

    def generate_stable_id(self) -> str:
        """
        Genera un ID estable basado en título + fecha + fuente.
        Esto permite detectar si un evento ya fue visto previamente,
        incluso entre reinicios del sistema.
        """
        import hashlib
        key = f"{self.title}|{self.due_date}|{self.source_id}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]


@dataclass
class DataSource:
    """Representa una fuente de datos (iCal, scraper web, manual, etc.)."""

    name: str
    type: str                           # "ical", "unrn_web", "rest", "manual"
    url: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    enabled: bool = True
    last_sync: Optional[str] = None     # ISO 8601 timestamp
    sync_error: Optional[str] = None
    event_count: int = 0                # Cantidad de eventos en último sync

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> DataSource:
        """Crea una instancia desde un diccionario."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class SyllabusUnit:
    """Representa una unidad del programa de una materia."""
    name: str
    weeks: list[int] = field(default_factory=list)
    contents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SyllabusUnit":
        raw_name = data.get("name")
        if not isinstance(raw_name, str):
            raise ValueError("Nombre de unidad inválido")

        name = raw_name.strip()
        if not name:
            raise ValueError("Nombre de unidad vacío")

        # Validate weeks: must be a list, accept only int >= 1, reject booleans and floats
        raw_weeks = data.get("weeks", [])
        if not isinstance(raw_weeks, list):
            raw_weeks = []
        weeks = []
        for w in raw_weeks:
            if isinstance(w, bool):  # bool is subclass of int in Python
                continue
            if isinstance(w, float):
                continue
                
            val = None
            if isinstance(w, int):
                val = w
            elif isinstance(w, str):
                w = w.strip()
                if w.isdigit():
                    val = int(w)
                    
            if val is not None and val >= 1:
                weeks.append(val)
        # Deduplicate preserving first occurrence, then sort
        weeks = sorted(set(weeks))

        # Validate contents: must be a list of strings, strip, remove empty, deduplicate preserving order
        raw_contents = data.get("contents", [])
        if not isinstance(raw_contents, list):
            raw_contents = []
        seen = set()
        contents = []
        for c in raw_contents:
            if not isinstance(c, str):
                continue
            c = c.strip()
            if c and c not in seen:
                seen.add(c)
                contents.append(c)

        return cls(name=name, weeks=weeks, contents=contents)


@dataclass
class SubjectSyllabus:
    """Representa una materia con su temario y fecha de inicio."""
    name: str
    start_date: str                     # ISO 8601: "2026-06-20"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    end_date: str = ""                  # Opcional ISO 8601
    class_schedule: list[ClassScheduleEntry] = field(default_factory=list)
    units: list[SyllabusUnit] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d['class_schedule'] = [entry.to_dict() for entry in self.class_schedule]
        d['units'] = [unit.to_dict() for unit in self.units]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> SubjectSyllabus:
        name = str(data.get("name", "")).strip()
        start_date = str(data.get("start_date", "")).strip()
        
        if not name:
            raise ValueError("Nombre de materia vacío")
            
        # Validar formato ISO 8601
        date.fromisoformat(start_date)
        
        schedule_data = data.get("class_schedule", [])
        if not isinstance(schedule_data, list):
            schedule_data = []
            
        class_schedule = []
        for e in schedule_data:
            if not isinstance(e, dict):
                continue
            try:
                class_schedule.append(ClassScheduleEntry.from_dict(e))
            except (ValueError, TypeError) as ex:
                # Descartar entrada corrupta de horario sin afectar el resto
                import logging
                logging.getLogger("fechas.models").warning(f"Error parseando ClassScheduleEntry: {ex}")
                continue

        units_data = data.get("units", [])
        if not isinstance(units_data, list):
            units_data = []

        units = []
        for u in units_data:
            if not isinstance(u, dict):
                continue
            try:
                units.append(SyllabusUnit.from_dict(u))
            except (ValueError, TypeError):
                continue

        # Mantener el ID original o generar uno si no existe
        subj_id = data.get("id")
        if not subj_id or not isinstance(subj_id, str):
            subj_id = str(uuid.uuid4())
            
        end_date = str(data.get("end_date", "")).strip()
        if end_date:
            try:
                ed = date.fromisoformat(end_date)
                sd = date.fromisoformat(start_date)
                if ed < sd:
                    import logging
                    logging.getLogger("fechas.models").warning(f"end_date {end_date} es anterior a start_date {start_date}, ignorando.")
                    end_date = ""
            except ValueError:
                end_date = ""
            
        return cls(name=name, start_date=start_date, id=subj_id, end_date=end_date, class_schedule=class_schedule, units=units)



@dataclass
class CurrentSubjectWeek:
    """Estado actual de una materia en su semana en curso."""
    subject_id: str
    subject_name: str
    week_number: int
    day_of_week: int
    week_start: str                     # ISO 8601 Date
    week_end: str                       # ISO 8601 Date
    topics: list[str]
    units: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CurrentSubjectWeek:
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class CacheData:
    """Estructura completa del cache.json."""

    last_sync: str = ""                 # ISO 8601 timestamp
    sync_status: str = "pending"        # "ok", "error", "pending"
    sync_error: Optional[str] = None
    events: list[dict] = field(default_factory=list)
    current_subjects: list[dict] = field(default_factory=list)
    weekly_schedule: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CacheData:
        """Crea una instancia desde un diccionario."""
        return cls(
            last_sync=data.get("last_sync", ""),
            sync_status=data.get("sync_status", "pending"),
            sync_error=data.get("sync_error"),
            events=data.get("events", []),
            current_subjects=data.get("current_subjects", []),
            weekly_schedule=data.get("weekly_schedule", []),
        )

@dataclass
class AcademicPeriod:
    """Representa un periodo académico."""
    name: str
    start_date: str
    end_date: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AcademicPeriod":
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("Nombre de periodo vacío")
        
        start_date = str(data.get("start_date", "")).strip()
        d_start = date.fromisoformat(start_date)
        if d_start.weekday() != 0:
            raise ValueError("start_date debe ser Lunes (weekday 0)")

        end_date = str(data.get("end_date", "")).strip()
        if end_date:
            d_end = date.fromisoformat(end_date)
            if d_end < d_start:
                raise ValueError("end_date debe ser mayor o igual a start_date")

        return cls(name=name, start_date=start_date, end_date=end_date)

    @property
    def effective_end_date(self) -> date:
        if self.end_date:
            return date.fromisoformat(self.end_date)
        return date.fromisoformat(self.start_date) + timedelta(weeks=16) - timedelta(days=1)


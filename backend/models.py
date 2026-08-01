"""
Modelos de datos del sistema de Fechas Académicas.
Usa dataclasses para representar eventos y fuentes de datos.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional


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
class SyllabusEntry:
    """Representa una entrada en el temario de una materia."""
    start_week: int
    end_week: int
    topic: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SyllabusEntry:
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class SubjectSyllabus:
    """Representa una materia con su temario y fecha de inicio."""
    name: str
    start_date: str                     # ISO 8601: "2026-06-20"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    syllabus: list[SyllabusEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d['syllabus'] = [entry.to_dict() for entry in self.syllabus]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> SubjectSyllabus:
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields and k != 'syllabus'}
        syllabus_data = data.get('syllabus', [])
        syllabus = [SyllabusEntry.from_dict(e) for e in syllabus_data]
        return cls(**filtered, syllabus=syllabus)


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
        )

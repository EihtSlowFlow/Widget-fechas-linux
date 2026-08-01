"""
Configuración central del sistema de Fechas Académicas.
Define rutas, intervalos y constantes globales.
"""

import os
from pathlib import Path

# ─── Rutas de datos ────────────────────────────────────────────────
HOME = Path.home()

# Directorio de datos persistentes (caché, historial)
DATA_DIR = HOME / ".local" / "share" / "fechas-academicas"

# Directorio de configuración del usuario
CONFIG_DIR = HOME / ".config" / "fechas-academicas"

# Archivos principales
CACHE_FILE = DATA_DIR / "cache.json"
KNOWN_EVENTS_FILE = DATA_DIR / "known_events.json"
SEEN_EVENTS_FILE = DATA_DIR / "seen_events.json"
COMPLETED_EVENTS_FILE = DATA_DIR / "completed_events.json"
SOURCES_FILE = CONFIG_DIR / "sources.json"
MANUAL_EVENTS_FILE = CONFIG_DIR / "manual_events.json"
SUBJECTS_FILE = CONFIG_DIR / "subjects.json"

# Directorio del proyecto (para referencia)
PROJECT_DIR = Path(__file__).resolve().parent.parent

# ─── Intervalos de sincronización ──────────────────────────────────
SYNC_INTERVAL_MINUTES = 30         # Cada cuánto se sincroniza (systemd timer)
LOOKAHEAD_DAYS = 90                # Cuántos días hacia adelante buscar eventos
CACHE_REFRESH_WIDGET_SEC = 60      # Cada cuánto relee el widget el cache.json

# ─── Umbrales de urgencia (semáforo) ───────────────────────────────
URGENCY_THRESHOLDS = {
    "red":    0,     # Hoy o vencido (días <= 0)
    "orange": 2,     # 1-2 días
    "yellow": 7,     # 3-7 días
    "green":  float("inf"),  # Más de 7 días
}

URGENCY_COLORS = {
    "red":    "#F44336",
    "orange": "#FF9800",
    "yellow": "#FFC107",
    "green":  "#4CAF50",
}

# ─── Fuentes pre-configuradas UNRN ────────────────────────────────
# La URL de Moodle es personal para cada usuario. Se configura desde la app
# (pestaña Fuentes → Agregar fuente). Para obtenerla:
#   1. Ingresá a Moodle → Calendario → Importar/Exportar
#   2. Seleccioná "Exportar" → "Todos los eventos" → "Mes actual"
#   3. Hacé clic en "Obtener URL del calendario" y copiá la URL completa
DEFAULT_MOODLE_ICAL_URL = ""

UNRN_CALENDAR_URL = "https://www.unrn.edu.ar/section/47/calendario-academico.html"

# ─── Configuración de red ─────────────────────────────────────────
REQUEST_TIMEOUT = 15               # Timeout en segundos para requests HTTP
MAX_RETRIES = 3                    # Reintentos ante fallo de red
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# ─── Logging ──────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def ensure_dirs():
    """Crea los directorios de datos y configuración si no existen."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_urgency(days_remaining: int) -> str:
    """Calcula el nivel de urgencia basado en días restantes."""
    if days_remaining <= URGENCY_THRESHOLDS["red"]:
        return "red"
    elif days_remaining <= URGENCY_THRESHOLDS["orange"]:
        return "orange"
    elif days_remaining <= URGENCY_THRESHOLDS["yellow"]:
        return "yellow"
    else:
        return "green"

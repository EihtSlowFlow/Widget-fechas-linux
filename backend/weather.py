"""
Módulo meteorológico para Fechas Académicas.

Consulta el pronóstico horario del día actual mediante Open-Meteo
y calcula el clima esperado al finalizar la última actividad académica.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from backend.config import (
    WEATHER_REQUEST_TIMEOUT,
    MAX_WEATHER_TIME_DIFFERENCE_MINUTES,
)
from backend.models import HourlyWeather, TodayWeather

logger = logging.getLogger("fechas.weather")

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# ─── Mapeo WMO weather codes → emojis ────────────────────────────
_WMO_ICONS_DAY = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    56: "🌧️", 57: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    66: "🌧️", 67: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "🌨️",
    77: "🌨️",
    80: "🌦️", 81: "🌧️", 82: "🌧️",
    85: "🌨️", 86: "🌨️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}
_WMO_ICONS_NIGHT = {
    0: "🌙", 1: "🌙", 2: "☁️", 3: "☁️",
}


def get_weather_icon(weather_code: int, is_day: bool) -> str:
    """Convierte un código WMO a emoji meteorológico."""
    if not is_day and weather_code in _WMO_ICONS_NIGHT:
        return _WMO_ICONS_NIGHT[weather_code]
    return _WMO_ICONS_DAY.get(weather_code, "🌡️")


# ─── Consulta de pronóstico ───────────────────────────────────────

def fetch_today_weather(
    latitude: float,
    longitude: float,
    timezone: str,
) -> TodayWeather:
    """
    Consulta el pronóstico horario del día actual desde Open-Meteo.

    Args:
        latitude: Latitud de la ubicación.
        longitude: Longitud de la ubicación.
        timezone: Zona horaria IANA (e.g. 'America/Argentina/Salta').

    Returns:
        TodayWeather con datos actuales y pronóstico horario del día.

    Raises:
        requests.RequestException: Si falla la consulta HTTP.
        ValueError: Si la respuesta tiene formato inesperado.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join([
            "temperature_2m",
            "apparent_temperature",
            "precipitation_probability",
            "weather_code",
            "wind_speed_10m",
            "is_day",
        ]),
        "current": ",".join([
            "temperature_2m",
            "apparent_temperature",
            "weather_code",
            "wind_speed_10m",
            "is_day",
        ]),
        "timezone": timezone,
        "forecast_days": 1,
    }

    response = requests.get(
        OPEN_METEO_FORECAST_URL,
        params=params,
        timeout=WEATHER_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()

    # ─── Parsear datos horarios ───────────────────────────────
    hourly_data = data.get("hourly", {})
    times = hourly_data.get("time", [])
    temps = hourly_data.get("temperature_2m", [])
    apparent = hourly_data.get("apparent_temperature", [])
    precip = hourly_data.get("precipitation_probability", [])
    codes = hourly_data.get("weather_code", [])
    winds = hourly_data.get("wind_speed_10m", [])
    is_days = hourly_data.get("is_day", [])

    # Validar que las listas principales tengan la misma longitud
    lengths = [len(times), len(temps), len(apparent), len(codes)]
    if len(set(lengths)) > 1:
        raise ValueError(
            f"Listas horarias de distinta longitud: {lengths}"
        )

    n = len(times)
    hourly: list[HourlyWeather] = []
    for i in range(n):
        hourly.append(HourlyWeather(
            time=times[i],
            temperature=temps[i],
            apparent_temperature=apparent[i],
            precipitation_probability=precip[i] if i < len(precip) else None,
            weather_code=codes[i],
            wind_speed=winds[i] if i < len(winds) else None,
            is_day=bool(is_days[i]) if i < len(is_days) else True,
        ))

    # ─── Parsear datos actuales ───────────────────────────────
    current_data = data.get("current", {})
    current = None
    if current_data and "temperature_2m" in current_data:
        current_time = current_data.get("time", "")

        # Obtener probabilidad de lluvia del registro horario más cercano
        current_precip = None
        if current_time and hourly:
            try:
                closest = find_weather_at_time(
                    hourly,
                    datetime.fromisoformat(current_time),
                )
                if closest:
                    current_precip = closest.precipitation_probability
            except (ValueError, TypeError):
                pass

        current = HourlyWeather(
            time=current_time,
            temperature=current_data.get("temperature_2m", 0),
            apparent_temperature=current_data.get("apparent_temperature", 0),
            precipitation_probability=current_precip,
            weather_code=current_data.get("weather_code", 0),
            wind_speed=current_data.get("wind_speed_10m"),
            is_day=bool(current_data.get("is_day", 1)),
        )

    now_iso = datetime.now(ZoneInfo(timezone)).isoformat()

    return TodayWeather(
        location_name="",
        timezone=timezone,
        updated_at=now_iso,
        current=current,
        hourly=hourly,
    )


# ─── Búsqueda de registro horario ────────────────────────────────

def find_weather_at_time(
    hourly_weather: list[HourlyWeather],
    target_time: datetime,
) -> HourlyWeather | None:
    """
    Busca el registro horario más cercano a target_time.

    - Solo busca registros de la misma fecha local.
    - Devuelve None si la diferencia mínima supera MAX_WEATHER_TIME_DIFFERENCE_MINUTES.
    - En caso de empate, prefiere la hora posterior.
    """
    if not hourly_weather:
        return None

    target_date = target_time.date()
    best = None
    best_diff = None

    for hw in hourly_weather:
        try:
            hw_time = datetime.fromisoformat(hw.time)
        except (ValueError, TypeError):
            continue

        # Solo registros de la misma fecha
        if hw_time.date() != target_date:
            continue

        # Compatibilizar offset-aware/naive para comparación
        if target_time.tzinfo is not None and hw_time.tzinfo is None:
            hw_time = hw_time.replace(tzinfo=target_time.tzinfo)
        elif target_time.tzinfo is None and hw_time.tzinfo is not None:
            pass  # Comparar tal cual

        diff_seconds = (hw_time - target_time).total_seconds()
        abs_diff = abs(diff_seconds)

        if best_diff is None or abs_diff < best_diff:
            best = hw
            best_diff = abs_diff
        elif abs_diff == best_diff and diff_seconds > 0:
            # Empate: preferir hora posterior
            best = hw

    if best is None or best_diff is None:
        return None

    max_diff_seconds = MAX_WEATHER_TIME_DIFFERENCE_MINUTES * 60
    if best_diff > max_diff_seconds:
        return None

    return best


# ─── Cálculo de clima para la vuelta ─────────────────────────────

def calculate_return_weather(
    schedule: list[dict],
    hourly_weather: list[HourlyWeather],
    now: datetime,
    return_trip_minutes: int = 0,
) -> dict:
    """
    Calcula el clima esperado al finalizar la última actividad académica de hoy.

    Args:
        schedule: Lista de entradas de weekly_schedule.
        hourly_weather: Pronóstico horario del día.
        now: Momento actual con zona horaria IANA.
        return_trip_minutes: Minutos estimados de regreso a casa.

    Returns:
        Dict con campo 'status' obligatorio:
        - 'upcoming': Última actividad aún no terminó.
        - 'completed': Todas las actividades ya finalizaron.
        - 'no_activities': No hay actividades hoy.
        - 'unavailable': Faltan datos meteorológicos.
    """
    today = now.date()

    # day_of_week: 1=lunes..7=domingo (compatible con ClassScheduleEntry)
    day_of_week = today.isoweekday()

    # Filtrar actividades de hoy
    today_entries = [
        entry for entry in schedule
        if entry.get("day_of_week") == day_of_week
    ]

    if not today_entries:
        return {"status": "no_activities"}

    # Ordenar por end_time y tomar la última
    today_entries.sort(key=lambda e: e.get("end_time", ""))
    last_entry = today_entries[-1]
    end_time_str = last_entry.get("end_time", "")

    if not end_time_str:
        return {"status": "no_activities"}

    # Construir datetime de finalización en la zona horaria actual
    try:
        end_hour, end_minute = map(int, end_time_str.split(":"))
        activity_end = now.replace(
            hour=end_hour, minute=end_minute, second=0, microsecond=0
        )
    except (ValueError, TypeError):
        return {"status": "unavailable"}

    # ¿La última actividad ya terminó?
    if now >= activity_end:
        return {"status": "completed"}

    # Hora estimada de regreso
    estimated_return = activity_end + timedelta(minutes=return_trip_minutes)
    return_crosses_midnight = estimated_return.date() > today

    # Buscar clima al finalizar la actividad
    weather_at_end = find_weather_at_time(hourly_weather, activity_end)
    if weather_at_end is None:
        return {"status": "unavailable"}

    # Buscar clima al regresar (null si cruza medianoche)
    weather_at_return = None
    if return_trip_minutes > 0 and not return_crosses_midnight:
        weather_at_return = find_weather_at_time(
            hourly_weather, estimated_return
        )

    # Temperatura actual (del registro horario más cercano a now)
    current_temp = None
    closest_to_now = find_weather_at_time(hourly_weather, now)
    if closest_to_now:
        current_temp = closest_to_now.temperature

    # Diferencia de temperatura
    end_temp = weather_at_end.temperature
    temp_diff = (
        round(end_temp - current_temp, 1)
        if current_temp is not None
        else None
    )

    return {
        "status": "upcoming",
        "last_activity": {
            "subject_name": last_entry.get("subject_name", ""),
            "end_time": end_time_str,
            "location": last_entry.get("location", ""),
        },
        "activity_end_at": activity_end.isoformat(),
        "estimated_return_at": estimated_return.isoformat(),
        "weather_at_end": weather_at_end.to_dict(),
        "weather_at_return": (
            weather_at_return.to_dict() if weather_at_return else None
        ),
        "current_temperature": current_temp,
        "end_temperature": end_temp,
        "temperature_diff": temp_diff,
    }


# ─── Geocoding ────────────────────────────────────────────────────

def geocode_location(query: str) -> list[dict]:
    """
    Busca localidades mediante la Geocoding API de Open-Meteo.

    Returns:
        Lista de hasta 5 resultados con name, country, admin1,
        latitude, longitude, timezone.
    """
    if not query or not query.strip():
        return []

    params = {
        "name": query.strip(),
        "count": 5,
        "language": "es",
        "format": "json",
    }

    response = requests.get(
        OPEN_METEO_GEOCODING_URL,
        params=params,
        timeout=WEATHER_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()

    results = []
    for r in data.get("results", []):
        results.append({
            "name": r.get("name", ""),
            "country": r.get("country", ""),
            "admin1": r.get("admin1", ""),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "timezone": r.get("timezone", ""),
        })

    return results

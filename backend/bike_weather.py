"""
Indicador meteorológico para decidir si las condiciones de la vuelta favorecen
el uso de bicicleta en la ruta habitual.
"""

from __future__ import annotations

from math import cos, radians
from typing import Iterable

from backend.models import HourlyWeather

# Ida: SE -> NE -> SE -> NE -> SE -> SE.
# Vuelta: inversión exacta de cada tramo.
OUTBOUND_HEADINGS = (135.0, 45.0, 135.0, 45.0, 135.0, 135.0)
RETURN_HEADINGS = tuple((heading + 180.0) % 360.0 for heading in OUTBOUND_HEADINGS)

EXTREME_HEADWIND_KMH = 40.0
EXTREME_CROSSWIND_KMH = 45.0
STRONG_WIND_KMH = 30.0
HEAVY_RAIN_CODES = frozenset({65, 67, 82, 95, 96, 97, 99})


def _angular_difference(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def wind_components(
    wind_direction: float | None,
    wind_speed: float | None,
    headings: Iterable[float] = RETURN_HEADINGS,
) -> dict:
    """Calcula componentes de frente y lateral para cada tramo."""
    empty = {
        "max_headwind_kmh": None,
        "max_crosswind_kmh": None,
        "mean_headwind_kmh": None,
        "worst_heading": None,
    }
    if wind_direction is None or wind_speed is None:
        return empty

    try:
        direction = float(wind_direction) % 360.0
        speed = max(0.0, float(wind_speed))
    except (TypeError, ValueError):
        return empty

    components = []
    for heading in headings:
        angle = _angular_difference(direction, heading)
        headwind = max(0.0, speed * cos(radians(angle)))
        crosswind = abs(speed * cos(radians(angle + 90.0)))
        components.append((headwind, crosswind, heading))

    worst = max(components, key=lambda item: item[0])
    return {
        "max_headwind_kmh": round(max(item[0] for item in components), 1),
        "max_crosswind_kmh": round(max(item[1] for item in components), 1),
        "mean_headwind_kmh": round(sum(item[0] for item in components) / len(components), 1),
        "worst_heading": worst[2],
    }


def _is_heavy_rain(weather: HourlyWeather) -> bool:
    """Detecta lluvia fuerte o tormenta usando los datos disponibles."""
    if weather.weather_code in HEAVY_RAIN_CODES:
        return True
    precipitation = getattr(weather, "precipitation", None)
    try:
        return precipitation is not None and float(precipitation) >= 4.0
    except (TypeError, ValueError):
        return False


def evaluate_bike_trip(return_weather: dict | None) -> dict:
    """
    Resume las condiciones de la vuelta.

    go       = no se detecta condición relevante.
    caution  = lluvia probable o viento fuerte, sin umbral extremo.
    avoid    = lluvia fuerte nocturna o viento extremo para la ruta.
    """
    unavailable = {
        "status": "unavailable",
        "label": "Sin datos",
        "icon": "❔",
        "reasons": [],
    }
    if not return_weather or return_weather.get("status") != "upcoming":
        return unavailable

    weather = return_weather.get("weather_at_return") or return_weather.get("weather_at_end")
    if not weather:
        return unavailable

    hourly = HourlyWeather.from_dict(weather)
    components = wind_components(hourly.wind_direction, hourly.wind_speed)
    max_headwind = components["max_headwind_kmh"]
    max_crosswind = components["max_crosswind_kmh"]

    heavy_rain = _is_heavy_rain(hourly)
    reasons = []
    if heavy_rain:
        reasons.append("lluvia fuerte")
    elif hourly.precipitation_probability is not None and hourly.precipitation_probability >= 70:
        reasons.append("alta probabilidad de lluvia")

    if max_headwind is not None:
        if max_headwind >= EXTREME_HEADWIND_KMH:
            reasons.append(f"viento de frente de hasta {max_headwind:.0f} km/h")
        elif max_headwind >= STRONG_WIND_KMH:
            reasons.append(f"viento de frente de hasta {max_headwind:.0f} km/h")

    if max_crosswind is not None and max_crosswind >= EXTREME_CROSSWIND_KMH:
        reasons.append(f"viento lateral de hasta {max_crosswind:.0f} km/h")

    is_night = not hourly.is_day
    heavy_rain_at_night = is_night and heavy_rain
    extreme_wind = (
        (max_headwind is not None and max_headwind >= EXTREME_HEADWIND_KMH)
        or (max_crosswind is not None and max_crosswind >= EXTREME_CROSSWIND_KMH)
    )

    if heavy_rain_at_night or extreme_wind:
        status, label, icon = "avoid", "No conviene", "🚲⚠️"
    elif reasons:
        status, label, icon = "caution", "Precaución", "🚲🟡"
    else:
        status, label, icon = "go", "Conviene ir en bici", "🚲🟢"

    return {
        "status": status,
        "label": label,
        "icon": icon,
        "is_night": is_night,
        "heavy_rain": heavy_rain,
        "heavy_rain_at_night": heavy_rain_at_night,
        "wind_speed_kmh": hourly.wind_speed,
        "wind_direction_deg": hourly.wind_direction,
        "max_headwind_kmh": max_headwind,
        "max_crosswind_kmh": max_crosswind,
        "mean_headwind_kmh": components["mean_headwind_kmh"],
        "worst_heading": components["worst_heading"],
        "reasons": reasons,
        "return_at": weather.get("time", ""),
    }

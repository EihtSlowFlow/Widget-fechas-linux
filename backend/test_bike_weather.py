"""Pruebas del indicador meteorológico para bicicleta.

Escenarios de lluvia con dirección:
  - Lluvia fuerte + noche + componente frontal → avoid
  - Lluvia fuerte + noche + viento de cola → caution (no avoid)
  - Lluvia fuerte + día + componente frontal → caution
  - Lluvia fuerte + viento lateral → caution
  - Sin lluvia, condiciones normales → go
"""

import unittest

from backend.bike_weather import (
    FRONTAL_RAIN_THRESHOLD_KMH,
    RETURN_HEADINGS,
    evaluate_bike_trip,
    wind_components,
    _has_frontal_rain_component,
)


def make_weather(
    *, speed=10.0, direction=135.0, code=0, precip=0,
    precip_probability=0, is_day=False
):
    return {
        "time": "2026-09-29T22:00",
        "temperature": 12.0,
        "apparent_temperature": 9.0,
        "precipitation_probability": precip_probability,
        "precipitation": precip,
        "weather_code": code,
        "wind_speed": speed,
        "wind_direction": direction,
        "is_day": is_day,
    }


def _trip(weather_dict):
    return evaluate_bike_trip({
        "status": "upcoming",
        "weather_at_return": weather_dict,
    })


class TestWindComponents(unittest.TestCase):
    def test_headwind_matches_return_heading(self):
        # Viento desde 315° (NW) golpea de frente al tramo NW (315°).
        self.assertEqual(wind_components(315.0, 40.0)["max_headwind_kmh"], 40.0)

    def test_tailwind_is_not_headwind(self):
        # Viento desde 135° (SE) es cola en tramos NW → 0 headwind.
        self.assertEqual(wind_components(135.0, 40.0)["max_headwind_kmh"], 0.0)

    def test_return_route_headings(self):
        self.assertEqual(RETURN_HEADINGS, (315.0, 225.0, 315.0, 225.0, 315.0, 315.0))


class TestFrontalRainComponent(unittest.TestCase):
    def test_above_threshold_is_frontal(self):
        self.assertTrue(_has_frontal_rain_component(FRONTAL_RAIN_THRESHOLD_KMH))

    def test_below_threshold_is_not_frontal(self):
        self.assertFalse(_has_frontal_rain_component(FRONTAL_RAIN_THRESHOLD_KMH - 1))

    def test_none_is_not_frontal(self):
        self.assertFalse(_has_frontal_rain_component(None))


class TestBikeAdvice(unittest.TestCase):
    # ─── Lluvia frontal nocturna: AVOID ───────────────────────────
    def test_heavy_rain_frontal_at_night_is_avoid(self):
        """Lluvia fuerte + noche + viento de frente = visibilidad comprometida."""
        # Viento desde 315° (NW) → máxima componente frontal en tramos NW.
        result = _trip(make_weather(code=65, speed=20.0, direction=315.0))
        self.assertEqual(result["status"], "avoid")
        self.assertTrue(result["frontal_rain"])
        self.assertTrue(result["frontal_rain_at_night"])
        self.assertTrue(any("visibilidad" in r for r in result["reasons"]))

    # ─── Lluvia fuerte con viento de cola de noche: CAUTION ───────
    def test_heavy_rain_tailwind_at_night_is_caution(self):
        """Lluvia fuerte + noche + viento de cola → te mojás, pero ves bien."""
        # Viento desde 135° (SE) = cola en los tramos NW → headwind ≈ 0.
        result = _trip(make_weather(code=65, speed=20.0, direction=135.0))
        self.assertEqual(result["status"], "caution")
        self.assertTrue(result["heavy_rain"])
        self.assertFalse(result["frontal_rain"])
        self.assertFalse(result["frontal_rain_at_night"])
        self.assertTrue(any("lateral/cola" in r for r in result["reasons"]))

    # ─── Lluvia fuerte lateral de noche: CAUTION ──────────────────
    def test_heavy_rain_crosswind_at_night_is_caution(self):
        """Lluvia fuerte con viento puramente lateral → precaución, no avoid."""
        # Viento desde 45° (NE) produce cross en tramos NW, head en SW.
        # A velocidad baja la componente frontal no supera el umbral.
        result = _trip(make_weather(code=65, speed=8.0, direction=45.0))
        self.assertEqual(result["status"], "caution")
        self.assertFalse(result["frontal_rain"])

    # ─── Lluvia frontal de DÍA: CAUTION ──────────────────────────
    def test_heavy_rain_frontal_during_day_is_caution(self):
        """Lluvia de frente de día es precaución, no avoid (hay luz)."""
        result = _trip(make_weather(code=65, speed=20.0, direction=315.0, is_day=True))
        self.assertEqual(result["status"], "caution")
        self.assertTrue(result["frontal_rain"])
        self.assertFalse(result["frontal_rain_at_night"])

    # ─── Viento extremo sigue siendo AVOID independientemente ────
    def test_extreme_headwind_is_avoid(self):
        result = _trip(make_weather(speed=45.0, direction=315.0))
        self.assertEqual(result["status"], "avoid")

    # ─── Viento fuerte pero no extremo: CAUTION ──────────────────
    def test_strong_but_not_extreme_wind_is_caution(self):
        result = _trip(make_weather(speed=32.0, direction=315.0))
        self.assertEqual(result["status"], "caution")

    # ─── Condiciones normales: GO ─────────────────────────────────
    def test_moderate_conditions_are_go(self):
        # Viento suave de cola, sin lluvia.
        result = _trip(make_weather(speed=15.0, direction=135.0))
        self.assertEqual(result["status"], "go")

    # ─── Alta probabilidad de lluvia sin lluvia fuerte: CAUTION ───
    def test_high_precipitation_probability_is_caution(self):
        result = _trip(make_weather(precip_probability=80))
        self.assertEqual(result["status"], "caution")
        self.assertTrue(any("probabilidad" in r for r in result["reasons"]))

    # ─── Sin datos: UNAVAILABLE ───────────────────────────────────
    def test_missing_weather_is_unavailable(self):
        self.assertEqual(evaluate_bike_trip({"status": "upcoming"})["status"], "unavailable")

    def test_none_weather_is_unavailable(self):
        self.assertEqual(evaluate_bike_trip(None)["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()

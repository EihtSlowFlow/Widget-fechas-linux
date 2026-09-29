"""Pruebas del indicador meteorológico para bicicleta."""

import unittest

from backend.bike_weather import RETURN_HEADINGS, evaluate_bike_trip, wind_components


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


class TestWindComponents(unittest.TestCase):
    def test_headwind_matches_return_heading(self):
        self.assertEqual(wind_components(315.0, 40.0)["max_headwind_kmh"], 40.0)

    def test_tailwind_is_not_headwind(self):
        self.assertEqual(wind_components(135.0, 40.0)["max_headwind_kmh"], 0.0)

    def test_return_route_headings(self):
        self.assertEqual(RETURN_HEADINGS, (315.0, 225.0, 315.0, 225.0, 315.0, 315.0))


class TestBikeAdvice(unittest.TestCase):
    def test_heavy_night_rain_is_avoid(self):
        result = evaluate_bike_trip({
            "status": "upcoming",
            "weather_at_return": make_weather(code=65),
        })
        self.assertEqual(result["status"], "avoid")
        self.assertTrue(result["heavy_rain_at_night"])

    def test_extreme_headwind_is_avoid(self):
        result = evaluate_bike_trip({
            "status": "upcoming",
            "weather_at_return": make_weather(speed=45.0, direction=315.0),
        })
        self.assertEqual(result["status"], "avoid")

    def test_moderate_conditions_are_go(self):
        result = evaluate_bike_trip({
            "status": "upcoming",
            "weather_at_return": make_weather(speed=15.0, direction=135.0),
        })
        self.assertEqual(result["status"], "go")

    def test_strong_but_not_extreme_wind_is_caution(self):
        result = evaluate_bike_trip({
            "status": "upcoming",
            "weather_at_return": make_weather(speed=32.0, direction=315.0),
        })
        self.assertEqual(result["status"], "caution")

    def test_missing_weather_is_unavailable(self):
        self.assertEqual(evaluate_bike_trip({"status": "upcoming"})["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()

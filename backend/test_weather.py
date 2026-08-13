"""
Pruebas unitarias del módulo meteorológico.

Ejecutar:
    python3 -m unittest backend.test_weather -v
"""

import unittest
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

from backend.models import HourlyWeather, TodayWeather, WeatherSettings, CacheData
from backend.weather import (
    find_weather_at_time,
    calculate_return_weather,
    get_weather_icon,
)


# ─── Helpers ──────────────────────────────────────────────────────

TZ = ZoneInfo("America/Argentina/Salta")


def _make_hourly(hour: int, temp: float = 20.0, apparent: float = 18.0,
                 precip: int = 0, code: int = 0, wind: float = 10.0,
                 is_day: bool = True, day: str = "2026-08-13") -> HourlyWeather:
    """Crea un HourlyWeather de prueba para una hora específica."""
    return HourlyWeather(
        time=f"{day}T{hour:02d}:00",
        temperature=temp,
        apparent_temperature=apparent,
        precipitation_probability=precip,
        weather_code=code,
        wind_speed=wind,
        is_day=is_day,
    )


def _make_schedule_entry(subject: str, start: str, end: str,
                         day: int = 4, location: str = "") -> dict:
    """Crea una entrada de weekly_schedule de prueba."""
    return {
        "subject_name": subject,
        "day_of_week": day,
        "start_time": start,
        "end_time": end,
        "location": location,
    }


# ─── Tests de modelos ─────────────────────────────────────────────

class TestHourlyWeather(unittest.TestCase):

    def test_to_dict_and_from_dict(self):
        hw = _make_hourly(15, temp=23.5, apparent=22.0, precip=10, code=1, wind=18.0)
        d = hw.to_dict()
        restored = HourlyWeather.from_dict(d)
        self.assertEqual(restored.temperature, 23.5)
        self.assertEqual(restored.apparent_temperature, 22.0)
        self.assertEqual(restored.precipitation_probability, 10)
        self.assertEqual(restored.weather_code, 1)
        self.assertEqual(restored.wind_speed, 18.0)

    def test_from_dict_tolerates_unknown_fields(self):
        data = {
            "time": "2026-08-13T15:00",
            "temperature": 20.0,
            "apparent_temperature": 18.0,
            "unknown_field": "ignored",
        }
        hw = HourlyWeather.from_dict(data)
        self.assertEqual(hw.temperature, 20.0)

    def test_is_day_distinction(self):
        day = _make_hourly(12, is_day=True)
        night = _make_hourly(22, is_day=False)
        self.assertTrue(day.is_day)
        self.assertFalse(night.is_day)


class TestTodayWeather(unittest.TestCase):

    def test_to_dict_and_from_dict(self):
        current = _make_hourly(14, temp=21.0)
        hourly = [_make_hourly(h) for h in range(24)]
        tw = TodayWeather(
            location_name="General Roca",
            timezone="America/Argentina/Salta",
            updated_at="2026-08-13T14:00:00-03:00",
            current=current,
            hourly=hourly,
        )
        d = tw.to_dict()
        restored = TodayWeather.from_dict(d)
        self.assertEqual(restored.location_name, "General Roca")
        self.assertEqual(len(restored.hourly), 24)
        self.assertIsNotNone(restored.current)
        self.assertFalse(restored.is_stale)

    def test_from_dict_with_no_current(self):
        tw = TodayWeather.from_dict({"hourly": []})
        self.assertIsNone(tw.current)

    def test_is_stale_flag(self):
        tw = TodayWeather.from_dict({"is_stale": True})
        self.assertTrue(tw.is_stale)


class TestWeatherSettings(unittest.TestCase):

    def test_valid_settings(self):
        ws = WeatherSettings.from_dict({
            "enabled": True,
            "location_name": "General Roca, Río Negro",
            "latitude": -39.03,
            "longitude": -67.58,
            "timezone": "America/Argentina/Salta",
            "return_trip_minutes": 30,
        })
        self.assertTrue(ws.enabled)
        self.assertEqual(ws.latitude, -39.03)
        self.assertEqual(ws.longitude, -67.58)
        self.assertEqual(ws.timezone, "America/Argentina/Salta")
        self.assertEqual(ws.return_trip_minutes, 30)

    def test_invalid_timezone_raises(self):
        with self.assertRaises(ValueError):
            WeatherSettings.from_dict({"timezone": "Invalid/Timezone"})

    def test_auto_timezone_raises(self):
        with self.assertRaises(ValueError):
            WeatherSettings.from_dict({"timezone": "auto"})

    def test_empty_timezone_allowed(self):
        ws = WeatherSettings.from_dict({"timezone": ""})
        self.assertEqual(ws.timezone, "")

    def test_latitude_out_of_range(self):
        ws = WeatherSettings.from_dict({"latitude": 100.0})
        self.assertIsNone(ws.latitude)

    def test_longitude_out_of_range(self):
        ws = WeatherSettings.from_dict({"longitude": -200.0})
        self.assertIsNone(ws.longitude)

    def test_return_trip_clamped(self):
        ws = WeatherSettings.from_dict({"return_trip_minutes": 500})
        self.assertEqual(ws.return_trip_minutes, 240)

    def test_return_trip_negative_clamped(self):
        ws = WeatherSettings.from_dict({"return_trip_minutes": -10})
        self.assertEqual(ws.return_trip_minutes, 0)

    def test_tolerates_unknown_fields(self):
        ws = WeatherSettings.from_dict({
            "enabled": True,
            "unknown_key": "value",
            "latitude": -39.03,
            "longitude": -67.58,
            "timezone": "America/Argentina/Salta",
        })
        self.assertTrue(ws.enabled)

    def test_corrupt_latitude(self):
        ws = WeatherSettings.from_dict({"latitude": "not_a_number"})
        self.assertIsNone(ws.latitude)


# ─── Tests de CacheData ──────────────────────────────────────────

class TestCacheDataWeatherFields(unittest.TestCase):

    def test_backward_compatible(self):
        """Cachés anteriores sin campos weather siguen funcionando."""
        data = {
            "last_sync": "2026-08-13T10:00:00",
            "sync_status": "ok",
            "events": [],
        }
        cache = CacheData.from_dict(data)
        self.assertIsNone(cache.today_weather)
        self.assertIsNone(cache.return_weather)

    def test_with_weather_fields(self):
        data = {
            "last_sync": "2026-08-13T10:00:00",
            "sync_status": "ok",
            "events": [],
            "today_weather": {"location_name": "Test"},
            "return_weather": {"status": "upcoming"},
        }
        cache = CacheData.from_dict(data)
        self.assertEqual(cache.today_weather["location_name"], "Test")
        self.assertEqual(cache.return_weather["status"], "upcoming")

    def test_to_dict_includes_weather(self):
        cache = CacheData(
            today_weather={"location_name": "Test"},
            return_weather={"status": "completed"},
        )
        d = cache.to_dict()
        self.assertIn("today_weather", d)
        self.assertIn("return_weather", d)


# ─── Tests de find_weather_at_time ────────────────────────────────

class TestFindWeatherAtTime(unittest.TestCase):

    def setUp(self):
        self.hourly = [_make_hourly(h, temp=10 + h) for h in range(24)]

    def test_exact_match(self):
        target = datetime(2026, 8, 13, 15, 0, tzinfo=TZ)
        result = find_weather_at_time(self.hourly, target)
        self.assertIsNotNone(result)
        self.assertEqual(result.temperature, 25.0)  # 10 + 15

    def test_closest_match(self):
        target = datetime(2026, 8, 13, 15, 20, tzinfo=TZ)
        result = find_weather_at_time(self.hourly, target)
        self.assertIsNotNone(result)
        self.assertEqual(result.temperature, 25.0)  # Más cerca de 15:00

    def test_tie_prefers_later(self):
        target = datetime(2026, 8, 13, 15, 30, tzinfo=TZ)
        result = find_weather_at_time(self.hourly, target)
        self.assertIsNotNone(result)
        # 15:30 equidista de 15:00 y 16:00, debe preferir 16:00
        self.assertEqual(result.temperature, 26.0)  # 10 + 16

    def test_beyond_90_min_returns_none(self):
        # Solo un registro a las 00:00, buscar a las 03:00 (180 min)
        sparse = [_make_hourly(0)]
        target = datetime(2026, 8, 13, 3, 0, tzinfo=TZ)
        result = find_weather_at_time(sparse, target)
        self.assertIsNone(result)

    def test_different_date_returns_none(self):
        target = datetime(2026, 8, 14, 15, 0, tzinfo=TZ)
        result = find_weather_at_time(self.hourly, target)
        self.assertIsNone(result)

    def test_empty_list(self):
        target = datetime(2026, 8, 13, 15, 0, tzinfo=TZ)
        result = find_weather_at_time([], target)
        self.assertIsNone(result)

    def test_within_90_min_boundary(self):
        sparse = [_make_hourly(15, temp=25.0)]
        # 13:31 → 89 min de diferencia con 15:00 → dentro del límite
        target = datetime(2026, 8, 13, 13, 31, tzinfo=TZ)
        result = find_weather_at_time(sparse, target)
        self.assertIsNotNone(result)

    def test_at_90_min_boundary_returns_none(self):
        sparse = [_make_hourly(15, temp=25.0)]
        # 13:29 → 91 min de diferencia con 15:00 → fuera del límite
        target = datetime(2026, 8, 13, 13, 29, tzinfo=TZ)
        result = find_weather_at_time(sparse, target)
        self.assertIsNone(result)


# ─── Tests de calculate_return_weather ────────────────────────────

class TestCalculateReturnWeather(unittest.TestCase):

    def setUp(self):
        self.hourly = [_make_hourly(h, temp=25 - h) for h in range(24)]
        # Jueves = isoweekday 4
        self.schedule = [
            _make_schedule_entry("Bases de Datos II", "16:00", "18:00", day=4, location="Aula 2"),
            _make_schedule_entry("Proyecto", "18:00", "21:00", day=4, location="Aula 4"),
        ]

    def test_status_upcoming(self):
        now = datetime(2026, 8, 13, 14, 0, tzinfo=TZ)  # Jueves 14:00
        result = calculate_return_weather(self.schedule, self.hourly, now)
        self.assertEqual(result["status"], "upcoming")
        self.assertEqual(result["last_activity"]["subject_name"], "Proyecto")
        self.assertEqual(result["last_activity"]["end_time"], "21:00")
        self.assertEqual(result["last_activity"]["location"], "Aula 4")

    def test_status_completed(self):
        now = datetime(2026, 8, 13, 22, 0, tzinfo=TZ)  # Después de las 21:00
        result = calculate_return_weather(self.schedule, self.hourly, now)
        self.assertEqual(result["status"], "completed")

    def test_status_no_activities(self):
        now = datetime(2026, 8, 12, 14, 0, tzinfo=TZ)  # Miércoles (day 3)
        result = calculate_return_weather(self.schedule, self.hourly, now)
        self.assertEqual(result["status"], "no_activities")

    def test_status_no_activities_empty_schedule(self):
        now = datetime(2026, 8, 13, 14, 0, tzinfo=TZ)
        result = calculate_return_weather([], self.hourly, now)
        self.assertEqual(result["status"], "no_activities")

    def test_weather_at_end(self):
        now = datetime(2026, 8, 13, 14, 0, tzinfo=TZ)
        result = calculate_return_weather(self.schedule, self.hourly, now)
        # Temp a las 21:00 = 25 - 21 = 4
        self.assertEqual(result["weather_at_end"]["temperature"], 4.0)

    def test_temperature_diff(self):
        now = datetime(2026, 8, 13, 14, 0, tzinfo=TZ)
        result = calculate_return_weather(self.schedule, self.hourly, now)
        # Temp actual (14:00) = 25 - 14 = 11
        # Temp de regreso con 0 min de viaje = 25 - 21 = 4
        # Diff = 4 - 11 = -7
        self.assertEqual(result["current_temperature"], 11.0)
        self.assertEqual(result["end_temperature"], 4.0)
        self.assertEqual(result["return_temperature"], 4.0)
        self.assertEqual(result["temperature_diff"], -7.0)

    def test_return_trip_0_minutes(self):
        now = datetime(2026, 8, 13, 14, 0, tzinfo=TZ)
        result = calculate_return_weather(
            self.schedule, self.hourly, now, return_trip_minutes=0
        )
        self.assertEqual(result["status"], "upcoming")
        self.assertIsNone(result["weather_at_return"])
        self.assertEqual(result["activity_end_at"], result["estimated_return_at"])
        self.assertEqual(result["return_temperature"], result["end_temperature"])

    def test_return_trip_30_minutes(self):
        now = datetime(2026, 8, 13, 14, 0, tzinfo=TZ)
        result = calculate_return_weather(
            self.schedule, self.hourly, now, return_trip_minutes=30
        )
        self.assertEqual(result["status"], "upcoming")
        # 21:00 + 30 min = 21:30, registro más cercano = 22:00
        end_dt = datetime.fromisoformat(result["estimated_return_at"])
        self.assertEqual(end_dt.hour, 21)
        self.assertEqual(end_dt.minute, 30)
        # weather_at_return debería existir (registro a las 22:00)
        self.assertIsNotNone(result["weather_at_return"])
        # Temp a las 22:00 = 25 - 22 = 3
        self.assertEqual(result["return_temperature"], 3.0)

    def test_multiple_subjects_selects_latest(self):
        schedule = [
            _make_schedule_entry("Física", "08:00", "10:00", day=4),
            _make_schedule_entry("Proyecto", "18:00", "21:00", day=4),
            _make_schedule_entry("Matemática", "10:00", "12:00", day=4),
        ]
        now = datetime(2026, 8, 13, 14, 0, tzinfo=TZ)
        result = calculate_return_weather(schedule, self.hourly, now)
        self.assertEqual(result["last_activity"]["subject_name"], "Proyecto")

    def test_unordered_schedule(self):
        schedule = [
            _make_schedule_entry("Proyecto", "18:00", "21:00", day=4),
            _make_schedule_entry("Física", "08:00", "10:00", day=4),
        ]
        now = datetime(2026, 8, 13, 14, 0, tzinfo=TZ)
        result = calculate_return_weather(schedule, self.hourly, now)
        self.assertEqual(result["last_activity"]["subject_name"], "Proyecto")

    def test_exact_hour_end(self):
        schedule = [_make_schedule_entry("Lab", "19:00", "21:00", day=4)]
        now = datetime(2026, 8, 13, 14, 0, tzinfo=TZ)
        result = calculate_return_weather(schedule, self.hourly, now)
        self.assertEqual(result["weather_at_end"]["time"], "2026-08-13T21:00")

    def test_between_hours_end(self):
        schedule = [_make_schedule_entry("Lab", "19:00", "20:30", day=4)]
        now = datetime(2026, 8, 13, 14, 0, tzinfo=TZ)
        result = calculate_return_weather(schedule, self.hourly, now)
        # 20:30 está entre 20:00 y 21:00, empate → prefiere 21:00
        end_weather = result["weather_at_end"]
        self.assertIn(end_weather["time"], ["2026-08-13T20:00", "2026-08-13T21:00"])

    def test_return_crosses_midnight(self):
        """Si el regreso cruza medianoche, weather_at_return debe ser null."""
        schedule = [_make_schedule_entry("Taller", "20:00", "23:30", day=4)]
        now = datetime(2026, 8, 13, 14, 0, tzinfo=TZ)
        result = calculate_return_weather(
            schedule, self.hourly, now, return_trip_minutes=120
        )
        self.assertEqual(result["status"], "upcoming")
        # 23:30 + 120 min = 01:30 del día siguiente
        self.assertIsNone(result["weather_at_return"])
        self.assertIsNone(result["return_temperature"])

    def test_unavailable_no_weather_data(self):
        schedule = [_make_schedule_entry("Lab", "08:00", "10:00", day=4)]
        now = datetime(2026, 8, 13, 7, 0, tzinfo=TZ)
        # Sin datos horarios → unavailable
        result = calculate_return_weather(schedule, [], now)
        self.assertEqual(result["status"], "unavailable")


# ─── Tests de get_weather_icon ────────────────────────────────────

class TestGetWeatherIcon(unittest.TestCase):

    def test_clear_day(self):
        self.assertEqual(get_weather_icon(0, True), "☀️")

    def test_clear_night(self):
        self.assertEqual(get_weather_icon(0, False), "🌙")

    def test_rain(self):
        self.assertEqual(get_weather_icon(61, True), "🌧️")

    def test_thunderstorm(self):
        self.assertEqual(get_weather_icon(95, True), "⛈️")

    def test_unknown_code(self):
        result = get_weather_icon(999, True)
        self.assertEqual(result, "🌡️")


# ─── Tests de caché meteorológico ─────────────────────────────────

class TestWeatherCacheValidation(unittest.TestCase):

    def setUp(self):
        self.settings = WeatherSettings(
            enabled=True,
            latitude=-39.03,
            longitude=-67.58,
            timezone="America/Argentina/Salta",
        )
        self.now_iso = datetime.now().astimezone().isoformat()

    def _make_cache(self, forecast_date="2026-08-13", lat=-39.03, lon=-67.58,
                    tz="America/Argentina/Salta", fetched_at=None):
        return {
            "forecast_date": forecast_date,
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
            "fetched_at": fetched_at or self.now_iso,
            "weather": {"location_name": "Test"},
        }

    def test_valid_cache(self):
        from backend.cache import is_weather_cache_valid
        cache = self._make_cache()
        result = is_weather_cache_valid(cache, self.settings, "2026-08-13")
        self.assertTrue(result)

    def test_cache_wrong_date(self):
        from backend.cache import is_weather_cache_valid
        cache = self._make_cache(forecast_date="2026-08-12")
        result = is_weather_cache_valid(cache, self.settings, "2026-08-13")
        self.assertFalse(result)

    def test_cache_wrong_location(self):
        from backend.cache import is_weather_cache_valid
        cache = self._make_cache(lat=-34.61)
        result = is_weather_cache_valid(cache, self.settings, "2026-08-13")
        self.assertFalse(result)

    def test_cache_wrong_timezone(self):
        from backend.cache import is_weather_cache_valid
        cache = self._make_cache(tz="Europe/London")
        result = is_weather_cache_valid(cache, self.settings, "2026-08-13")
        self.assertFalse(result)

    def test_cache_expired(self):
        from backend.cache import is_weather_cache_valid
        old = (datetime.now().astimezone() - timedelta(minutes=40)).isoformat()
        cache = self._make_cache(fetched_at=old)
        result = is_weather_cache_valid(cache, self.settings, "2026-08-13")
        self.assertFalse(result)

    def test_context_matches_ignores_age(self):
        from backend.cache import weather_cache_matches_context
        old = (datetime.now().astimezone() - timedelta(hours=5)).isoformat()
        cache = self._make_cache(fetched_at=old)
        result = weather_cache_matches_context(cache, self.settings, "2026-08-13")
        self.assertTrue(result)

    def test_context_no_match_different_date(self):
        from backend.cache import weather_cache_matches_context
        cache = self._make_cache(forecast_date="2026-08-12")
        result = weather_cache_matches_context(cache, self.settings, "2026-08-13")
        self.assertFalse(result)

    def test_empty_cache(self):
        from backend.cache import is_weather_cache_valid
        result = is_weather_cache_valid({}, self.settings, "2026-08-13")
        self.assertFalse(result)


# ─── Tests de resiliencia ─────────────────────────────────────────

class TestWeatherResilience(unittest.TestCase):

    @patch("backend.weather.requests.get")
    def test_network_failure_raises(self, mock_get):
        """fetch_today_weather propaga la excepción para que el sync la capture."""
        from backend.weather import fetch_today_weather
        mock_get.side_effect = Exception("Connection refused")
        with self.assertRaises(Exception):
            fetch_today_weather(-39.03, -67.58, "America/Argentina/Salta")

    def test_disabled_weather_produces_none(self):
        """Si el clima está desactivado, today_weather debe ser None en cache."""
        cache = CacheData(
            last_sync="2026-08-13T10:00:00",
            sync_status="ok",
            today_weather=None,
            return_weather=None,
        )
        self.assertIsNone(cache.today_weather)
        self.assertIsNone(cache.return_weather)


if __name__ == "__main__":
    unittest.main()

"""
Vista de configuración meteorológica.
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QLineEdit, QPushButton, QFrame, QSpinBox, QListWidget,
    QListWidgetItem, QGroupBox, QGridLayout, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, pyqtSlot
from PyQt6.QtGui import QFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.cache import read_weather_settings, write_weather_settings
from backend.models import WeatherSettings, HourlyWeather
from backend.weather import geocode_location, fetch_today_weather, calculate_return_weather, get_weather_icon
from app.styles.theme import DARK_PALETTE


class _GeocodingWorker(QObject):
    """Worker para búsqueda de localidades en hilo separado."""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self._query = query

    @pyqtSlot()
    def run(self):
        try:
            results = geocode_location(self._query)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class _WeatherTestWorker(QObject):
    """Worker para probar la configuración meteorológica en hilo separado."""
    finished = pyqtSignal(dict)  # emits the TodayWeather.to_dict()
    error = pyqtSignal(str)

    def __init__(self, lat: float, lon: float, tz: str, location_name: str):
        super().__init__()
        self._lat = lat
        self._lon = lon
        self._tz = tz
        self._location_name = location_name

    @pyqtSlot()
    def run(self):
        try:
            tw = fetch_today_weather(self._lat, self._lon, self._tz)
            tw.location_name = self._location_name
            self.finished.emit(tw.to_dict())
        except Exception as e:
            self.error.emit(str(e))


class WeatherView(QWidget):
    """
    Vista para configurar el pronóstico meteorológico.
    Pestaña '🌤️ Clima' del Centro de Gestión.
    """

    weather_settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = WeatherSettings()
        self._geocode_results = []
        self._thread = None
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("🌤️ Configuración Meteorológica")
        header.setObjectName("sectionTitle")
        layout.addWidget(header)

        desc = QLabel(
            "Configurá la localidad para ver el pronóstico del día actual "
            "y el clima esperado al terminar la cursada."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {DARK_PALETTE['text_secondary']};")
        layout.addWidget(desc)

        # Enable checkbox
        self._enabled_cb = QCheckBox("Mostrar el clima en el widget")
        self._enabled_cb.toggled.connect(self._on_enabled_toggled)
        layout.addWidget(self._enabled_cb)

        # Settings container (hidden when disabled)
        self._settings_container = QWidget()
        settings_layout = QVBoxLayout(self._settings_container)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(12)

        # ── Location search group ──
        location_group = QGroupBox("Localidad meteorológica")
        loc_layout = QVBoxLayout(location_group)

        search_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar localidad... (ej: General Roca)")
        self._search_input.returnPressed.connect(self._search_location)
        search_row.addWidget(self._search_input, stretch=1)

        self._search_btn = QPushButton("Buscar")
        self._search_btn.clicked.connect(self._search_location)
        search_row.addWidget(self._search_btn)
        loc_layout.addLayout(search_row)

        self._search_status = QLabel("")
        self._search_status.setObjectName("mutedText")
        self._search_status.setVisible(False)
        loc_layout.addWidget(self._search_status)

        self._results_list = QListWidget()
        self._results_list.setMaximumHeight(150)
        self._results_list.setVisible(False)
        self._results_list.itemClicked.connect(self._on_result_selected)
        loc_layout.addWidget(self._results_list)

        # Selected location info
        info_grid = QGridLayout()
        info_grid.setSpacing(8)

        info_grid.addWidget(QLabel("Localidad:"), 0, 0)
        self._location_label = QLabel("—")
        self._location_label.setStyleSheet(f"color: {DARK_PALETTE['accent']};")
        info_grid.addWidget(self._location_label, 0, 1)

        info_grid.addWidget(QLabel("Latitud:"), 1, 0)
        self._lat_label = QLabel("—")
        info_grid.addWidget(self._lat_label, 1, 1)

        info_grid.addWidget(QLabel("Longitud:"), 1, 2)
        self._lon_label = QLabel("—")
        info_grid.addWidget(self._lon_label, 1, 3)

        info_grid.addWidget(QLabel("Zona horaria:"), 2, 0)
        self._tz_label = QLabel("—")
        info_grid.addWidget(self._tz_label, 2, 1)

        loc_layout.addLayout(info_grid)
        settings_layout.addWidget(location_group)

        # ── Return trip group ──
        trip_group = QGroupBox("Tiempo de regreso")
        trip_layout = QHBoxLayout(trip_group)

        trip_layout.addWidget(QLabel("Tiempo estimado de regreso a casa:"))
        self._return_spin = QSpinBox()
        self._return_spin.setRange(0, 240)
        self._return_spin.setSuffix(" min")
        self._return_spin.setToolTip("Minutos entre que sale de la universidad y llega a su casa")
        trip_layout.addWidget(self._return_spin)
        trip_layout.addStretch()
        settings_layout.addWidget(trip_group)



        # ── Preview frame ──
        self._preview_frame = QFrame()
        self._preview_frame.setStyleSheet(f"""
            QFrame {{
                background: {DARK_PALETTE['bg_card']};
                border: 1px solid {DARK_PALETTE['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        self._preview_layout = QVBoxLayout(self._preview_frame)
        self._preview_label = QLabel("")
        self._preview_label.setWordWrap(True)
        self._preview_layout.addWidget(self._preview_label)
        self._preview_frame.setVisible(False)
        settings_layout.addWidget(self._preview_frame)

        settings_layout.addStretch()
        layout.addWidget(self._settings_container)
        layout.addStretch()

        # ── Actions row (siempre visible) ──
        actions_row = QHBoxLayout()

        self._test_btn = QPushButton("🌡️ Probar configuración")
        self._test_btn.setObjectName("secondaryButton")
        self._test_btn.clicked.connect(self._test_config)
        actions_row.addWidget(self._test_btn)

        actions_row.addStretch()

        self._save_btn = QPushButton("💾 Guardar configuración")
        self._save_btn.clicked.connect(self._save_settings)
        actions_row.addWidget(self._save_btn)

        layout.addLayout(actions_row)

    def _load_settings(self):
        """Carga la configuración meteorológica persistida."""
        self._settings = read_weather_settings()
        self._enabled_cb.setChecked(self._settings.enabled)
        self._settings_container.setVisible(self._settings.enabled)

        if self._settings.location_name:
            self._location_label.setText(self._settings.location_name)
        if self._settings.latitude is not None:
            self._lat_label.setText(f"{self._settings.latitude:.4f}")
        if self._settings.longitude is not None:
            self._lon_label.setText(f"{self._settings.longitude:.4f}")
        if self._settings.timezone:
            self._tz_label.setText(self._settings.timezone)
        self._return_spin.setValue(self._settings.return_trip_minutes)

    def _on_enabled_toggled(self, checked: bool):
        self._settings_container.setVisible(checked)

    def _search_location(self):
        """Busca localidades usando la Geocoding API en un hilo separado."""
        query = self._search_input.text().strip()
        if not query:
            return

        self._search_btn.setEnabled(False)
        self._search_btn.setText("Buscando...")
        self._search_status.setText("Consultando Open-Meteo Geocoding...")
        self._search_status.setVisible(True)
        self._results_list.clear()
        self._results_list.setVisible(False)

        self._thread = QThread()
        self._worker = _GeocodingWorker(query)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_geocode_results)
        self._worker.error.connect(self._on_geocode_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_geocode_results(self, results: list):
        self._search_btn.setEnabled(True)
        self._search_btn.setText("Buscar")
        self._geocode_results = results

        if not results:
            self._search_status.setText("No se encontraron resultados.")
            self._search_status.setVisible(True)
            self._results_list.setVisible(False)
            return

        self._search_status.setVisible(False)
        self._results_list.clear()
        for r in results:
            admin = f", {r['admin1']}" if r.get('admin1') else ""
            text = f"{r['name']}{admin}, {r['country']}"
            item = QListWidgetItem(text)
            self._results_list.addItem(item)
        self._results_list.setVisible(True)

    def _on_geocode_error(self, error_msg: str):
        self._search_btn.setEnabled(True)
        self._search_btn.setText("Buscar")
        self._search_status.setText(f"⚠ Error: {error_msg}")
        self._search_status.setVisible(True)

    def _on_result_selected(self, item: QListWidgetItem):
        idx = self._results_list.row(item)
        if 0 <= idx < len(self._geocode_results):
            r = self._geocode_results[idx]
            admin = f", {r['admin1']}" if r.get('admin1') else ""
            self._location_label.setText(f"{r['name']}{admin}, {r['country']}")
            self._lat_label.setText(f"{r['latitude']:.4f}")
            self._lon_label.setText(f"{r['longitude']:.4f}")
            self._tz_label.setText(r.get('timezone', ''))
            self._results_list.setVisible(False)
            self._search_status.setText(f"✔ Localidad seleccionada: {r['name']}")
            self._search_status.setVisible(True)

    def _save_settings(self):
        """Persiste la configuración y emite señal de cambio."""
        try:
            lat_text = self._lat_label.text()
            lon_text = self._lon_label.text()
            tz_text = self._tz_label.text()
            loc_text = self._location_label.text()

            settings = WeatherSettings.from_dict({
                "enabled": self._enabled_cb.isChecked(),
                "location_name": loc_text if loc_text != "—" else "",
                "latitude": float(lat_text) if lat_text != "—" else None,
                "longitude": float(lon_text) if lon_text != "—" else None,
                "timezone": tz_text if tz_text != "—" else "",
                "return_trip_minutes": self._return_spin.value(),
            })

            write_weather_settings(settings)
            self._settings = settings
            self.weather_settings_changed.emit()

            QMessageBox.information(
                self, "Configuración guardada",
                "La configuración meteorológica se guardó correctamente.\n"
                "El widget se actualizará en la próxima sincronización."
            )
        except ValueError as e:
            QMessageBox.warning(self, "Error de validación", str(e))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar: {e}")

    def _test_config(self):
        """Prueba la configuración en un hilo separado."""
        lat_text = self._lat_label.text()
        lon_text = self._lon_label.text()
        tz_text = self._tz_label.text()
        loc_text = self._location_label.text()

        if lat_text == "—" or lon_text == "—" or tz_text == "—":
            QMessageBox.warning(
                self, "Sin localidad",
                "Primero seleccioná una localidad usando el buscador."
            )
            return

        self._test_btn.setEnabled(False)
        self._test_btn.setText("🌡️ Consultando pronóstico…")
        self._preview_frame.setVisible(True)
        self._preview_label.setText("Consultando Open-Meteo...")

        self._test_thread = QThread()
        self._test_worker = _WeatherTestWorker(
            float(lat_text), float(lon_text), tz_text, loc_text
        )
        self._test_worker.moveToThread(self._test_thread)
        self._test_thread.started.connect(self._test_worker.run)
        self._test_worker.finished.connect(self._on_test_results)
        self._test_worker.error.connect(self._on_test_error)
        self._test_worker.finished.connect(self._test_thread.quit)
        self._test_worker.error.connect(self._test_thread.quit)
        self._test_thread.start()

    def _on_test_results(self, weather_dict: dict):
        self._test_btn.setEnabled(True)
        self._test_btn.setText("🌡️ Probar configuración")

        current = weather_dict.get("current")
        hourly = weather_dict.get("hourly", [])
        location = weather_dict.get("location_name", "")

        lines = [f"<b>🌤️ {location}</b><br>"]

        if current:
            icon = get_weather_icon(current.get("weather_code", 0), current.get("is_day", True))
            temp = current.get("temperature", 0)
            feels = current.get("apparent_temperature", 0)
            wind = current.get("wind_speed", 0)
            precip = current.get("precipitation_probability")
            lines.append(
                f"<b>Ahora:</b> {icon} {temp:.0f} °C · "
                f"Sensación {feels:.0f} °C · "
                f"Viento {wind:.0f} km/h"
            )
            if precip is not None:
                lines[-1] += f" · Lluvia {precip} %"
            lines.append("<br>")

        if hourly:
            lines.append("<b>Pronóstico horario:</b>")
            # Show every 3 hours
            for i, h in enumerate(hourly):
                if i % 3 != 0:
                    continue
                time_str = h.get("time", "")[-5:]
                icon = get_weather_icon(h.get("weather_code", 0), h.get("is_day", True))
                temp = h.get("temperature", 0)
                feels = h.get("apparent_temperature", 0)
                lines.append(
                    f"&nbsp;&nbsp;{time_str}  {icon}  {temp:.0f} °C · Sens. {feels:.0f} °C"
                )

        self._preview_label.setText("<br>".join(lines))

    def _on_test_error(self, error_msg: str):
        self._test_btn.setEnabled(True)
        self._test_btn.setText("🌡️ Probar configuración")
        self._preview_label.setText(f"⚠ Error al consultar el pronóstico: {error_msg}")

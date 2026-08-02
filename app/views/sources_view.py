"""
Vista de gestión de fuentes de datos.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.cache import read_sources, write_sources
from backend.models import DataSource
from app.styles.theme import DARK_PALETTE


class SourcesView(QWidget):
    """Vista para gestionar fuentes de datos."""

    source_changed = pyqtSignal()
    sync_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sources: list[DataSource] = []
        self._setup_ui()
        self.reload_sources()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Fuentes de Datos")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("+ Agregar Fuente")
        add_btn.clicked.connect(self._add_source)
        header.addWidget(add_btn)

        layout.addLayout(header)

        # Sources list
        self._list = QListWidget()
        self._list.setSpacing(4)
        self._list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list, stretch=1)

        # Detail panel
        self._detail_frame = QFrame()
        self._detail_frame.setStyleSheet(f"""
            QFrame {{
                background: {DARK_PALETTE['bg_card']};
                border: 1px solid {DARK_PALETTE['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        detail_layout = QVBoxLayout(self._detail_frame)

        self._detail_name = QLabel("Seleccioná una fuente")
        self._detail_name.setFont(self._detail_name.font())
        self._detail_name.setStyleSheet(f"font-weight: 600; font-size: 14px; background: transparent;")
        detail_layout.addWidget(self._detail_name)

        self._detail_type = QLabel("")
        self._detail_type.setStyleSheet(f"color: {DARK_PALETTE['text_secondary']}; background: transparent;")
        detail_layout.addWidget(self._detail_type)

        self._detail_url = QLabel("")
        self._detail_url.setWordWrap(True)
        self._detail_url.setStyleSheet(f"color: {DARK_PALETTE['text_muted']}; font-size: 11px; background: transparent;")
        detail_layout.addWidget(self._detail_url)

        self._detail_status = QLabel("")
        self._detail_status.setStyleSheet(f"color: {DARK_PALETTE['text_secondary']}; background: transparent;")
        detail_layout.addWidget(self._detail_status)

        # Action buttons
        btn_row = QHBoxLayout()
        self._toggle_btn = QPushButton("Deshabilitar")
        self._toggle_btn.setObjectName("secondaryButton")
        self._toggle_btn.clicked.connect(self._toggle_source)
        btn_row.addWidget(self._toggle_btn)

        self._sync_btn = QPushButton("🔄 Sincronizar Ahora")
        self._sync_btn.clicked.connect(self._sync_source)
        btn_row.addWidget(self._sync_btn)

        self._delete_btn = QPushButton("Eliminar")
        self._delete_btn.setObjectName("dangerButton")
        self._delete_btn.clicked.connect(self._delete_source)
        btn_row.addWidget(self._delete_btn)

        btn_row.addStretch()
        detail_layout.addLayout(btn_row)

        layout.addWidget(self._detail_frame)

    def reload_sources(self):
        """Recarga las fuentes desde disco."""
        self._sources = read_sources()
        self._list.clear()
        for s in self._sources:
            status = "✓" if s.enabled else "✗"
            icon = {"ical": "📅", "unrn_web": "🌐", "rest": "🔌", "manual": "✏️"}.get(s.type, "📎")
            item = QListWidgetItem(f"{icon}  {status} {s.name}  ({s.event_count} eventos)")
            if not s.enabled:
                item.setForeground(Qt.GlobalColor.gray)
            self._list.addItem(item)

    def _on_selection_changed(self, row: int):
        """Actualiza el panel de detalle."""
        if row < 0 or row >= len(self._sources):
            return
        s = self._sources[row]
        self._detail_name.setText(s.name)
        type_names = {"ical": "iCalendar Feed", "unrn_web": "Web Scraper", "rest": "API REST", "manual": "Manual"}
        self._detail_type.setText(f"Tipo: {type_names.get(s.type, s.type)}")
        url_display = s.url[:80] + "..." if len(s.url) > 80 else s.url
        self._detail_url.setText(f"URL: {url_display}" if s.url else "Sin URL")
        sync_text = f"Última sync: {s.last_sync or 'nunca'}"
        if s.sync_error:
            sync_text += f"\n⚠ Error: {s.sync_error}"
        self._detail_status.setText(sync_text)
        self._toggle_btn.setText("Deshabilitar" if s.enabled else "Habilitar")

    def _toggle_source(self):
        row = self._list.currentRow()
        if row < 0:
            return
        self._sources[row].enabled = not self._sources[row].enabled
        write_sources(self._sources)
        self.reload_sources()
        self._list.setCurrentRow(row)
        self.source_changed.emit()

    def _delete_source(self):
        row = self._list.currentRow()
        if row < 0:
            return
        s = self._sources[row]
        
        if s.id == "manual":
            QMessageBox.warning(self, "Acción no permitida", "La fuente de Eventos Manuales no puede eliminarse, solo deshabilitarse.")
            return

        reply = QMessageBox.question(
            self, "Eliminar fuente",
            f"¿Eliminar la fuente '{s.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._sources.pop(row)
            write_sources(self._sources)
            self.reload_sources()
            self.source_changed.emit()

    def _add_source(self):
        from app.dialogs.source_dialog import SourceDialog
        dialog = SourceDialog(self)
        if dialog.exec():
            data = dialog.get_source_data()
            new_source = DataSource(**data)
            self._sources.append(new_source)
            write_sources(self._sources)
            self.reload_sources()
            self.source_changed.emit()

    def _sync_source(self):
        """Lanza la sincronización del backend."""
        row = self._list.currentRow()
        if row < 0:
            return
        s = self._sources[row]
        self.sync_requested.emit(s.id)
        QMessageBox.information(
            self, "Sincronización",
            f"Sincronización de '{s.name}' encolada.",
        )

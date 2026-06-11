"""
Diálogo para crear/editar eventos manuales.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QDateTimeEdit, QComboBox, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, QDateTime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.models import AcademicEvent
from backend.cache import read_manual_events, write_manual_events
from backend.config import get_urgency
from app.styles.theme import DARK_PALETTE, get_urgency_style

from datetime import datetime, date


class EventDialog(QDialog):
    """Diálogo para crear o editar un evento manual."""

    def __init__(self, event_data: dict = None, parent=None):
        super().__init__(parent)
        self._event_data = event_data
        self._is_editing = event_data is not None
        self.setWindowTitle("Editar Evento" if self._is_editing else "Nuevo Evento")
        self.setMinimumSize(450, 400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        layout.addWidget(QLabel("Título:"))
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Ej: Entrega TP2 — Algoritmos")
        if self._event_data:
            self._title_edit.setText(self._event_data.get("title", ""))
        layout.addWidget(self._title_edit)

        # Description
        layout.addWidget(QLabel("Descripción (opcional):"))
        self._desc_edit = QTextEdit()
        self._desc_edit.setMaximumHeight(80)
        self._desc_edit.setPlaceholderText("Detalles adicionales...")
        if self._event_data:
            self._desc_edit.setPlainText(self._event_data.get("description", ""))
        layout.addWidget(self._desc_edit)

        # Date/Time
        layout.addWidget(QLabel("Fecha y hora de vencimiento:"))
        self._datetime_edit = QDateTimeEdit()
        self._datetime_edit.setCalendarPopup(True)
        self._datetime_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        if self._event_data:
            try:
                dt = datetime.fromisoformat(self._event_data.get("due_date", ""))
                self._datetime_edit.setDateTime(QDateTime(
                    dt.year, dt.month, dt.day, dt.hour, dt.minute
                ))
            except (ValueError, TypeError):
                self._datetime_edit.setDateTime(QDateTime.currentDateTime())
        else:
            self._datetime_edit.setDateTime(QDateTime.currentDateTime().addDays(7))
        self._datetime_edit.dateTimeChanged.connect(self._update_preview)
        layout.addWidget(self._datetime_edit)

        # Category
        layout.addWidget(QLabel("Categoría:"))
        self._category_combo = QComboBox()
        self._category_combo.addItems([
            "📝 Entrega",
            "📋 Examen",
            "✏️ Inscripción",
            "📌 Otro",
        ])
        if self._event_data:
            cat_map = {"entrega": 0, "examen": 1, "inscripcion": 2, "otro": 3}
            idx = cat_map.get(self._event_data.get("category", "otro"), 3)
            self._category_combo.setCurrentIndex(idx)
        layout.addWidget(self._category_combo)

        # Urgency preview
        self._preview_frame = QFrame()
        self._preview_frame.setStyleSheet(f"""
            background: {DARK_PALETTE['bg_card']};
            border-radius: 8px;
            padding: 12px;
        """)
        preview_layout = QHBoxLayout(self._preview_frame)

        self._preview_dot = QLabel("●")
        self._preview_dot.setStyleSheet("font-size: 20px; background: transparent;")
        preview_layout.addWidget(self._preview_dot)

        self._preview_text = QLabel("")
        self._preview_text.setStyleSheet(f"color: {DARK_PALETTE['text_primary']}; background: transparent;")
        preview_layout.addWidget(self._preview_text, stretch=1)

        layout.addWidget(self._preview_frame)
        self._update_preview()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾 Guardar Evento")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _update_preview(self):
        """Actualiza la preview de urgencia en tiempo real."""
        qdt = self._datetime_edit.dateTime()
        target = date(qdt.date().year(), qdt.date().month(), qdt.date().day())
        delta = (target - date.today()).days
        urgency = get_urgency(delta)
        color = get_urgency_style(urgency)

        self._preview_dot.setStyleSheet(f"color: {color}; font-size: 20px; background: transparent;")

        if delta < 0:
            text = f"⚠ Vencido hace {abs(delta)} días"
        elif delta == 0:
            text = "🔴 ¡Es HOY!"
        elif delta == 1:
            text = "🟠 Falta 1 día"
        elif delta <= 2:
            text = f"🟠 Faltan {delta} días"
        elif delta <= 7:
            text = f"🟡 Faltan {delta} días"
        else:
            text = f"🟢 Faltan {delta} días"

        self._preview_text.setText(text)

    def _save(self):
        """Guarda el evento manual."""
        title = self._title_edit.text().strip()
        if not title:
            self._title_edit.setFocus()
            self._title_edit.setStyleSheet(f"border: 2px solid {DARK_PALETTE['danger']};")
            return

        qdt = self._datetime_edit.dateTime()
        from dateutil.tz import gettz
        dt = datetime(
            qdt.date().year(), qdt.date().month(), qdt.date().day(),
            qdt.time().hour(), qdt.time().minute(),
            tzinfo=gettz("America/Argentina/Buenos_Aires"),
        )

        cat_map = {0: "entrega", 1: "examen", 2: "inscripcion", 3: "otro"}
        category = cat_map.get(self._category_combo.currentIndex(), "otro")

        event = AcademicEvent(
            title=title,
            description=self._desc_edit.toPlainText().strip(),
            due_date=dt.isoformat(),
            source_id="manual",
            source_name="Eventos Manuales",
            category=category,
            is_manual=True,
        )
        event.id = event.generate_stable_id()

        # Read existing manual events and add/update
        manual_events = read_manual_events()

        if self._is_editing and self._event_data:
            # Update existing
            old_id = self._event_data.get("id", "")
            manual_events = [e for e in manual_events if e.id != old_id]

        manual_events.append(event)
        write_manual_events(manual_events)

        self.accept()

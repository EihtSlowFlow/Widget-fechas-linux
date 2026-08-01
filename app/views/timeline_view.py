"""
Vista de línea de tiempo — muestra eventos en tarjetas agrupadas por urgencia.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QLineEdit, QComboBox, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.styles.theme import DARK_PALETTE
from app.widgets.event_card import EventCard


class TimelineView(QWidget):
    """Vista principal de timeline con tarjetas de eventos."""

    event_clicked = pyqtSignal(dict)  # Emitida al hacer clic en un evento
    event_edit_requested = pyqtSignal(dict)  # Emitida al solicitar edición de evento manual

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ─── Filter bar ──────────────────────────────────
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Buscar eventos...")
        self._search.textChanged.connect(self._apply_filters)
        filter_bar.addWidget(self._search, stretch=1)

        self._category_filter = QComboBox()
        self._category_filter.addItems([
            "Todas las categorías",
            "📝 Entregas",
            "📋 Exámenes",
            "✏️ Inscripciones",
            "📌 Otros",
        ])
        self._category_filter.currentIndexChanged.connect(self._apply_filters)
        filter_bar.addWidget(self._category_filter)

        self._source_filter = QComboBox()
        self._source_filter.addItem("Todas las fuentes")
        self._source_filter.currentIndexChanged.connect(self._apply_filters)
        filter_bar.addWidget(self._source_filter)

        layout.addLayout(filter_bar)

        # ─── Scroll area for event cards ──────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 8, 0)
        self._cards_layout.setSpacing(4)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_widget)
        layout.addWidget(scroll)

    def set_events(self, events: list[dict]):
        """Actualiza la lista de eventos."""
        self._events = events

        # Update source filter
        sources = sorted(set(e.get("source_name", "") for e in events))
        current = self._source_filter.currentText()
        self._source_filter.blockSignals(True)
        self._source_filter.clear()
        self._source_filter.addItem("Todas las fuentes")
        self._source_filter.addItems(sources)
        if current in sources:
            self._source_filter.setCurrentText(current)
        self._source_filter.blockSignals(False)

        self._apply_filters()

    def _apply_filters(self):
        """Aplica filtros de búsqueda, categoría y fuente."""
        search_text = self._search.text().lower()
        cat_idx = self._category_filter.currentIndex()
        source_text = self._source_filter.currentText()

        cat_map = {1: "entrega", 2: "examen", 3: "inscripcion", 4: "otro"}
        target_cat = cat_map.get(cat_idx)

        filtered = []
        for e in self._events:
            # Search filter
            if search_text:
                if (search_text not in e.get("title", "").lower() and
                    search_text not in e.get("source_name", "").lower()):
                    continue
            # Category filter
            if target_cat and e.get("category") != target_cat:
                continue
            # Source filter
            if source_text != "Todas las fuentes" and e.get("source_name") != source_text:
                continue
            filtered.append(e)

        self._render_cards(filtered)

    def _render_cards(self, events: list[dict]):
        """Renderiza las tarjetas de eventos, agrupadas por urgencia."""
        # Clear existing
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not events:
            empty = QLabel("📅 No hay eventos que coincidan con los filtros")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {DARK_PALETTE['text_muted']}; padding: 40px; background: transparent;")
            self._cards_layout.insertWidget(0, empty)
            return

        # Group by urgency
        groups = {"red": [], "orange": [], "yellow": [], "green": []}
        for e in events:
            urg = e.get("urgency", "green")
            groups.get(urg, groups["green"]).append(e)

        group_labels = {
            "red":    "🔴 Urgente — Hoy o vencido",
            "orange": "🟠 Próximos días — 1 a 2 días",
            "yellow": "🟡 Esta semana — 3 a 7 días",
            "green":  "🟢 Más adelante — +7 días",
        }

        insert_idx = 0
        for urg_key in ["red", "orange", "yellow", "green"]:
            group = groups[urg_key]
            if not group:
                continue

            # Section header
            header = QLabel(group_labels[urg_key])
            header.setObjectName("sectionTitle")
            header.setStyleSheet(f"""
                font-size: 13px;
                font-weight: 600;
                color: {DARK_PALETTE['text_secondary']};
                padding: 8px 0px 4px 4px;
                background: transparent;
            """)
            self._cards_layout.insertWidget(insert_idx, header)
            insert_idx += 1

            for e in group:
                card = EventCard(e)
                # Conectar señal de completado → refrescar tarjetas
                card.completion_toggled.connect(self._on_completion_toggled)
                # Conectar señal de edición
                card.edit_requested.connect(self.event_edit_requested.emit)
                self._cards_layout.insertWidget(insert_idx, card)
                insert_idx += 1

    def _on_completion_toggled(self, event_id: str, is_completed: bool):
        """Refresca la vista cuando se marca/desmarca un evento."""
        # Actualizar el estado en la lista interna
        for e in self._events:
            if e.get("id") == event_id:
                e["is_completed"] = is_completed
                break
        # Re-renderizar para reflejar el cambio visual
        self._apply_filters()

"""
Vista de calendario — muestra un calendario mensual con eventos resaltados.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget, QLabel,
    QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QTextCharFormat, QColor, QFont

from app.styles.theme import DARK_PALETTE, get_urgency_style
from app.widgets.event_card import EventCard
from datetime import datetime
from PyQt6.QtCore import pyqtSignal

class CalendarView(QWidget):
    """Vista de calendario con eventos resaltados por urgencia."""

    event_edit_requested = pyqtSignal(dict)  # Emitida al solicitar edición de evento manual

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events = []
        self._events_by_date: dict[str, list[dict]] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ─── Calendar widget ─────────────────────────────
        cal_col = QVBoxLayout()

        self._calendar = QCalendarWidget()
        self._calendar.setGridVisible(True)
        self._calendar.setMinimumHeight(320)
        self._calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self._calendar.clicked.connect(self._on_date_clicked)
        cal_col.addWidget(self._calendar)

        # Legend
        legend = QHBoxLayout()
        legend.setSpacing(12)
        for urgency, label_text in [
            ("red", "Urgente"), ("orange", "Próximo"),
            ("yellow", "Semana"), ("green", "Normal"),
        ]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {get_urgency_style(urgency)}; font-size: 14px; background: transparent;")
            legend.addWidget(dot)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {DARK_PALETTE['text_muted']}; font-size: 11px; background: transparent;")
            legend.addWidget(lbl)
        legend.addStretch()
        cal_col.addLayout(legend)

        layout.addLayout(cal_col, stretch=1)

        # ─── Day detail panel ─────────────────────────────
        detail_col = QVBoxLayout()
        detail_col.setSpacing(8)

        self._day_label = QLabel("Seleccioná un día")
        self._day_label.setObjectName("sectionTitle")
        self._day_label.setStyleSheet(f"""
            font-size: 15px; font-weight: 600;
            color: {DARK_PALETTE['accent']};
            padding-bottom: 4px;
            background: transparent;
        """)
        detail_col.addWidget(self._day_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")
        scroll.setMinimumWidth(300)

        self._detail_widget = QWidget()
        self._detail_layout = QVBoxLayout(self._detail_widget)
        self._detail_layout.setContentsMargins(0, 0, 0, 0)
        self._detail_layout.setSpacing(4)
        self._detail_layout.addStretch()

        scroll.setWidget(self._detail_widget)
        detail_col.addWidget(scroll)

        layout.addLayout(detail_col, stretch=1)

    def set_events(self, events: list[dict]):
        """Actualiza los eventos y resalta los días correspondientes."""
        self._events = events
        self._events_by_date.clear()

        # Reset all dates
        default_fmt = QTextCharFormat()
        self._calendar.setDateTextFormat(QDate(), default_fmt)

        for e in events:
            try:
                dt = datetime.fromisoformat(e.get("due_date", ""))
                date_key = dt.strftime("%Y-%m-%d")
                qdate = QDate(dt.year, dt.month, dt.day)

                if date_key not in self._events_by_date:
                    self._events_by_date[date_key] = []
                self._events_by_date[date_key].append(e)

                # Highlight the calendar day with urgency color
                urgency = e.get("urgency", "green")
                color = QColor(get_urgency_style(urgency))
                fmt = QTextCharFormat()
                fmt.setBackground(QColor(color.red(), color.green(), color.blue(), 80))
                fmt.setForeground(QColor("white"))
                fmt.setFontWeight(QFont.Weight.Bold)
                self._calendar.setDateTextFormat(qdate, fmt)

            except (ValueError, TypeError):
                continue

        # Show today's events by default
        self._on_date_clicked(self._calendar.selectedDate())

    def _on_date_clicked(self, qdate: QDate):
        """Muestra los eventos del día seleccionado."""
        date_key = qdate.toString("yyyy-MM-dd")
        day_events = self._events_by_date.get(date_key, [])

        self._day_label.setText(
            qdate.toString("dddd, d 'de' MMMM yyyy")
        )

        # Clear detail panel
        while self._detail_layout.count() > 1:
            item = self._detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not day_events:
            empty = QLabel("Sin eventos este día")
            empty.setStyleSheet(f"color: {DARK_PALETTE['text_muted']}; padding: 20px; background: transparent;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._detail_layout.insertWidget(0, empty)
        else:
            for i, e in enumerate(day_events):
                card = EventCard(e)
                card.edit_requested.connect(self.event_edit_requested.emit)
                self._detail_layout.insertWidget(i, card)

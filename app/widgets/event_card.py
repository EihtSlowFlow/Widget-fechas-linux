"""
Widget de tarjeta de evento para la aplicación principal.
Muestra un evento con semáforo, días restantes, badge 'Nuevo' (dismiss on hover),
rango de fechas ("Inicia en X días"), y toggle de completado (✓ Entregado).
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from app.styles.theme import get_urgency_style, DARK_PALETTE


class UrgencyBadge(QLabel):
    """Badge circular de urgencia con color del semáforo."""

    def __init__(self, urgency: str = "green", parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self.set_urgency(urgency)

    def set_urgency(self, urgency: str):
        color = get_urgency_style(urgency)
        self.setStyleSheet(f"""
            background-color: {color};
            border-radius: 6px;
            border: 2px solid rgba(255, 255, 255, 0.2);
        """)


class EventCard(QFrame):
    """Tarjeta visual de un evento académico."""

    # Señal emitida cuando se marca/desmarca como completado
    completion_toggled = pyqtSignal(str, bool)  # (event_id, is_completed)
    # Señal emitida cuando el badge "Nuevo" debe desaparecer
    new_dismissed = pyqtSignal(str)  # event_id

    def __init__(self, event_data: dict, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self._new_badge = None
        self._hover_timer = None
        self._setup_ui()

    def _format_date_range(self) -> str:
        """
        Genera texto descriptivo para el rango de fechas.
        Si hay start_date y due_date distintas:
          - "Inicia en X días, finaliza en Y días"
          - "En curso — finaliza en Y días"
          - "Del dd/mm al dd/mm"
        Si no hay rango, muestra solo la fecha deadline.
        """
        e = self.event_data
        start_date = e.get("start_date", "")
        due_date = e.get("due_date", "")
        days_start = e.get("days_until_start")
        days_end = e.get("days_remaining", 0)

        try:
            from datetime import datetime
            due_dt = datetime.fromisoformat(due_date)
            due_str = due_dt.strftime("%d/%m")
        except (ValueError, TypeError):
            due_str = ""

        if start_date:
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_date)
                start_str = start_dt.strftime("%d/%m")
            except (ValueError, TypeError):
                start_str = ""
                start_date = ""

        if start_date and due_str and days_start is not None:
            if days_start > 1:
                return f"Inicia en {days_start} días ({start_str}) · Finaliza {due_str}"
            elif days_start == 1:
                return f"Inicia mañana ({start_str}) · Finaliza {due_str}"
            elif days_start == 0:
                return f"Inicia hoy ({start_str}) · Finaliza {due_str}"
            else:
                # Ya empezó
                if days_end > 1:
                    return f"En curso · Finaliza en {days_end} días ({due_str})"
                elif days_end == 1:
                    return f"En curso · Finaliza mañana ({due_str})"
                elif days_end == 0:
                    return f"En curso · Finaliza hoy ({due_str})"
                else:
                    return f"Finalizó ({due_str})"
        else:
            # Fecha única
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(due_date)
                return dt.strftime("%d %b %Y • %H:%M")
            except (ValueError, TypeError):
                return due_date

    def _setup_ui(self):
        e = self.event_data
        urgency = e.get("urgency", "green")
        urgency_color = get_urgency_style(urgency)
        days = e.get("days_remaining", 0)
        is_new = e.get("is_new", False)
        is_completed = e.get("is_completed", False)

        self.setObjectName("eventCard")

        # Estilo base — con opacidad reducida si está completado
        opacity = "0.55" if is_completed else "1.0"
        border_color = "#666" if is_completed else urgency_color
        self.setStyleSheet(f"""
            QFrame#eventCard {{
                background-color: {DARK_PALETTE['bg_card']};
                border-left: 4px solid {border_color};
                border-radius: 8px;
                padding: 0px;
                margin: 2px 0px;
                opacity: {opacity};
            }}
            QFrame#eventCard:hover {{
                background-color: {DARK_PALETTE['bg_hover']};
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # ─── Days column ──────────────────────────────────
        days_col = QVBoxLayout()
        days_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        days_col.setSpacing(0)

        if is_completed:
            days_text = "✓"
            sub_text = "hecho"
        elif days == 0:
            days_text = "HOY"
            sub_text = "⚠"
        elif days < 0:
            days_text = str(abs(days))
            sub_text = "vencido"
        elif days == 1:
            days_text = "1"
            sub_text = "día"
        else:
            days_text = str(days)
            sub_text = "días"

        text_color = "#666" if is_completed else urgency_color

        days_label = QLabel(days_text)
        days_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        days_label.setFont(QFont("Inter", 22, QFont.Weight.Bold))
        days_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        days_label.setFixedWidth(60)
        days_col.addWidget(days_label)

        sub_label = QLabel(sub_text)
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_label.setStyleSheet(f"color: {DARK_PALETTE['text_muted']}; font-size: 11px; background: transparent;")
        days_col.addWidget(sub_label)

        layout.addLayout(days_col)

        # ─── Separator ────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {DARK_PALETTE['border']}; background: transparent;")
        sep.setFixedWidth(1)
        layout.addWidget(sep)

        # ─── Info column ──────────────────────────────────
        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        title_text = e.get("title", "Sin título")
        title_label = QLabel(title_text)
        title_label.setFont(QFont("Inter", 13, QFont.Weight.Bold))
        title_label.setWordWrap(True)
        title_style = f"color: {DARK_PALETTE['text_muted']}; background: transparent; text-decoration: line-through;" if is_completed else f"color: {DARK_PALETTE['text_primary']}; background: transparent;"
        title_label.setStyleSheet(title_style)
        info_col.addWidget(title_label)

        source_label = QLabel(e.get("source_name", ""))
        source_label.setStyleSheet(f"color: {DARK_PALETTE['text_secondary']}; font-size: 11px; background: transparent;")
        info_col.addWidget(source_label)

        # ─── Date range display ──────────────────────────
        date_info = self._format_date_range()
        date_label = QLabel(date_info)
        date_label.setStyleSheet(f"color: {DARK_PALETTE['text_muted']}; font-size: 11px; background: transparent;")
        date_label.setWordWrap(True)
        info_col.addWidget(date_label)

        layout.addLayout(info_col, stretch=1)

        # ─── Right side: badges and actions ───────────────
        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_col.setSpacing(6)

        # Badge "NUEVO" (will be hidden on hover)
        if is_new:
            self._new_badge = QLabel("  NUEVO  ")
            self._new_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._new_badge.setStyleSheet(f"""
                background-color: {DARK_PALETTE['nuevo_badge']};
                color: white;
                border-radius: 10px;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 8px;
                letter-spacing: 1px;
            """)
            self._new_badge.setFixedHeight(22)
            right_col.addWidget(self._new_badge)

        # Botón completar/desmarcar — texto según categoría
        cat = e.get("category", "otro")
        completion_labels = {
            "entrega":     ("✓ Entregado", "Marcar entregado"),
            "examen":      ("✓ Rendido", "Marcar rendido"),
            "inscripcion": ("✓ Inscripto", "Marcar inscripto"),
            "otro":        ("✓ Listo", "Marcar listo"),
            "receso":      ("✓ Listo", "Marcar listo"),
        }
        done_text, pending_text = completion_labels.get(cat, ("✓ Listo", "Marcar listo"))
        btn_text = done_text if is_completed else pending_text

        self._complete_btn = QPushButton(btn_text)
        self._complete_btn.setFixedHeight(24)
        btn_bg = "#4CAF50" if is_completed else DARK_PALETTE['bg_selected']
        btn_fg = "white" if is_completed else DARK_PALETTE['text_secondary']
        self._complete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_fg};
                border-radius: 10px;
                font-size: 10px;
                padding: 3px 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {'#388E3C' if is_completed else '#555'};
            }}
        """)
        self._complete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._complete_btn.clicked.connect(self._on_toggle_completed)
        right_col.addWidget(self._complete_btn)

        # Category chip
        cat = e.get("category", "otro")
        cat_display = {
            "entrega": "📝 Entrega",
            "examen": "📋 Examen",
            "inscripcion": "✏️ Inscripción",
            "receso": "🏖 Receso",
            "otro": "📌 Otro",
        }.get(cat, f"📌 {cat}")

        cat_label = QLabel(cat_display)
        cat_label.setStyleSheet(f"""
            background-color: {DARK_PALETTE['bg_selected']};
            color: {DARK_PALETTE['text_secondary']};
            border-radius: 10px;
            font-size: 10px;
            padding: 3px 8px;
        """)
        cat_label.setFixedHeight(22)
        right_col.addWidget(cat_label)

        layout.addLayout(right_col)

    def enterEvent(self, event):
        """Al pasar el mouse: desmarcar badge 'Nuevo' tras breve delay."""
        super().enterEvent(event)
        if self._new_badge is not None and self.event_data.get("is_new", False):
            # Delay de 600ms para evitar falsos positivos
            self._hover_timer = QTimer()
            self._hover_timer.setSingleShot(True)
            self._hover_timer.timeout.connect(self._dismiss_new_badge)
            self._hover_timer.start(600)

    def leaveEvent(self, event):
        """Al salir: cancelar timer si no se completó."""
        super().leaveEvent(event)
        if self._hover_timer is not None:
            self._hover_timer.stop()
            self._hover_timer = None

    def _dismiss_new_badge(self):
        """Oculta el badge y persiste el estado."""
        if self._new_badge is not None:
            self._new_badge.hide()
            self._new_badge = None
            event_id = self.event_data.get("id", "")
            if event_id:
                from backend.cache import mark_event_seen
                mark_event_seen(event_id)
                self.event_data["is_new"] = False
                self.new_dismissed.emit(event_id)

    def _on_toggle_completed(self):
        """Toggle de completado y emite señal para refrescar."""
        event_id = self.event_data.get("id", "")
        if event_id:
            from backend.cache import toggle_completed
            is_done = toggle_completed(event_id)
            self.event_data["is_completed"] = is_done
            self.completion_toggled.emit(event_id, is_done)

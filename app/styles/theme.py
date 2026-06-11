"""
Sistema de diseño para la aplicación de Fechas Académicas.
Paleta compatible con KDE Breeze, con soporte oscuro/claro.
"""

from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication


# ─── Colores del semáforo ─────────────────────────────────────
URGENCY_COLORS = {
    "red":    "#F44336",
    "orange": "#FF9800",
    "yellow": "#FFC107",
    "green":  "#4CAF50",
}

# ─── Paleta oscura estilo Breeze ──────────────────────────────
DARK_PALETTE = {
    "bg_primary":    "#1e1e2e",
    "bg_secondary":  "#252536",
    "bg_card":       "#2a2a3c",
    "bg_hover":      "#353548",
    "bg_selected":   "#3d3d52",
    "text_primary":  "#e0e0e8",
    "text_secondary":"#a0a0b0",
    "text_muted":    "#606070",
    "accent":        "#7c9df5",
    "accent_hover":  "#94b0ff",
    "border":        "#3a3a4a",
    "border_light":  "#454558",
    "nuevo_badge":   "#2196F3",
    "success":       "#4CAF50",
    "warning":       "#FFC107",
    "danger":        "#F44336",
    "shadow":        "rgba(0, 0, 0, 0.3)",
}


def get_app_stylesheet() -> str:
    """Retorna el QSS completo para la aplicación."""
    c = DARK_PALETTE
    return f"""
    /* ─── Global ───────────────────────────────────────── */
    QMainWindow, QWidget {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
        font-family: 'Inter', 'Noto Sans', 'Segoe UI', sans-serif;
        font-size: 13px;
    }}

    /* ─── Tab Bar ──────────────────────────────────────── */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        background: {c['bg_secondary']};
        margin-top: -1px;
    }}
    QTabBar::tab {{
        background: {c['bg_card']};
        color: {c['text_secondary']};
        padding: 10px 20px;
        margin-right: 2px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        border: 1px solid {c['border']};
        border-bottom: none;
        font-weight: 500;
    }}
    QTabBar::tab:selected {{
        background: {c['bg_secondary']};
        color: {c['accent']};
        font-weight: 600;
    }}
    QTabBar::tab:hover {{
        background: {c['bg_hover']};
        color: {c['text_primary']};
    }}

    /* ─── Push Buttons ─────────────────────────────────── */
    QPushButton {{
        background-color: {c['accent']};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 18px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: {c['accent_hover']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_selected']};
    }}
    QPushButton:disabled {{
        background-color: {c['bg_card']};
        color: {c['text_muted']};
    }}
    QPushButton#dangerButton {{
        background-color: {c['danger']};
    }}
    QPushButton#dangerButton:hover {{
        background-color: #E53935;
    }}
    QPushButton#secondaryButton {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
    }}
    QPushButton#secondaryButton:hover {{
        background-color: {c['bg_hover']};
    }}

    /* ─── Scroll Area ──────────────────────────────────── */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: {c['bg_primary']};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border_light']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['text_muted']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* ─── Line Edit / Text Edit ────────────────────────── */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 12px;
        selection-background-color: {c['accent']};
    }}
    QLineEdit:focus, QTextEdit:focus {{
        border-color: {c['accent']};
    }}

    /* ─── ComboBox ─────────────────────────────────────── */
    QComboBox {{
        background: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 12px;
    }}
    QComboBox::drop-down {{
        border: none;
        padding-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent']};
    }}

    /* ─── Calendar Widget ──────────────────────────────── */
    QCalendarWidget {{
        background: {c['bg_secondary']};
    }}
    QCalendarWidget QToolButton {{
        color: {c['text_primary']};
        background: {c['bg_card']};
        border-radius: 4px;
        padding: 4px 8px;
        margin: 2px;
    }}
    QCalendarWidget QToolButton:hover {{
        background: {c['bg_hover']};
    }}

    /* ─── Labels ───────────────────────────────────────── */
    QLabel {{
        color: {c['text_primary']};
    }}
    QLabel#sectionTitle {{
        font-size: 16px;
        font-weight: 700;
        color: {c['text_primary']};
    }}
    QLabel#subtitle {{
        font-size: 12px;
        color: {c['text_secondary']};
    }}
    QLabel#mutedText {{
        color: {c['text_muted']};
        font-size: 11px;
    }}

    /* ─── Status Bar ───────────────────────────────────── */
    QStatusBar {{
        background: {c['bg_card']};
        color: {c['text_secondary']};
        border-top: 1px solid {c['border']};
        padding: 4px;
        font-size: 12px;
    }}

    /* ─── Group Box ────────────────────────────────────── */
    QGroupBox {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding: 16px 12px 12px 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        padding: 0 8px;
        color: {c['accent']};
    }}

    /* ─── List Widget ──────────────────────────────────── */
    QListWidget {{
        background: {c['bg_secondary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px;
        border-bottom: 1px solid {c['border']};
    }}
    QListWidget::item:selected {{
        background: {c['bg_selected']};
        color: {c['text_primary']};
    }}
    QListWidget::item:hover {{
        background: {c['bg_hover']};
    }}

    /* ─── Dialog ───────────────────────────────────────── */
    QDialog {{
        background: {c['bg_primary']};
    }}

    /* ─── Date/Time Edit ───────────────────────────────── */
    QDateTimeEdit, QDateEdit {{
        background: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 12px;
    }}
    """


def get_urgency_style(urgency: str) -> str:
    """Returns a CSS color string for the urgency level."""
    return URGENCY_COLORS.get(urgency, URGENCY_COLORS["green"])

"""
Diálogo para agregar una nueva fuente de datos.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton,
)
from app.styles.theme import DARK_PALETTE


class SourceDialog(QDialog):
    """Diálogo para agregar una nueva fuente."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar Fuente")
        self.setMinimumWidth(450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Nombre:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Ej: Moodle — Matemática Discreta")
        layout.addWidget(self._name_edit)

        layout.addWidget(QLabel("Tipo:"))
        self._type_combo = QComboBox()
        self._type_combo.addItems([
            "📅 iCalendar Feed (Moodle, Google, etc.)",
            "🔌 API REST",
        ])
        layout.addWidget(self._type_combo)

        layout.addWidget(QLabel("URL:"))
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://...")
        layout.addWidget(self._url_edit)

        info = QLabel(
            "💡 Para Moodle: andá a Calendario → Importar/Exportar → "
            "\"Obtener URL del calendario\" y pegá la URL acá."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {DARK_PALETTE['text_muted']}; font-size: 11px;")
        layout.addWidget(info)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("✓ Agregar")
        save_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _validate_and_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        if not self._url_edit.text().strip():
            self._url_edit.setFocus()
            return
        self.accept()

    def get_source_data(self) -> dict:
        type_map = {0: "ical", 1: "rest"}
        return {
            "name": self._name_edit.text().strip(),
            "type": type_map.get(self._type_combo.currentIndex(), "ical"),
            "url": self._url_edit.text().strip(),
            "enabled": True,
        }

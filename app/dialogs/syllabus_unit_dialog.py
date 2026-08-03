"""
Diálogo para agregar o editar una unidad del programa.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt


class SyllabusUnitDialog(QDialog):
    """Diálogo para configurar una unidad del programa."""

    def __init__(self, parent=None, unit_data=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Unidad")
        self.setMinimumWidth(450)
        self.setMinimumHeight(350)
        self._unit_data = unit_data
        self._setup_ui()
        if self._unit_data:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Unit name
        layout.addWidget(QLabel("Nombre de la unidad:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Ej: 1. Nociones avanzadas de diseño de DB")
        layout.addWidget(self._name_edit)

        # Weeks
        layout.addWidget(QLabel("Semanas (separadas por comas):"))
        self._weeks_edit = QLineEdit()
        self._weeks_edit.setPlaceholderText("Ej: 1, 2, 3, 4")
        layout.addWidget(self._weeks_edit)

        # Contents
        layout.addWidget(QLabel("Contenidos:"))
        self._contents_table = QTableWidget(0, 1)
        self._contents_table.setHorizontalHeaderLabels(["Contenido"])
        self._contents_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._contents_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self._contents_table)

        # Content buttons
        content_btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Agregar Contenido")
        add_btn.clicked.connect(self._add_content)
        content_btn_layout.addWidget(add_btn)

        remove_btn = QPushButton("- Eliminar Seleccionado")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(self._remove_content)
        content_btn_layout.addWidget(remove_btn)

        content_btn_layout.addStretch()
        layout.addLayout(content_btn_layout)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("✓ Guardar")
        save_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_data(self):
        self._name_edit.setText(self._unit_data.get("name", ""))
        weeks = self._unit_data.get("weeks", [])
        if weeks:
            self._weeks_edit.setText(", ".join(str(w) for w in weeks))
        contents = self._unit_data.get("contents", [])
        self._contents_table.setRowCount(len(contents))
        for row, content in enumerate(contents):
            self._contents_table.setItem(row, 0, QTableWidgetItem(content))

    def _add_content(self):
        row = self._contents_table.rowCount()
        self._contents_table.insertRow(row)
        self._contents_table.setItem(row, 0, QTableWidgetItem("Nuevo contenido"))

    def _remove_content(self):
        row = self._contents_table.currentRow()
        if row >= 0:
            self._contents_table.removeRow(row)

    def _validate_and_accept(self):
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "El nombre de la unidad no puede estar vacío.")
            self._name_edit.setFocus()
            return

        # Parse and validate weeks
        weeks_text = self._weeks_edit.text().strip()
        weeks = []
        if weeks_text:
            for part in weeks_text.split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    val = int(part)
                    if val < 1:
                        QMessageBox.warning(self, "Error", f"Semana inválida: {part}. Las semanas deben ser números enteros >= 1.")
                        self._weeks_edit.setFocus()
                        return
                    weeks.append(val)
                except ValueError:
                    QMessageBox.warning(self, "Error", f"Valor inválido: '{part}'. Las semanas deben ser números enteros.")
                    self._weeks_edit.setFocus()
                    return

        # UI requires at least one valid week
        if not weeks:
            QMessageBox.warning(self, "Semanas requeridas", "La unidad debe tener al menos una semana válida.")
            self._weeks_edit.setFocus()
            return

        self.accept()

    def get_unit_data(self) -> dict:
        name = self._name_edit.text().strip()

        # Parse weeks
        weeks = []
        for part in self._weeks_edit.text().strip().split(","):
            part = part.strip()
            if not part:
                continue
            try:
                val = int(part)
                if val >= 1:
                    weeks.append(val)
            except ValueError:
                continue
        weeks = sorted(set(weeks))

        # Collect contents, deduplicate preserving order
        contents = []
        seen = set()
        for row in range(self._contents_table.rowCount()):
            item = self._contents_table.item(row, 0)
            if item:
                text = item.text().strip()
                if text and text not in seen:
                    seen.add(text)
                    contents.append(text)

        return {
            "name": name,
            "weeks": weeks,
            "contents": contents
        }

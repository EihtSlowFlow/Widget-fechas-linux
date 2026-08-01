"""
Diálogo para agregar o editar una materia y su temario.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from app.styles.theme import DARK_PALETTE

class SubjectDialog(QDialog):
    """Diálogo para configurar una materia."""

    def __init__(self, parent=None, subject_data=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Materia")
        self.setMinimumWidth(550)
        self.setMinimumHeight(450)
        self._subject_data = subject_data
        self._setup_ui()
        if self._subject_data:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Basic Info
        form_layout = QHBoxLayout()
        
        name_layout = QVBoxLayout()
        name_layout.addWidget(QLabel("Nombre de la Materia:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Ej: Matemática 3")
        name_layout.addWidget(self._name_edit)
        form_layout.addLayout(name_layout, stretch=2)

        date_layout = QVBoxLayout()
        date_layout.addWidget(QLabel("Fecha de Inicio:"))
        self._start_date_edit = QDateEdit()
        self._start_date_edit.setCalendarPopup(True)
        self._start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self._start_date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(self._start_date_edit)
        form_layout.addLayout(date_layout, stretch=1)

        layout.addLayout(form_layout)

        # Syllabus Section
        layout.addWidget(QLabel("Temario (Syllabus):"))
        
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Semana Inicio", "Semana Fin", "Tema"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self._table)

        # Table buttons
        tb_layout = QHBoxLayout()
        self._add_topic_btn = QPushButton("+ Agregar Tema")
        self._add_topic_btn.clicked.connect(self._add_topic)
        tb_layout.addWidget(self._add_topic_btn)

        self._remove_topic_btn = QPushButton("- Eliminar Seleccionado")
        self._remove_topic_btn.setObjectName("dangerButton")
        self._remove_topic_btn.clicked.connect(self._remove_topic)
        tb_layout.addWidget(self._remove_topic_btn)
        
        tb_layout.addStretch()
        layout.addLayout(tb_layout)

        # Action Buttons
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
        self._name_edit.setText(self._subject_data.get("name", ""))
        start_date_str = self._subject_data.get("start_date", "")
        if start_date_str:
            self._start_date_edit.setDate(QDate.fromString(start_date_str, Qt.DateFormat.ISODate))
            
        syllabus = self._subject_data.get("syllabus", [])
        self._table.setRowCount(len(syllabus))
        for row, entry in enumerate(syllabus):
            self._table.setItem(row, 0, QTableWidgetItem(str(entry.get("start_week", 1))))
            self._table.setItem(row, 1, QTableWidgetItem(str(entry.get("end_week", 1))))
            self._table.setItem(row, 2, QTableWidgetItem(entry.get("topic", "")))

    def _add_topic(self):
        row = self._table.rowCount()
        self._table.insertRow(row)
        # Defaults
        self._table.setItem(row, 0, QTableWidgetItem("1"))
        self._table.setItem(row, 1, QTableWidgetItem("1"))
        self._table.setItem(row, 2, QTableWidgetItem("Nuevo tema"))

    def _remove_topic(self):
        row = self._table.currentRow()
        if row >= 0:
            self._table.removeRow(row)

    def _validate_and_accept(self):
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, "Error", "El nombre de la materia no puede estar vacío.")
            self._name_edit.setFocus()
            return

        # Validate syllabus
        for row in range(self._table.rowCount()):
            try:
                sw = int(self._table.item(row, 0).text())
                ew = int(self._table.item(row, 1).text())
                if sw < 1 or ew < sw:
                    raise ValueError
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "Error", f"Fila {row+1}: Las semanas deben ser números enteros, semana inicio >= 1 y fin >= inicio.")
                return
                
            topic = self._table.item(row, 2).text().strip()
            if not topic:
                QMessageBox.warning(self, "Error", f"Fila {row+1}: El tema no puede estar vacío.")
                return

        self.accept()

    def get_subject_data(self) -> dict:
        syllabus = []
        for row in range(self._table.rowCount()):
            syllabus.append({
                "start_week": int(self._table.item(row, 0).text()),
                "end_week": int(self._table.item(row, 1).text()),
                "topic": self._table.item(row, 2).text().strip()
            })
            
        data = {
            "name": self._name_edit.text().strip(),
            "start_date": self._start_date_edit.date().toString(Qt.DateFormat.ISODate),
            "syllabus": syllabus
        }
        
        if self._subject_data and "id" in self._subject_data:
            data["id"] = self._subject_data["id"]
            
        return data

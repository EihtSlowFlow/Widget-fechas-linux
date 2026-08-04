from datetime import date
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QDateEdit
)
from PyQt6.QtCore import Qt, QDate

from backend.models import AcademicPeriod
from app.styles.theme import get_urgency_style


class AcademicPeriodDialog(QDialog):
    def __init__(self, period: AcademicPeriod | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar período académico")
        self.setMinimumWidth(400)
        self._period = period
        
        self._setup_ui()
        if period:
            self._load_data(period)
            
        self._update_estimation()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Name
        name_layout = QVBoxLayout()
        name_layout.setSpacing(5)
        name_label = QLabel("Nombre del período:")
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Ej. Segundo cuatrimestre 2026")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self._name_edit)
        layout.addLayout(name_layout)

        # Start Date
        start_layout = QVBoxLayout()
        start_layout.setSpacing(5)
        start_label = QLabel("Fecha de inicio (debe ser un lunes):")
        self._start_edit = QDateEdit()
        self._start_edit.setCalendarPopup(True)
        self._start_edit.setDisplayFormat("dd/MM/yyyy")
        self._start_edit.setDate(QDate.currentDate())
        self._start_edit.dateChanged.connect(self._update_estimation)
        start_layout.addWidget(start_label)
        start_layout.addWidget(self._start_edit)
        layout.addLayout(start_layout)

        # End Date
        end_layout = QVBoxLayout()
        end_layout.setSpacing(5)
        end_label = QLabel("Fecha de finalización (opcional):")
        self._end_edit = QDateEdit()
        self._end_edit.setCalendarPopup(True)
        self._end_edit.setDisplayFormat("dd/MM/yyyy")
        self._end_edit.setSpecialValueText("Sin configurar (por defecto 16 semanas)")
        self._end_edit.setDate(self._end_edit.minimumDate()) # Triggers special value
        self._end_edit.dateChanged.connect(self._update_estimation)
        end_layout.addWidget(end_label)
        end_layout.addWidget(self._end_edit)
        layout.addLayout(end_layout)

        # Estimation Label
        self._estimation_label = QLabel()
        self._estimation_label.setStyleSheet("color: #a0a0b0; font-style: italic;")
        layout.addWidget(self._estimation_label)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Guardar")
        save_btn.clicked.connect(self._save)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _load_data(self, period: AcademicPeriod):
        self._name_edit.setText(period.name)
        self._start_edit.setDate(QDate.fromString(period.start_date, Qt.DateFormat.ISODate))
        if period.end_date:
            self._end_edit.setDate(QDate.fromString(period.end_date, Qt.DateFormat.ISODate))

    def _update_estimation(self):
        start_date = self._start_edit.date().toPyDate()
        
        if self._end_edit.date() == self._end_edit.minimumDate():
            self._estimation_label.setText(f"Estimación: 16 semanas (Finaliza aprox. {start_date.strftime('%d/%m/%Y')} + 16 semanas)")
        else:
            end_date = self._end_edit.date().toPyDate()
            if end_date < start_date:
                self._estimation_label.setText("Error: La fecha de fin es anterior al inicio.")
                self._estimation_label.setStyleSheet("color: #F44336;")
            else:
                weeks = ((end_date - start_date).days // 7) + 1
                self._estimation_label.setText(f"Duración configurada: {weeks} semanas")
                self._estimation_label.setStyleSheet("color: #a0a0b0; font-style: italic;")

    def _save(self):
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "El nombre no puede estar vacío.")
            return

        start_date = self._start_edit.date().toPyDate()
        if start_date.weekday() != 0:
            QMessageBox.warning(self, "Error", "La fecha de inicio debe corresponder a un lunes.")
            return

        end_date_str = ""
        if self._end_edit.date() != self._end_edit.minimumDate():
            end_date = self._end_edit.date().toPyDate()
            if end_date < start_date:
                QMessageBox.warning(self, "Error", "La fecha de finalización no puede ser anterior al inicio.")
                return
            end_date_str = end_date.isoformat()

        self.period_data = {
            "name": name,
            "start_date": start_date.isoformat(),
            "end_date": end_date_str
        }
        self.accept()

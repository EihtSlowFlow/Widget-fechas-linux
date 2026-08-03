"""
Diálogo para agregar o editar una materia y su temario.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QMessageBox, QAbstractItemView, QComboBox, QTimeEdit,
    QCheckBox
)
from PyQt6.QtCore import Qt, QDate, QTime
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

        end_date_layout = QVBoxLayout()
        self._has_end_date = QCheckBox("Fecha de Fin:")
        self._has_end_date.stateChanged.connect(lambda state: self._end_date_edit.setEnabled(state == Qt.CheckState.Checked.value))
        end_date_layout.addWidget(self._has_end_date)
        self._end_date_edit = QDateEdit()
        self._end_date_edit.setCalendarPopup(True)
        self._end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self._end_date_edit.setDate(QDate.currentDate().addMonths(4))
        self._end_date_edit.setEnabled(False)
        end_date_layout.addWidget(self._end_date_edit)
        form_layout.addLayout(end_date_layout, stretch=1)

        layout.addLayout(form_layout)

        # Schedules Section
        layout.addWidget(QLabel("Horarios de Cursada:"))
        
        self._schedule_table = QTableWidget(0, 4)
        self._schedule_table.setHorizontalHeaderLabels(["Día", "Desde", "Hasta", "Aula/Ubicación"])
        s_header = self._schedule_table.horizontalHeader()
        s_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        s_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        s_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        s_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._schedule_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self._schedule_table)

        sch_btn_layout = QHBoxLayout()
        self._add_sch_btn = QPushButton("+ Agregar Horario")
        self._add_sch_btn.clicked.connect(self._add_schedule)
        sch_btn_layout.addWidget(self._add_sch_btn)

        self._remove_sch_btn = QPushButton("- Eliminar Seleccionado")
        self._remove_sch_btn.setObjectName("dangerButton")
        self._remove_sch_btn.clicked.connect(self._remove_schedule)
        sch_btn_layout.addWidget(self._remove_sch_btn)
        
        sch_btn_layout.addStretch()
        layout.addLayout(sch_btn_layout)

        # Units Section
        layout.addWidget(QLabel("Unidades del programa:"))

        self._units_table = QTableWidget(0, 3)
        self._units_table.setHorizontalHeaderLabels(["Unidad", "Semanas", "Contenidos"])
        u_header = self._units_table.horizontalHeader()
        u_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        u_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        u_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._units_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._units_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self._units_table)

        unit_btn_layout = QHBoxLayout()
        self._add_unit_btn = QPushButton("+ Agregar Unidad")
        self._add_unit_btn.clicked.connect(self._add_unit)
        unit_btn_layout.addWidget(self._add_unit_btn)

        self._edit_unit_btn = QPushButton("Editar Seleccionada")
        self._edit_unit_btn.setObjectName("secondaryButton")
        self._edit_unit_btn.clicked.connect(self._edit_unit)
        unit_btn_layout.addWidget(self._edit_unit_btn)

        self._remove_unit_btn = QPushButton("- Eliminar Seleccionada")
        self._remove_unit_btn.setObjectName("dangerButton")
        self._remove_unit_btn.clicked.connect(self._remove_unit)
        unit_btn_layout.addWidget(self._remove_unit_btn)

        unit_btn_layout.addStretch()
        layout.addLayout(unit_btn_layout)

        # Legacy Syllabus Section
        from PyQt6.QtWidgets import QWidget
        self._legacy_container = QWidget()
        legacy_layout = QVBoxLayout(self._legacy_container)
        legacy_layout.setContentsMargins(0, 0, 0, 0)

        self._legacy_syllabus_label = QLabel("Temario anterior (legado):")
        legacy_layout.addWidget(self._legacy_syllabus_label)
        
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Semana Inicio", "Semana Fin", "Tema"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        legacy_layout.addWidget(self._table)

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
        legacy_layout.addLayout(tb_layout)

        layout.addWidget(self._legacy_container)
        
        has_legacy = bool(self._subject_data and self._subject_data.get("syllabus"))
        self._legacy_container.setVisible(has_legacy)

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
            
        end_date_str = self._subject_data.get("end_date", "")
        if end_date_str:
            self._has_end_date.setChecked(True)
            self._end_date_edit.setDate(QDate.fromString(end_date_str, Qt.DateFormat.ISODate))
            
        syllabus = self._subject_data.get("syllabus", [])
        self._table.setRowCount(len(syllabus))
        for row, entry in enumerate(syllabus):
            self._table.setItem(row, 0, QTableWidgetItem(str(entry.get("start_week", 1))))
            self._table.setItem(row, 1, QTableWidgetItem(str(entry.get("end_week", 1))))
            self._table.setItem(row, 2, QTableWidgetItem(entry.get("topic", "")))

        schedules = self._subject_data.get("class_schedule", [])
        self._schedule_table.setRowCount(len(schedules))
        for row, entry in enumerate(schedules):
            combo = QComboBox()
            combo.addItems(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
            day_idx = entry.get("day_of_week", 1) - 1
            if 0 <= day_idx <= 6:
                combo.setCurrentIndex(day_idx)
            self._schedule_table.setCellWidget(row, 0, combo)
            
            start_time = QTimeEdit()
            start_time.setDisplayFormat("HH:mm")
            start_time.setTime(QTime.fromString(entry.get("start_time", "08:00"), "HH:mm"))
            self._schedule_table.setCellWidget(row, 1, start_time)
            
            end_time = QTimeEdit()
            end_time.setDisplayFormat("HH:mm")
            end_time.setTime(QTime.fromString(entry.get("end_time", "10:00"), "HH:mm"))
            self._schedule_table.setCellWidget(row, 2, end_time)
            
            self._schedule_table.setItem(row, 3, QTableWidgetItem(entry.get("location", "")))

        units = self._subject_data.get("units", [])
        for unit_data in units:
            self._insert_unit_row(unit_data)

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

    def _add_schedule(self):
        row = self._schedule_table.rowCount()
        self._schedule_table.insertRow(row)
        
        combo = QComboBox()
        combo.addItems(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
        self._schedule_table.setCellWidget(row, 0, combo)
        
        start_time = QTimeEdit()
        start_time.setDisplayFormat("HH:mm")
        start_time.setTime(QTime(8, 0))
        self._schedule_table.setCellWidget(row, 1, start_time)
        
        end_time = QTimeEdit()
        end_time.setDisplayFormat("HH:mm")
        end_time.setTime(QTime(10, 0))
        self._schedule_table.setCellWidget(row, 2, end_time)
        
        self._schedule_table.setItem(row, 3, QTableWidgetItem(""))

    def _remove_schedule(self):
        row = self._schedule_table.currentRow()
        if row >= 0:
            self._schedule_table.removeRow(row)

    def _add_unit(self):
        from app.dialogs.syllabus_unit_dialog import SyllabusUnitDialog
        dialog = SyllabusUnitDialog(self)
        if dialog.exec():
            unit_data = dialog.get_unit_data()
            self._insert_unit_row(unit_data)

    def _edit_unit(self):
        row = self._units_table.currentRow()
        if row < 0:
            return
        unit_data = self._get_unit_at_row(row)
        from app.dialogs.syllabus_unit_dialog import SyllabusUnitDialog
        dialog = SyllabusUnitDialog(self, unit_data=unit_data)
        if dialog.exec():
            new_data = dialog.get_unit_data()
            self._update_unit_row(row, new_data)

    def _remove_unit(self):
        row = self._units_table.currentRow()
        if row >= 0:
            self._units_table.removeRow(row)

    def _insert_unit_row(self, unit_data):
        row = self._units_table.rowCount()
        self._units_table.insertRow(row)
        self._update_unit_row(row, unit_data)

    def _update_unit_row(self, row, unit_data):
        self._units_table.setItem(row, 0, QTableWidgetItem(unit_data.get("name", "")))
        weeks_str = ", ".join(str(w) for w in unit_data.get("weeks", []))
        self._units_table.setItem(row, 1, QTableWidgetItem(weeks_str))
        contents_count = len(unit_data.get("contents", []))
        self._units_table.setItem(row, 2, QTableWidgetItem(f"{contents_count} contenidos"))
        # Store original data in the name item
        self._units_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, unit_data)

    def _get_unit_at_row(self, row):
        item = self._units_table.item(row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole) or {}
        return {}

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
                QMessageBox.warning(self, "Error", f"Fila temario {row+1}: Las semanas deben ser números enteros, inicio >= 1 y fin >= inicio.")
                return
                
            topic = self._table.item(row, 2).text().strip()
            if not topic:
                QMessageBox.warning(self, "Error", f"Fila temario {row+1}: El tema no puede estar vacío.")
                return

        if self._has_end_date.isChecked():
            if self._end_date_edit.date() < self._start_date_edit.date():
                QMessageBox.warning(self, "Error", "La fecha de fin no puede ser anterior a la de inicio.")
                self._end_date_edit.setFocus()
                return

        # Validate schedules
        for row in range(self._schedule_table.rowCount()):
            start = self._schedule_table.cellWidget(row, 1).time()
            end = self._schedule_table.cellWidget(row, 2).time()
            
            if start >= end:
                QMessageBox.warning(self, "Error", f"Fila horario {row+1}: La hora de inicio debe ser menor a la hora de fin.")
                return

        # Check for overlaps
        current_data = self.get_subject_data()
        
        try:
            from backend.cache import read_subjects
            from backend.fechas_sync import generate_weekly_schedule, find_schedule_overlaps
            from backend.models import SubjectSyllabus
            from datetime import date
            
            # Use current date as today for overlaps check
            today = date.today()
            subjects = read_subjects()
            
            # Remove current subject from list if editing, to replace with current_data
            current_id = current_data.get("id")
            if current_id:
                subjects = [s for s in subjects if s.id != current_id]
                
            current_subj_obj = SubjectSyllabus.from_dict(current_data)
            
            # Generate external schedule for all other active subjects
            schedule_list = generate_weekly_schedule(subjects, today)
            
            # Force append current subject's schedule, ignoring its active status
            for entry in current_data["class_schedule"]:
                schedule_list.append({
                    "day_of_week": entry["day_of_week"],
                    "start_time": entry["start_time"],
                    "end_time": entry["end_time"],
                    "subject_id": current_subj_obj.id,
                    "subject_name": current_subj_obj.name,
                })
            
            overlaps = find_schedule_overlaps(schedule_list)
            
            if overlaps:
                # Find overlaps involving the current subject
                relevant_overlaps = []
                for e1, e2 in overlaps:
                    if e1["subject_id"] == current_subj_obj.id or e2["subject_id"] == current_subj_obj.id:
                        days = ["", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                        day_name = days[e1["day_of_week"]] if 1 <= e1["day_of_week"] <= 7 else str(e1["day_of_week"])
                        relevant_overlaps.append(
                            f"El horario del {day_name} {e1['start_time']}–{e1['end_time']} ({e1['subject_name']}) "
                            f"se superpone con {e2['start_time']}–{e2['end_time']} ({e2['subject_name']})."
                        )
                
                if relevant_overlaps:
                    msg = "\n".join(relevant_overlaps) + "\n\n¿Deseás guardar igualmente?"
                    reply = QMessageBox.question(
                        self, "Advertencia de superposición", msg,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return
                        
        except Exception as e:
            import logging
            logging.getLogger("fechas.app").error(f"Error checking overlaps: {e}")

        self.accept()

    def get_subject_data(self) -> dict:
        syllabus = []
        for row in range(self._table.rowCount()):
            syllabus.append({
                "start_week": int(self._table.item(row, 0).text()),
                "end_week": int(self._table.item(row, 1).text()),
                "topic": self._table.item(row, 2).text().strip()
            })
            
        schedules = []
        for row in range(self._schedule_table.rowCount()):
            combo = self._schedule_table.cellWidget(row, 0)
            start_time = self._schedule_table.cellWidget(row, 1).time().toString("HH:mm")
            end_time = self._schedule_table.cellWidget(row, 2).time().toString("HH:mm")
            location_item = self._schedule_table.item(row, 3)
            location = location_item.text().strip() if location_item else ""
            
            schedules.append({
                "day_of_week": combo.currentIndex() + 1,
                "start_time": start_time,
                "end_time": end_time,
                "location": location
            })
            
        units = []
        for row in range(self._units_table.rowCount()):
            unit_data = self._get_unit_at_row(row)
            if unit_data:
                units.append(unit_data)

        data = {
            "name": self._name_edit.text().strip(),
            "start_date": self._start_date_edit.date().toString(Qt.DateFormat.ISODate),
            "end_date": self._end_date_edit.date().toString(Qt.DateFormat.ISODate) if self._has_end_date.isChecked() else "",
            "syllabus": syllabus,
            "class_schedule": schedules,
            "units": units
        }
        
        if self._subject_data and "id" in self._subject_data:
            data["id"] = self._subject_data["id"]
            
        return data

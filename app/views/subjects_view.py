"""
Vista de gestión de materias y temarios.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.cache import read_subjects, write_subjects
from backend.models import SubjectSyllabus, SyllabusEntry
from app.styles.theme import DARK_PALETTE


class SubjectsView(QWidget):
    """Vista para gestionar materias y sus temarios."""

    subjects_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._subjects: list[SubjectSyllabus] = []
        self._setup_ui()
        self.reload_subjects()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Materias (Semana de cursada)")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("+ Agregar Materia")
        add_btn.clicked.connect(self._add_subject)
        header.addWidget(add_btn)

        layout.addLayout(header)

        # Subjects list
        self._list = QListWidget()
        self._list.setSpacing(4)
        self._list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list, stretch=1)

        # Detail panel
        self._detail_frame = QFrame()
        self._detail_frame.setStyleSheet(f"""
            QFrame {{
                background: {DARK_PALETTE['bg_card']};
                border: 1px solid {DARK_PALETTE['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        detail_layout = QVBoxLayout(self._detail_frame)

        self._detail_name = QLabel("Seleccioná una materia")
        self._detail_name.setFont(self._detail_name.font())
        self._detail_name.setStyleSheet(f"font-weight: 600; font-size: 14px; background: transparent;")
        detail_layout.addWidget(self._detail_name)

        self._detail_start = QLabel("")
        self._detail_start.setStyleSheet(f"color: {DARK_PALETTE['text_secondary']}; background: transparent;")
        detail_layout.addWidget(self._detail_start)

        self._detail_schedule = QLabel("")
        self._detail_schedule.setWordWrap(True)
        self._detail_schedule.setStyleSheet(f"color: {DARK_PALETTE['text_primary']}; font-size: 13px; background: transparent; margin-top: 8px; margin-bottom: 8px;")
        detail_layout.addWidget(self._detail_schedule)

        self._detail_syllabus = QLabel("")
        self._detail_syllabus.setWordWrap(True)
        self._detail_syllabus.setStyleSheet(f"color: {DARK_PALETTE['text_muted']}; font-size: 12px; background: transparent;")
        detail_layout.addWidget(self._detail_syllabus)

        # Action buttons
        btn_row = QHBoxLayout()
        self._edit_btn = QPushButton("Editar")
        self._edit_btn.setObjectName("secondaryButton")
        self._edit_btn.clicked.connect(self._edit_subject)
        btn_row.addWidget(self._edit_btn)

        self._delete_btn = QPushButton("Eliminar")
        self._delete_btn.setObjectName("dangerButton")
        self._delete_btn.clicked.connect(self._delete_subject)
        btn_row.addWidget(self._delete_btn)

        btn_row.addStretch()
        detail_layout.addLayout(btn_row)

        layout.addWidget(self._detail_frame)

    def reload_subjects(self):
        """Recarga las materias desde disco."""
        self._subjects = read_subjects()
        self._list.clear()
        for s in self._subjects:
            if hasattr(s, 'units') and s.units:
                info = f"{len(s.units)} unidades"
            else:
                info = "Sin unidades configuradas"
            item = QListWidgetItem(f"📚 {s.name} ({info}, inicio: {s.start_date})")
            self._list.addItem(item)

    def _on_selection_changed(self, row: int):
        """Actualiza el panel de detalle."""
        if row < 0 or row >= len(self._subjects):
            return
        s = self._subjects[row]
        self._detail_name.setText(s.name)
        if getattr(s, 'end_date', ""):
            self._detail_start.setText(f"Inicio: {s.start_date} | Fin: {s.end_date}")
        else:
            self._detail_start.setText(f"Inicio de cursada: {s.start_date}")
            
        if not hasattr(s, 'class_schedule') or not s.class_schedule:
            self._detail_schedule.setText("Sin horarios configurados.")
        else:
            days = ["", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            lines = []
            for entry in s.class_schedule:
                day_name = days[entry.day_of_week] if 1 <= entry.day_of_week <= 7 else "Desconocido"
                loc = f" (📍 {entry.location})" if entry.location else ""
                lines.append(f"• {day_name} {entry.start_time}-{entry.end_time}{loc}")
            self._detail_schedule.setText("Horarios:\n" + "\n".join(lines))
        
        if hasattr(s, 'units') and s.units:
            lines = []
            for unit in s.units:
                weeks_str = ", ".join(str(w) for w in unit.weeks)
                lines.append(unit.name)
                lines.append(f"Semanas: {weeks_str}")
                if unit.contents:
                    for c in unit.contents:
                        lines.append(f"  • {c}")
                else:
                    lines.append("  Sin contenidos configurados.")
                lines.append("")  # blank line between units
            self._detail_syllabus.setText("\n".join(lines).rstrip())
        else:
            self._detail_syllabus.setText("Sin unidades configuradas.")

    def _delete_subject(self):
        row = self._list.currentRow()
        if row < 0:
            return
        s = self._subjects[row]
        reply = QMessageBox.question(
            self, "Eliminar materia",
            f"¿Eliminar la materia '{s.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._subjects.pop(row)
            write_subjects(self._subjects)
            self.reload_subjects()
            self.subjects_changed.emit()

    def _add_subject(self):
        from app.dialogs.subject_dialog import SubjectDialog
        dialog = SubjectDialog(self)
        if dialog.exec():
            data = dialog.get_subject_data()
            new_subject = SubjectSyllabus.from_dict(data)
            self._subjects.append(new_subject)
            write_subjects(self._subjects)
            self.reload_subjects()
            self.subjects_changed.emit()

    def _edit_subject(self):
        row = self._list.currentRow()
        if row < 0:
            return
        s = self._subjects[row]
        
        from app.dialogs.subject_dialog import SubjectDialog
        dialog = SubjectDialog(self, subject_data=s.to_dict())
        if dialog.exec():
            data = dialog.get_subject_data()
            self._subjects[row] = SubjectSyllabus.from_dict(data)
            write_subjects(self._subjects)
            self.reload_subjects()
            self._list.setCurrentRow(row)
            self.subjects_changed.emit()

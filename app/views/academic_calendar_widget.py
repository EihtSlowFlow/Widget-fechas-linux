from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QToolButton, 
    QCalendarWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal

class AcademicCalendarWidget(QWidget):
    dateClicked = pyqtSignal(QDate)
    weekClicked = pyqtSignal(QDate, QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._academic_period = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Weeks column
        self._weeks_layout = QVBoxLayout()
        # Offset to roughly align with the calendar grid (bypassing the month/year header and day names)
        # Note: In a real app we might need to adjust this depending on the exact styling, but 32 is a safe default for breeze.
        self._weeks_layout.setContentsMargins(0, 32, 0, 0) 
        self._weeks_layout.setSpacing(0)
        
        self._week_buttons = []
        for i in range(6): # QCalendarWidget always shows 6 rows
            btn = QToolButton()
            btn.setText("S -")
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
            btn.clicked.connect(lambda checked, idx=i: self._on_week_clicked(idx))
            self._weeks_layout.addWidget(btn)
            self._week_buttons.append(btn)
            
        layout.addLayout(self._weeks_layout)

        # Native calendar
        self._calendar = QCalendarWidget()
        self._calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self._calendar.setGridVisible(True)
        self._calendar.currentPageChanged.connect(self._update_weeks)
        self._calendar.selectionChanged.connect(self._update_weeks)
        self._calendar.clicked.connect(self.dateClicked)
        layout.addWidget(self._calendar, stretch=1)

    def set_academic_period(self, period):
        self._academic_period = period
        self._update_weeks()

    def setDateTextFormat(self, qdate, fmt):
        self._calendar.setDateTextFormat(qdate, fmt)

    def selectedDate(self) -> QDate:
        return self._calendar.selectedDate()
        
    def setSelectedDate(self, date: QDate):
        self._calendar.setSelectedDate(date)

    def _update_weeks(self, year=None, month=None):
        if year is None or month is None:
            year = self._calendar.yearShown()
            month = self._calendar.monthShown()

        first_month_day = date(year, month, 1)
        grid_start = first_month_day - timedelta(days=first_month_day.weekday())

        for i in range(6):
            row_monday = grid_start + timedelta(weeks=i)
            btn = self._week_buttons[i]
            btn.setProperty("row_monday", row_monday)
            
            if self._academic_period:
                try:
                    from backend.academic_weeks import academic_week_number
                    week_num = academic_week_number(row_monday, self._academic_period)
                    if week_num is not None:
                        btn.setText(f"Sem {week_num}")
                        # Highlight if selected date is in this week
                        sel_date = self._calendar.selectedDate().toPyDate()
                        if row_monday <= sel_date <= row_monday + timedelta(days=6):
                            btn.setStyleSheet("font-weight: bold; background-color: #3d3d52; color: #7c9df5; border-radius: 4px;")
                        else:
                            btn.setStyleSheet("background: transparent; color: #e0e0e8;")
                        continue
                except ImportError:
                    pass
            btn.setText("S -")
            btn.setStyleSheet("color: #606070; background: transparent;")

    def _on_week_clicked(self, row_idx):
        btn = self._week_buttons[row_idx]
        row_monday = btn.property("row_monday")
        if row_monday:
            qdate = QDate(row_monday.year, row_monday.month, row_monday.day)
            self._calendar.setSelectedDate(qdate)
            row_sunday = row_monday + timedelta(days=6)
            q_sunday = QDate(row_sunday.year, row_sunday.month, row_sunday.day)
            self.weekClicked.emit(qdate, q_sunday)

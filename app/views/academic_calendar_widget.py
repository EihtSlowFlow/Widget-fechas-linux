from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QHBoxLayout, QToolButton,
    QSizePolicy, QLabel
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal

class AcademicCalendarWidget(QWidget):
    date_clicked = pyqtSignal(date)
    week_clicked = pyqtSignal(date, date)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._academic_period = None
        self._events = []
        
        self._current_year = date.today().year
        self._current_month = date.today().month
        self._selected_date = date.today()
        
        self._setup_ui()
        self.go_to_today()

    def _setup_ui(self):
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        
        # Row 0: Navigation
        self._month_label = QLabel()
        self._month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._month_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        prev_btn = QToolButton()
        prev_btn.setText("<")
        prev_btn.clicked.connect(self._prev_month)
        
        next_btn = QToolButton()
        next_btn.setText(">")
        next_btn.clicked.connect(self._next_month)
        
        nav_layout = QHBoxLayout()
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(self._month_label, stretch=1)
        nav_layout.addWidget(next_btn)
        
        self._layout.addLayout(nav_layout, 0, 1, 1, 7) # Span across days

        # Row 1: Headers
        days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for col, day_name in enumerate(days, start=1):
            lbl = QLabel(day_name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; color: #a0a0b0;")
            self._layout.addWidget(lbl, 1, col)
            
        # Rows 2-7: Grid (42 days + 6 weeks)
        self._week_buttons = []
        self._day_buttons = []
        
        for row in range(2, 8):
            # Week button
            w_btn = QToolButton()
            w_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            w_btn.clicked.connect(lambda checked, r=row-2: self._on_week_clicked(r))
            self._layout.addWidget(w_btn, row, 0)
            self._week_buttons.append(w_btn)
            
            # Day buttons
            for col in range(1, 8):
                d_btn = QToolButton()
                d_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                d_btn.clicked.connect(lambda checked, idx=len(self._day_buttons): self._on_day_clicked(idx))
                self._layout.addWidget(d_btn, row, col)
                self._day_buttons.append(d_btn)

    def set_academic_period(self, period):
        self._academic_period = period
        self._update_grid()

    def set_events(self, events):
        self._events = events
        self._update_grid()

    def set_selected_date(self, target_date: date):
        self._selected_date = target_date
        # Check if we need to change month view
        if target_date.month != self._current_month or target_date.year != self._current_year:
            self._current_month = target_date.month
            self._current_year = target_date.year
        self._update_grid()

    def selected_date(self) -> date:
        return self._selected_date

    def show_month(self, year: int, month: int):
        self._current_year = year
        self._current_month = month
        self._update_grid()

    def go_to_today(self):
        self.set_selected_date(date.today())

    def _prev_month(self):
        m = self._current_month - 1
        y = self._current_year
        if m < 1:
            m = 12
            y -= 1
        self.show_month(y, m)

    def _next_month(self):
        m = self._current_month + 1
        y = self._current_year
        if m > 12:
            m = 1
            y += 1
        self.show_month(y, m)

    def _update_grid(self):
        months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        self._month_label.setText(f"{months[self._current_month - 1]} {self._current_year}")
        
        first_day = date(self._current_year, self._current_month, 1)
        grid_start = first_day - timedelta(days=first_day.weekday())
        
        sel_monday = self._selected_date - timedelta(days=self._selected_date.weekday())
        today = date.today()
        
        # Compute events dictionary (indexed by date)
        events_by_date = {}
        for e in self._events:
            due = e.get("due_date", "")
            if not due:
                continue
            try:
                from datetime import datetime
                d = datetime.fromisoformat(due).date()
                if d not in events_by_date:
                    events_by_date[d] = []
                events_by_date[d].append(e)
            except ValueError:
                continue
        
        from app.styles.theme import get_urgency_style, highest_incomplete_urgency
        
        today_monday = today - timedelta(days=today.weekday())
        
        for i in range(6):
            row_monday = grid_start + timedelta(weeks=i)
            w_btn = self._week_buttons[i]
            w_btn.setProperty("row_monday", row_monday)
            
            is_selected_week = (row_monday == sel_monday)
            
            week_num = None
            is_outside = True
            
            if self._academic_period:
                try:
                    from backend.academic_weeks import academic_week_number
                    week_num = academic_week_number(row_monday, self._academic_period)
                    is_outside = week_num is None
                except ImportError:
                    pass
            
            is_current_week = (row_monday == today_monday)
            
            if not is_outside:
                w_btn.setText(f"Sem {week_num}")
                w_btn.setEnabled(True)
                if is_selected_week:
                    w_btn.setStyleSheet("font-weight: bold; background-color: #3d3d52; color: #7c9df5; border-radius: 4px;")
                elif is_current_week:
                    w_btn.setStyleSheet("font-weight: bold; background: transparent; color: #7c9df5; border: 1px solid #7c9df5; border-radius: 4px;")
                else:
                    w_btn.setStyleSheet("background: transparent; color: #e0e0e8;")
            else:
                w_btn.setText("S -")
                w_btn.setEnabled(False)
                w_btn.setStyleSheet("color: #606070; background: transparent;")
            
            for j in range(7):
                cell_idx = i * 7 + j
                cell_date = grid_start + timedelta(days=cell_idx)
                d_btn = self._day_buttons[cell_idx]
                d_btn.setProperty("cell_date", cell_date)
                
                d_btn.setText(str(cell_date.day))
                
                # Verify if cell is outside academic period completely
                cell_outside = False
                if self._academic_period:
                    try:
                        from backend.academic_weeks import academic_week_number
                        cell_outside = academic_week_number(cell_date, self._academic_period) is None
                    except ImportError:
                        pass
                
                d_btn.setEnabled(not cell_outside)
                
                # Styles
                style_chunks = ["border-radius: 4px;"]
                
                if cell_outside:
                    style_chunks.append("color: #404050; background-color: transparent;")
                    d_btn.setStyleSheet(" ".join(style_chunks))
                    continue
                
                # Is other month?
                if cell_date.month != self._current_month:
                    style_chunks.append("color: #606070;")
                else:
                    style_chunks.append("color: #ffffff;")
                    
                # Is selected week?
                if is_selected_week:
                    style_chunks.append("background-color: #3d3d52;")
                else:
                    style_chunks.append("background-color: transparent;")
                    
                # Urgency marker
                urg = highest_incomplete_urgency(events_by_date.get(cell_date, []))
                if urg:
                    color = get_urgency_style(urg)
                    style_chunks.append(f"border: 2px solid {color};")
                else:
                    style_chunks.append("border: 1px solid transparent;")
                    
                # Is today?
                if cell_date == today:
                    style_chunks.append("font-weight: bold; color: #7c9df5; text-decoration: underline;")
                    if not is_selected_week:
                        style_chunks.append("background-color: #2a2a3c;")
                    
                # Is selected date? (exact match)
                if cell_date == self._selected_date:
                    style_chunks.append("background-color: #555570;") # slightly brighter
                    
                d_btn.setStyleSheet(" ".join(style_chunks))

    def _on_week_clicked(self, row_idx):
        btn = self._week_buttons[row_idx]
        row_monday = btn.property("row_monday")
        if row_monday:
            self.set_selected_date(row_monday)
            row_sunday = row_monday + timedelta(days=6)
            self.week_clicked.emit(row_monday, row_sunday)

    def _on_day_clicked(self, cell_idx):
        btn = self._day_buttons[cell_idx]
        cell_date = btn.property("cell_date")
        if cell_date:
            self.set_selected_date(cell_date)
            self.date_clicked.emit(cell_date)

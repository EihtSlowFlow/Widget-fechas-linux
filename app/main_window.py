"""
Ventana principal de la aplicación Fechas Académicas.
Centro de gestión con vistas de calendario, timeline y fuentes.
"""

import json
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import CACHE_FILE, ensure_dirs
from backend.cache import read_cache
from app.styles.theme import DARK_PALETTE, get_urgency_style
from app.views.timeline_view import TimelineView
from app.views.calendar_view import CalendarView
from app.views.sources_view import SourcesView
from app.views.subjects_view import SubjectsView
from app.dialogs.event_dialog import EventDialog


class MainWindow(QMainWindow):
    """Ventana principal — Centro de Gestión de Fechas Académicas."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("📅 Fechas Académicas — Centro de Gestión")
        self.setMinimumSize(900, 600)
        self.resize(1050, 700)
        self._events = []
        self._setup_ui()
        self._load_data()
        self._start_auto_refresh()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 0)
        main_layout.setSpacing(8)

        # ─── Top bar ─────────────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        app_icon = QLabel("📅")
        app_icon.setFont(QFont("", 22))
        app_icon.setStyleSheet("background: transparent;")
        top_bar.addWidget(app_icon)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_label = QLabel("Fechas Académicas")
        title_label.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {DARK_PALETTE['text_primary']}; background: transparent;")
        title_col.addWidget(title_label)

        subtitle = QLabel("Centro de Gestión — UNRN")
        subtitle.setObjectName("subtitle")
        subtitle.setStyleSheet(f"color: {DARK_PALETTE['text_muted']}; background: transparent;")
        title_col.addWidget(subtitle)
        top_bar.addLayout(title_col)

        top_bar.addStretch()

        # New event button
        new_btn = QPushButton("+ Nuevo Evento")
        new_btn.setFixedHeight(38)
        new_btn.clicked.connect(self._add_event)
        top_bar.addWidget(new_btn)

        # Sync button
        self._sync_btn = QPushButton("🔄 Sincronizar")
        self._sync_btn.setObjectName("secondaryButton")
        self._sync_btn.setFixedHeight(38)
        self._sync_btn.clicked.connect(self._force_sync)
        top_bar.addWidget(self._sync_btn)

        main_layout.addLayout(top_bar)

        # ─── Tab widget ──────────────────────────────────
        self._tabs = QTabWidget()

        self._timeline_view = TimelineView()
        self._tabs.addTab(self._timeline_view, "📋 Timeline")

        self._calendar_view = CalendarView()
        self._tabs.addTab(self._calendar_view, "📅 Calendario")

        self._subjects_view = SubjectsView()
        self._subjects_view.subjects_changed.connect(self._on_source_changed)
        self._tabs.addTab(self._subjects_view, "📚 Materias")

        self._sources_view = SourcesView()
        self._sources_view.source_changed.connect(self._on_source_changed)
        self._tabs.addTab(self._sources_view, "⚙ Fuentes")

        main_layout.addWidget(self._tabs)

        # ─── Status bar ──────────────────────────────────
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

        self._status_next = QLabel("")
        self._status_next.setStyleSheet("background: transparent;")
        self._statusbar.addWidget(self._status_next, stretch=1)

        self._status_sync = QLabel("")
        self._status_sync.setStyleSheet("background: transparent;")
        self._statusbar.addPermanentWidget(self._status_sync)

        self._status_count = QLabel("")
        self._status_count.setStyleSheet("background: transparent;")
        self._statusbar.addPermanentWidget(self._status_count)

    def _load_data(self):
        """Carga datos desde cache.json."""
        ensure_dirs()
        cache = read_cache()
        self._events = cache.events

        # Update views
        self._timeline_view.set_events(self._events)
        self._calendar_view.set_events(self._events)

        # Update status bar
        self._status_count.setText(f"📊 {len(self._events)} eventos")

        if cache.last_sync:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(cache.last_sync)
                self._status_sync.setText(f"🔄 Sync: {dt.strftime('%H:%M')}")
            except (ValueError, TypeError):
                self._status_sync.setText(f"🔄 Sync: {cache.last_sync}")
        else:
            self._status_sync.setText("🔄 Sin sincronizar")

        if self._events:
            next_event = self._events[0]
            days = next_event.get("days_remaining", 0)
            title = next_event.get("title", "")[:40]
            urgency = next_event.get("urgency", "green")
            color = get_urgency_style(urgency)
            if days == 0:
                self._status_next.setText(f"⚠ <b>HOY</b>: {title}")
            elif days == 1:
                self._status_next.setText(f"Próximo: <b>{title}</b> — mañana")
            elif days < 0:
                self._status_next.setText(f"⚠ <b>VENCIDO</b>: {title}")
            else:
                self._status_next.setText(f"Próximo: <b>{title}</b> en {days} días")

        # Count new events
        new_count = sum(1 for e in self._events if e.get("is_new"))
        if new_count > 0:
            self._status_count.setText(
                f"📊 {len(self._events)} eventos  |  🆕 {new_count} nuevos hoy"
            )

    def _start_auto_refresh(self):
        """Refresca los datos cada 60 segundos."""
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._load_data)
        self._refresh_timer.start(60000)

    def _add_event(self):
        """Abre el diálogo de nuevo evento."""
        dialog = EventDialog(parent=self)
        if dialog.exec():
            self._force_sync()

    def _force_sync(self):
        """Ejecuta la sincronización utilizando QProcess."""
        from PyQt6.QtCore import QProcess
        
        if hasattr(self, '_sync_process') and self._sync_process.state() != QProcess.ProcessState.NotRunning:
            self._status_sync.setText("🔄 Sincronización ya en curso...")
            return

        project_dir = Path(__file__).resolve().parent.parent
        
        self._sync_process = QProcess(self)
        self._sync_process.setWorkingDirectory(str(project_dir))
        
        self._is_polling_lock = False
        
        def _check_lock():
            if not self._is_polling_lock:
                return
            self._lock_check_process = QProcess(self)
            self._lock_check_process.setWorkingDirectory(str(project_dir))
            
            def on_lock_check_finished(code, status):
                if not self._is_polling_lock:
                    return
                if code == 0:
                    if hasattr(self, '_sync_timeout_timer'):
                        self._sync_timeout_timer.stop()
                    self._is_polling_lock = False
                    self._sync_btn.setEnabled(True)
                    self._sync_btn.setText("🔄 Sincronizar")
                    self._load_data()
                else:
                    QTimer.singleShot(3000, _check_lock)
                    
            def on_lock_check_error(error):
                if hasattr(self, '_sync_timeout_timer'):
                    self._sync_timeout_timer.stop()
                self._is_polling_lock = False
                self._sync_btn.setEnabled(True)
                self._sync_btn.setText("🔄 Sincronizar")
                self._load_data()
                
            self._lock_check_process.finished.connect(on_lock_check_finished)
            self._lock_check_process.errorOccurred.connect(on_lock_check_error)
            self._lock_check_process.start("python3", [str(project_dir / "backend" / "fechas_sync.py"), "--check-lock"])

        def on_finished(exit_code, exit_status):
            if exit_code == 3:
                self._status_sync.setText("🔄 Sincronización ya en curso (esperando)...")
                self._is_polling_lock = True
                QTimer.singleShot(3000, _check_lock)
            else:
                if hasattr(self, '_sync_timeout_timer'):
                    self._sync_timeout_timer.stop()

                if exit_code == 0:
                    self._sync_btn.setEnabled(True)
                    self._sync_btn.setText("🔄 Sincronizar")
                    self._load_data()
                else:
                    self._sync_btn.setEnabled(True)
                    self._sync_btn.setText("🔄 Sincronizar")
                    QMessageBox.warning(self, "Error", f"Error en sincronización (código {exit_code})")
                    self._load_data()
                
        self._sync_process.finished.connect(on_finished)
        
        def on_error(error):
            if hasattr(self, '_sync_timeout_timer'):
                self._sync_timeout_timer.stop()
            self._sync_btn.setEnabled(True)
            self._sync_btn.setText("🔄 Sincronizar")
            QMessageBox.warning(self, "Error", f"No se pudo iniciar la sincronización: {error}")
            self._load_data()
            
        self._sync_process.errorOccurred.connect(on_error)
        
        def on_timeout():
            self._is_polling_lock = False
            self._sync_btn.setEnabled(True)
            self._sync_btn.setText("🔄 Sincronizar")
            self._status_sync.setText("🔄 Sincronización en segundo plano...")
            
        self._sync_timeout_timer = QTimer(self)
        self._sync_timeout_timer.setSingleShot(True)
        self._sync_timeout_timer.timeout.connect(on_timeout)
        self._sync_timeout_timer.start(120000)
        
        self._sync_btn.setEnabled(False)
        self._sync_btn.setText("🔄 Sincronizando...")
        self._status_sync.setText("🔄 Sincronizando...")
        
        self._sync_process.start("python3", [str(project_dir / "backend" / "fechas_sync.py")])


    def _on_source_changed(self):
        """Recarga datos cuando se modifica una fuente."""
        self._force_sync()

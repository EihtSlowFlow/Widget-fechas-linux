#!/usr/bin/env python3
"""
Punto de entrada de la aplicación Fechas Académicas.
Centro de gestión para visualizar, filtrar y administrar eventos académicos.

Uso:
    python3 main.py                  # Abre la aplicación normalmente
    python3 main.py --add-event      # Abre directamente el diálogo de nuevo evento
"""

import sys
import argparse
from pathlib import Path

# Asegurar que el proyecto esté en el path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from app.styles.theme import get_app_stylesheet
from app.main_window import MainWindow
from backend.config import ensure_dirs


def main():
    parser = argparse.ArgumentParser(description="Fechas Académicas — Centro de Gestión")
    parser.add_argument(
        "--add-event",
        action="store_true",
        help="Abrir directamente el diálogo de nuevo evento",
    )
    args = parser.parse_args()

    # Asegurar que existan los directorios de datos
    ensure_dirs()

    app = QApplication(sys.argv)
    app.setApplicationName("Fechas Académicas")
    app.setOrganizationName("UNRN")
    app.setDesktopFileName("fechas-academicas")

    # Intentar usar un ícono de KDE disponible
    app.setWindowIcon(QIcon.fromTheme("view-calendar-upcoming-events"))

    # Aplicar tema oscuro
    app.setStyleSheet(get_app_stylesheet())

    window = MainWindow()
    window.show()

    # Si se pidió agregar evento directamente
    if args.add_event:
        window._add_event()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

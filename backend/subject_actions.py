#!/usr/bin/env python3
"""Acciones seguras para materias invocadas desde el widget Plasma."""

import argparse
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.cache import read_subjects
from backend.virtual_class import is_valid_virtual_class_url

SUBJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def virtual_class_url_for_subject(subject_id: str) -> str | None:
    """Obtiene la URL desde subjects.json; nunca la recibe desde el shell."""
    if not SUBJECT_ID_PATTERN.fullmatch(subject_id):
        return None
    for subject in read_subjects():
        if subject.id == subject_id:
            url = getattr(subject, "virtual_class_url", "")
            return url if is_valid_virtual_class_url(url) else None
    return None


def copy_virtual_class_link(subject_id: str) -> int:
    url = virtual_class_url_for_subject(subject_id)
    if url is None:
        return 2

    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(["fechas-copy-link"])
    app.clipboard().setText(url)
    # Da tiempo a KDE/Klipper para adquirir el contenido antes de terminar.
    QTimer.singleShot(150, app.quit)
    app.exec()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["copy-link"])
    parser.add_argument("subject_id")
    args = parser.parse_args()
    return copy_virtual_class_link(args.subject_id)


if __name__ == "__main__":
    raise SystemExit(main())

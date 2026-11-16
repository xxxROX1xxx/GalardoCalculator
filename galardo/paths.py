from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths

APP_NAME = "Galardo"


def resource_dir() -> Path:
    """Directory with bundled resources, both in source and PyInstaller builds."""
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled)
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    return resource_dir().joinpath(*parts)


def data_dir() -> Path:
    """Writable application data directory (survives updates and restarts)."""
    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    if not location:
        location = str(Path.home() / "AppData" / "Roaming" / APP_NAME)
    directory = Path(location)
    directory.mkdir(parents=True, exist_ok=True)
    return directory

"""Recently opened .kmol files — a small persisted list the welcome screen
and File > Open Recent read from.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os

from PyQt5.QtCore import QSettings

from . import style

_KEY = "recent_files"
MAX_RECENT = 8


def list_paths():
    """Existing recent files, most recent first — missing ones dropped."""
    raw = QSettings(*style._SETTINGS).value(_KEY, [])
    if isinstance(raw, str):
        raw = [raw] if raw else []
    paths = [p for p in raw if p and os.path.isfile(p)]
    if paths != list(raw):
        _save(paths)
    return paths


def add(path):
    """Move *path* to the front of the recent list (adding it if new)."""
    path = os.path.abspath(path)
    paths = [p for p in list_paths() if p != path]
    paths.insert(0, path)
    _save(paths[:MAX_RECENT])


def remove(path):
    _save([p for p in list_paths() if p != os.path.abspath(path)])


def clear():
    _save([])


def _save(paths):
    QSettings(*style._SETTINGS).setValue(_KEY, paths)

"""khervemol.recent: the persisted list of recently opened .kmol files.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os
import tempfile

from PyQt5.QtCore import QSettings

from khervemol import recent, style


def _snapshot():
    return QSettings(*style._SETTINGS).value(recent._KEY, [])


def _restore(saved):
    QSettings(*style._SETTINGS).setValue(recent._KEY, saved)


def test_add_moves_to_front_and_dedupes():
    saved = _snapshot()
    try:
        recent.clear()
        with tempfile.NamedTemporaryFile(suffix=".kmol") as f1, \
                tempfile.NamedTemporaryFile(suffix=".kmol") as f2:
            recent.add(f1.name)
            recent.add(f2.name)
            paths = recent.list_paths()
            assert paths == [os.path.abspath(f2.name), os.path.abspath(f1.name)]
            recent.add(f1.name)             # re-opening moves it to the front
            assert recent.list_paths()[0] == os.path.abspath(f1.name)
            assert len(recent.list_paths()) == 2
    finally:
        _restore(saved)


def test_remove_and_missing_files_are_pruned():
    saved = _snapshot()
    try:
        recent.clear()
        with tempfile.NamedTemporaryFile(suffix=".kmol") as f1:
            recent.add(f1.name)
            recent.remove(f1.name)
            assert recent.list_paths() == []
            recent.add(f1.name)
        # the file is now closed/deleted -- list_paths prunes it on read
        assert recent.list_paths() == []
    finally:
        _restore(saved)


def test_list_is_capped_at_max_recent():
    saved = _snapshot()
    try:
        recent.clear()
        files = [tempfile.NamedTemporaryFile(suffix=".kmol")
                 for _ in range(recent.MAX_RECENT + 3)]
        try:
            for f in files:
                recent.add(f.name)
            assert len(recent.list_paths()) == recent.MAX_RECENT
            assert recent.list_paths()[0] == os.path.abspath(files[-1].name)
        finally:
            for f in files:
                f.close()
    finally:
        _restore(saved)

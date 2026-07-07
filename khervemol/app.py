"""Application entry: QApplication setup, crash log, Fusion style.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import faulthandler
import sys
import tempfile
from pathlib import Path

from PyQt5.QtWidgets import QApplication

CRASH_LOG = Path(tempfile.gettempdir()) / "khervemol_crash.log"


def main():
    crash_file = open(CRASH_LOG, "w")
    faulthandler.enable(file=crash_file)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("KherveMol")

    from .style import apply_style
    apply_style(app)

    from .mainwindow import MainWindow
    win = MainWindow()
    win.show()

    # A file path on the command line opens straight away.
    for arg in app.arguments()[1:]:
        if not arg.startswith("-") and Path(arg).exists():
            win.open_path(arg)
            break

    sys.exit(app.exec_())

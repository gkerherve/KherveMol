"""The start screen: a wallpaper behind quick actions and the recently
opened files, shown in place of the workspace until a molecule is on
screen.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os
from datetime import datetime

from PyQt5.QtCore import QPointF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QLinearGradient, QPainter
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMenu, QPushButton,
                             QSizePolicy, QVBoxLayout, QWidget)

from . import icons, recent, style


class _Wallpaper(QWidget):
    """The teal gradient backdrop, with a few soft translucent atoms
    drifting across it for texture — repainted from the active theme's
    tokens so it never fights whichever colour scheme is chosen."""

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = style.tokens()
        w, h = self.width(), self.height()
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0.0, QColor(t["window"]))
        g.setColorAt(1.0, QColor(t["chrome"]))
        p.fillRect(self.rect(), g)
        accent = QColor(t["select"])
        accent.setAlpha(22)
        p.setPen(Qt.NoPen)
        p.setBrush(accent)
        for cx, cy, r in ((0.12, 0.18, 0.11), (0.88, 0.80, 0.16),
                          (0.92, 0.10, 0.06), (0.06, 0.88, 0.08),
                          (0.50, 0.94, 0.05)):
            p.drawEllipse(QPointF(cx * w, cy * h), r * w, r * w)
        p.end()


def _divider():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Plain)
    return line


def _row_subtitle(path):
    folder = os.path.basename(os.path.dirname(path)) or path
    try:
        when = datetime.fromtimestamp(os.path.getmtime(path)).strftime(
            "%b %d, %Y")
    except OSError:
        return folder
    return f"{folder} — {when}"


class _RecentRow(QFrame):
    """One clickable recent-file row: name, folder + modified date."""

    chosen = pyqtSignal(str)
    forgotten = pyqtSignal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.setObjectName("welcomeRecentRow")
        self.setCursor(Qt.PointingHandCursor)
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 10, 6)
        mark = QLabel()
        mark.setPixmap(icons.icon("mdi.molecule").pixmap(20, 20))
        row.addWidget(mark)
        text = QVBoxLayout()
        text.setSpacing(0)
        name = QLabel(os.path.basename(path))
        name.setStyleSheet("font-weight: 600; background: transparent;")
        text.addWidget(name)
        sub = QLabel(_row_subtitle(path))
        sub.setStyleSheet("color: palette(mid); font-size: 11px; "
                          "background: transparent;")
        text.addWidget(sub)
        row.addLayout(text, 1)
        self.restyle()

    def restyle(self):
        t = style.tokens()
        self.setStyleSheet(
            f"QFrame#welcomeRecentRow {{ border-radius: 6px; }}"
            f"QFrame#welcomeRecentRow:hover {{ background: {t['hover']}; }}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.chosen.emit(self.path)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        m = QMenu(self)
        m.addAction("Open", lambda: self.chosen.emit(self.path))
        m.addAction("Remove from Recent Files",
                    lambda: self.forgotten.emit(self.path))
        m.exec_(event.globalPos())


class WelcomeScreen(QWidget):
    """Shown at startup (and from File > Start Screen) in place of the
    workspace: the KMol mark, New / Open / Browse actions, and the
    recently opened files. `MainWindow` switches away from it the moment
    a molecule lands in the 3D view."""

    new_requested = pyqtSignal()
    open_requested = pyqtSignal()
    browse_requested = pyqtSignal()
    path_chosen = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._wallpaper = _Wallpaper()
        outer.addWidget(self._wallpaper)

        wl = QVBoxLayout(self._wallpaper)
        wl.setAlignment(Qt.AlignCenter)

        self._card = QFrame()
        self._card.setObjectName("welcomeCard")
        self._card.setMaximumWidth(560)
        self._card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        cl = QVBoxLayout(self._card)
        cl.setContentsMargins(36, 32, 36, 32)
        cl.setSpacing(14)

        head = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(icons.app_icon().pixmap(64, 64))
        head.addWidget(mark)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("KherveMol")
        title.setStyleSheet("font-size: 22px; font-weight: 700; "
                            "background: transparent;")
        titles.addWidget(title)
        subtitle = QLabel("Molecules and crystals, in 3D and 2D.")
        subtitle.setStyleSheet("color: palette(mid); background: transparent;")
        titles.addWidget(subtitle)
        head.addLayout(titles, 1)
        cl.addLayout(head)

        actions = QHBoxLayout()
        new_btn = QPushButton(icons.icon("mdi.file-outline"), " New Molecule")
        new_btn.clicked.connect(self.new_requested)
        open_btn = QPushButton(icons.icon("mdi.folder-open"), " Open…")
        open_btn.clicked.connect(self.open_requested)
        browse_btn = QPushButton(icons.icon("mdi.magnify"), " Browse Library…")
        browse_btn.clicked.connect(self.browse_requested)
        for b in (new_btn, open_btn, browse_btn):
            b.setMinimumHeight(34)
            actions.addWidget(b)
        cl.addLayout(actions)

        cl.addWidget(_divider())
        recent_label = QLabel("Recent")
        recent_label.setStyleSheet("font-weight: 600; color: palette(mid); "
                                   "background: transparent;")
        cl.addWidget(recent_label)

        self._empty_label = QLabel(
            "No recent files yet — open or save a molecule to see it here.")
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet("color: palette(mid); "
                                        "background: transparent;")

        self._recent_box = QVBoxLayout()
        self._recent_box.setSpacing(2)
        cl.addLayout(self._recent_box)

        wl.addWidget(self._card)
        self.restyle()
        self.refresh()

    def restyle(self):
        """Re-tint the card and its rows after a theme change."""
        t = style.tokens()
        self._card.setStyleSheet(
            f"QFrame#welcomeCard {{ background: {t['card']}; "
            f"border: 1px solid {t['border']}; border-radius: 14px; }}")
        for i in range(self._recent_box.count()):
            w = self._recent_box.itemAt(i).widget()
            if isinstance(w, _RecentRow):
                w.restyle()

    def refresh(self):
        """Reload the recent-files list from disk."""
        while self._recent_box.count():
            item = self._recent_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        paths = recent.list_paths()
        if not paths:
            self._recent_box.addWidget(self._empty_label)
            return
        for path in paths:
            row = _RecentRow(path)
            row.chosen.connect(self.path_chosen)
            row.forgotten.connect(self._forget)
            self._recent_box.addWidget(row)

    def _forget(self, path):
        recent.remove(path)
        self.refresh()

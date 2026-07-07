"""Application-wide look and feel — selectable themes.

Token-driven theming in the Kherve family style: every theme is a small
dict of colours fed into one QSS template and palette. The chosen theme
persists via QSettings (View > Theme). KherveMol's signature colour is a
laboratory teal-green.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QColor, QPalette

#: theme name -> colour tokens.
THEMES = {
    "Light": dict(
        window="#f4f5f7", chrome="#fafbfc", card="#ffffff",
        border="#e1e4e8", text="#1a1a1a", editor="#f8f9fa",
        hover="#e3eef9", pressed="#cfe3f6", select="#2176c7",
        icon="#444444", gutter="#1565c0", dark=False),
    "Dark": dict(
        window="#1e2227", chrome="#262b31", card="#2b3138",
        border="#3a4149", text="#e6e9ec", editor="#23282e",
        hover="#37404a", pressed="#415060", select="#4aa3ff",
        icon="#cfd6dd", gutter="#6ab0f3", dark=True),
    # --- The teal-green family (KherveMol's signature colour) --------------
    "Flask": dict(
        window="#e7f3ef", chrome="#d8ebe4", card="#ffffff",
        border="#bcdccf", text="#12352b", editor="#eef7f3",
        hover="#c8e6da", pressed="#aedac9", select="#159c74",
        icon="#2b6a57", gutter="#159c74", dark=False),
    "Mint": dict(
        window="#eaf6ef", chrome="#dcefe2", card="#fbfffc",
        border="#c1ddca", text="#1c3a2a", editor="#eff8f2",
        hover="#d0ecd9", pressed="#b9e0c6", select="#1f9d5b",
        icon="#356f4c", gutter="#1f9d5b", dark=False),
    "Teal": dict(
        window="#e5f2f3", chrome="#d6e9eb", card="#ffffff",
        border="#bad8db", text="#123539", editor="#edf6f7",
        hover="#c6e5e8", pressed="#aed9dd", select="#0e8f9a",
        icon="#296a71", gutter="#0e8f9a", dark=False),
    "Emerald": dict(
        window="#e3f4ea", chrome="#d3ecdd", card="#ffffff",
        border="#b6dcc4", text="#0f3524", editor="#ecf7f0",
        hover="#c6e8d3", pressed="#addfc0", select="#0a9a5a",
        icon="#256b48", gutter="#0a9a5a", dark=False),
    "Seafoam": dict(
        window="#e9f5f1", chrome="#daece6", card="#fbfffe",
        border="#bfdcd3", text="#173a32", editor="#eff8f4",
        hover="#cde9e1", pressed="#b5ddd1", select="#149080",
        icon="#2c6a5f", gutter="#149080", dark=False),
    "Slate": dict(
        window="#e8ebef", chrome="#dde2e8", card="#ffffff",
        border="#c5ccd4", text="#2e3440", editor="#f0f3f6",
        hover="#cfd9e4", pressed="#b9c8d8", select="#4a6fa5",
        icon="#4c566a", gutter="#4a6fa5", dark=False),
    "Ocean": dict(
        window="#e7f1f6", chrome="#d9e9f2", card="#ffffff",
        border="#bcd6e4", text="#173a4d", editor="#eef6fa",
        hover="#c8e2ef", pressed="#aed5e8", select="#1a6e8e",
        icon="#2a647e", gutter="#1a6e8e", dark=False),
    "Forest": dict(
        window="#eaf1ea", chrome="#dde9dd", card="#ffffff",
        border="#c3d6c3", text="#23362a", editor="#f0f6f0",
        hover="#d0e4d0", pressed="#b9d6b9", select="#2e7d4f",
        icon="#3c5a44", gutter="#2e7d4f", dark=False),
    "Graphite": dict(
        window="#26262a", chrome="#2e2e33", card="#333339",
        border="#46464d", text="#dddde2", editor="#2b2b30",
        hover="#3f3f47", pressed="#4c4c56", select="#3fb58f",
        icon="#c4c4cc", gutter="#3fb58f", dark=True),
    "Midnight": dict(
        window="#151b21", chrome="#1c242c", card="#222c35",
        border="#33414c", text="#dbe6ef", editor="#1a222a",
        hover="#2b3945", pressed="#375063", select="#39c0a6",
        icon="#c3d0dc", gutter="#39c0a6", dark=True),
    "High Contrast": dict(
        window="#ffffff", chrome="#ffffff", card="#ffffff",
        border="#000000", text="#000000", editor="#ffffff",
        hover="#dddddd", pressed="#bbbbbb", select="#008060",
        icon="#000000", gutter="#008060", dark=False),
}

DEFAULT_THEME = "Flask"
_SETTINGS = ("Kherve", "KherveMol")
_THEME_KEY = "theme_v1"
_current = DEFAULT_THEME


def _template(t: dict) -> str:
    return f"""
QMainWindow, QDialog {{ background: {t['window']}; }}
QWidget {{ color: {t['text']}; }}

QMenuBar {{ background: {t['chrome']};
            border-bottom: 1px solid {t['border']}; }}
QMenuBar::item {{ padding: 5px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: {t['hover']}; border-radius: 4px; }}
QMenu {{ background: {t['card']}; border: 1px solid {t['border']};
         padding: 4px; }}
QMenu::item {{ padding: 5px 24px 5px 12px; border-radius: 4px; }}
QMenu::item:selected {{ background: {t['hover']}; }}

QToolBar {{
    background: {t['chrome']};
    border: none;
    border-bottom: 1px solid {t['border']};
    padding: 3px 6px;
    spacing: 2px;
}}
QToolBar[orientation="vertical"] {{
    border-bottom: none;
    border-right: 1px solid {t['border']};
}}
QToolButton {{ border: none; border-radius: 6px; padding: 4px;
               margin: 1px; }}
QToolButton:hover {{ background: {t['hover']}; }}
QToolButton:pressed {{ background: {t['pressed']}; }}
QToolButton:checked {{ background: {t['pressed']}; }}
QToolButton::menu-indicator {{ image: none; width: 0; height: 0; }}

QComboBox {{
    background: {t['card']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 4px 10px;
    min-width: 70px;
}}
QComboBox:hover {{ border-color: {t['select']}; }}
QComboBox::drop-down {{ subcontrol-origin: padding;
    subcontrol-position: center right; border: none; width: 18px; }}
QComboBox::down-arrow {{
    image: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {t['icon']};
    margin-right: 6px;
}}
QComboBox::down-arrow:on {{ border-top: none;
    border-bottom: 5px solid {t['icon']}; }}
QComboBox QAbstractItemView {{ background: {t['card']};
    selection-background-color: {t['hover']};
    selection-color: {t['text']}; }}

QSpinBox, QDoubleSpinBox {{
    background: {t['card']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 3px 6px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {t['select']}; }}

QGraphicsView {{ background: {t['card']}; border: none; }}

QTabWidget::pane {{ border: 1px solid {t['border']}; border-radius: 6px;
                    top: -1px; }}
QTabBar::tab {{ background: {t['chrome']}; padding: 6px 16px;
    border: 1px solid {t['border']}; border-bottom: none;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
    margin-right: 2px; }}
QTabBar::tab:selected {{ background: {t['card']}; }}
QTabBar::tab:hover {{ background: {t['hover']}; }}

QTreeWidget, QListWidget {{ background: {t['card']};
    border: 1px solid {t['border']}; border-radius: 6px; }}
QTreeWidget::item, QListWidget::item {{ padding: 3px; border-radius: 4px; }}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background: {t['pressed']}; color: {t['text']}; }}
QHeaderView::section {{ background: {t['chrome']}; padding: 4px;
    border: none; border-bottom: 1px solid {t['border']}; }}
QDockWidget {{ titlebar-close-icon: none; }}
QDockWidget::title {{ background: {t['chrome']}; padding: 5px;
    border-bottom: 1px solid {t['border']}; }}

QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t['border']};
    border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 11px;
    margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {t['border']};
    border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; }}

QStatusBar {{ background: {t['chrome']};
              border-top: 1px solid {t['border']}; }}
QSlider::groove:horizontal {{ height: 4px; background: {t['border']};
    border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {t['select']}; width: 14px;
    margin: -6px 0; border-radius: 7px; }}

QPushButton {{ background: {t['card']}; border: 1px solid {t['border']};
    border-radius: 6px; padding: 5px 12px; }}
QPushButton:hover {{ border-color: {t['select']}; background: {t['hover']}; }}
QPushButton:pressed {{ background: {t['pressed']}; }}

QLineEdit {{
    background: {t['editor']};
    border: 1px solid {t['border']};
    border-radius: 5px;
    padding: 3px 6px;
    color: {t['text']};
}}
QLineEdit:focus {{ border-color: {t['select']}; }}
"""


def _palette(t: dict) -> QPalette:
    p = QPalette()
    p.setColor(QPalette.Window, QColor(t["window"]))
    p.setColor(QPalette.WindowText, QColor(t["text"]))
    p.setColor(QPalette.Base, QColor(t["card"]))
    p.setColor(QPalette.AlternateBase, QColor(t["chrome"]))
    p.setColor(QPalette.Text, QColor(t["text"]))
    p.setColor(QPalette.Button, QColor(t["window"]))
    p.setColor(QPalette.ButtonText, QColor(t["text"]))
    p.setColor(QPalette.ToolTipBase, QColor(t["chrome"]))
    p.setColor(QPalette.ToolTipText, QColor(t["text"]))
    p.setColor(QPalette.Highlight, QColor(t["select"]))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.PlaceholderText, QColor(t["border"]))
    return p


def current_theme() -> str:
    return _current


def tokens(name: str = None) -> dict:
    return THEMES.get(name or _current, THEMES[DEFAULT_THEME])


def saved_theme() -> str:
    name = QSettings(*_SETTINGS).value(_THEME_KEY, DEFAULT_THEME)
    return name if name in THEMES else DEFAULT_THEME


def apply_style(app, name: str = None):
    """Apply theme *name* (or the saved one at startup).

    Only an explicit *name* (a user choice from the Theme menu) is
    persisted — startup must not overwrite the saved value."""
    global _current
    _current = name or saved_theme()
    t = tokens(_current)
    app.setPalette(_palette(t))
    app.setStyleSheet(_template(t))
    if name is not None:
        QSettings(*_SETTINGS).setValue(_THEME_KEY, name)
    from . import icons
    icons.set_icon_color(t["icon"])

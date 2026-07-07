"""Toolbar icon helpers — qtawesome MDI glyphs with graceful fallback.

Same icon system as the rest of the Kherve family: themed Material Design
icons via qtawesome. When qtawesome is missing the actions fall back to
their text labels, so the app still works.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import (QColor, QFont, QFontMetricsF, QIcon, QPainter,
                         QPen, QPixmap, QPolygonF, QRadialGradient)

try:
    import qtawesome as qta
except ImportError:          # pragma: no cover - optional dependency
    qta = None

#: Glyph colour for neutral icons — set by the active theme.
DEFAULT_COLOR = "#2b6a57"

#: The app mark: a "KMol" wordmark over a ball-and-stick pair on a teal tile.
_TILE_FILL = "#c9ecdf"
_TILE_EDGE = "#8fcdb6"
_INK = "#123529"


def set_icon_color(color: str):
    """Called by style.apply_style so icons follow the theme."""
    global DEFAULT_COLOR
    DEFAULT_COLOR = color


def icon(name: str, color: str = None) -> QIcon:
    """Return the qtawesome icon *name* (e.g. "mdi.rotate-3d"), or a null
    icon if qtawesome is unavailable."""
    if qta is None:
        return QIcon()
    try:
        return qta.icon(name, color=color or DEFAULT_COLOR)
    except Exception:
        return QIcon()


def _sphere(p, cx, cy, r, body):
    """Draw a small sun-lit sphere (used by the app mark / element chips)."""
    g = QRadialGradient(QPointF(cx - r * 0.32, cy - r * 0.32), r * 1.5,
                        QPointF(cx - r * 0.42, cy - r * 0.42))
    hi = QColor(body).lighter(160)
    rim = QColor(body).darker(150)
    g.setColorAt(0.0, hi)
    g.setColorAt(1.0, rim)
    p.setBrush(g)
    p.setPen(QPen(QColor(body).darker(180), max(0.6, r * 0.12)))
    p.drawEllipse(QPointF(cx, cy), r, r)


def _paint_tile(p, s):
    """Fill the teal rounded tile; return the inner rect."""
    m = s * 0.06
    radius = s * 0.22
    rect = QRectF(m, m, s - 2 * m, s - 2 * m)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(_TILE_FILL))
    p.drawRoundedRect(rect, radius, radius)
    pen = QPen(QColor(_TILE_EDGE))
    pen.setWidthF(max(1.0, s * 0.02))
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(rect, radius, radius)
    return rect


def _paint_wordmark(p, rect, text):
    avail = rect.width() * 0.84
    font = QFont("Segoe UI")
    font.setBold(True)
    size = 1.0
    while size < rect.height():
        font.setPointSizeF(size + 0.5)
        fm = QFontMetricsF(font)
        if fm.horizontalAdvance(text) > avail or fm.height() > rect.height():
            break
        size += 0.5
    font.setPointSizeF(size)
    p.setFont(font)
    p.setPen(QColor(_INK))
    p.drawText(rect, Qt.AlignCenter, text)


def _paint_kmol(size):
    """Draw the KherveMol mark: 'KMol' above a two-atom ball-and-stick."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = float(size)
    rect = _paint_tile(p, s)
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    _paint_wordmark(p, QRectF(x, y + h * 0.06, w, h * 0.40), "KMol")
    # ball-and-stick: a bond between a carbon and an oxygen sphere.
    cy = y + h * 0.72
    r = h * 0.17
    ax, bx = x + w * 0.34, x + w * 0.66
    p.setPen(QPen(QColor("#5c6168"), max(1.5, s * 0.05)))
    p.drawLine(QPointF(ax, cy), QPointF(bx, cy))
    _sphere(p, ax, cy, r, "#3a3a3a")
    _sphere(p, bx, cy, r * 0.92, "#e01f1f")
    p.end()
    return pm


def app_icon() -> QIcon:
    """Window/taskbar icon: the 'KMol' mark on a teal tile."""
    ic = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        ic.addPixmap(_paint_kmol(size))
    return ic


def element_icon(color: str, size: int = 22) -> QIcon:
    """A little sun-lit sphere in *color* — an element chip for palettes."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    r = size * 0.40
    _sphere(p, size / 2.0, size / 2.0, r, color)
    p.end()
    return QIcon(pm)


# --------------------------------------------------------------- view cubes
_CUBE_V = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
           (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
_CUBE_F = [((1, 0, 0), (1, 2, 6, 5)), ((-1, 0, 0), (0, 4, 7, 3)),
           ((0, 1, 0), (2, 3, 7, 6)), ((0, -1, 0), (0, 1, 5, 4)),
           ((0, 0, 1), (4, 5, 6, 7)), ((0, 0, -1), (0, 3, 2, 1))]
_VIEW_NORMAL = {"front": (0, -1, 0), "back": (0, 1, 0), "left": (-1, 0, 0),
                "right": (1, 0, 0), "top": (0, 0, 1), "bottom": (0, 0, -1),
                "isometric": None}


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross3(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _unit3(a):
    n = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def view_cube_icon(view: str, size: int = 26, accent: str = "#159c74") -> QIcon:
    """A small 3D cube with the face for *view* shaded — Front/Back/Left/
    Right/Top/Bottom highlight that face; Isometric shows a plain cube."""
    target = _VIEW_NORMAL.get(view, None)
    if target is None:
        cam = _unit3((1.0, -1.0, 0.8))
    else:
        cam = _unit3(tuple(n * 1.3 if n else 0.5 for n in target))
    world_up = (0.0, 1.0, 0.0) if abs(cam[2]) > 0.94 else (0.0, 0.0, 1.0)
    right = _unit3(_cross3(world_up, cam))
    up = _unit3(_cross3(cam, right))

    def project(pt):
        return (_dot(pt, right), -_dot(pt, up), _dot(pt, cam))

    pv = [project(v) for v in _CUBE_V]
    xs = [p[0] for p in pv]
    ys = [p[1] for p in pv]
    lo, hi = min(xs + ys), max(xs + ys)
    span = (hi - lo) or 1.0
    margin = size * 0.16
    scale = (size - 2 * margin) / span

    def to_px(pt):
        return QPointF(margin + (pt[0] - lo) * scale,
                       margin + (pt[1] - lo) * scale)

    faces = []
    for normal, idx in _CUBE_F:
        if _dot(normal, cam) <= 0.01:
            continue
        depth = sum(pv[i][2] for i in idx) / 4.0
        is_target = target is not None and normal == tuple(target)
        faces.append((depth, idx, is_target))
    faces.sort(key=lambda f: f[0])

    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    edge = QPen(QColor("#33373d"))
    edge.setWidthF(max(1.0, size * 0.05))
    edge.setJoinStyle(Qt.RoundJoin)
    for _depth, idx, is_target in faces:
        poly = QPolygonF([to_px(pv[i]) for i in idx])
        p.setPen(edge)
        p.setBrush(QColor(accent) if is_target else QColor("#e6e8ec"))
        p.drawPolygon(poly)
    p.end()
    return QIcon(pm)

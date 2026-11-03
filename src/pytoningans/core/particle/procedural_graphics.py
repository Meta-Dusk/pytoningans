from __future__ import annotations

from typing import Union, Any, Optional
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPen, QPixmap, QRadialGradient, QColor


type QtColor = Union[QColor, str, Qt.GlobalColor]


class ProceduralGraphics:
    """
    Static helper class generating lightweight procedural particle textures on the fly.
    """
    _CACHE: dict[tuple, QPixmap] = {}

    @staticmethod
    def _to_qcolor(color: Union[QtColor, tuple, int]) -> QColor:
        from PySide6.QtGui import QColor
        if isinstance(color, QColor):
            return color
        return QColor(color)

    @staticmethod
    def create_dot(radius: int, color: QtColor) -> QPixmap:
        """Generates a solid anti-aliased circular dot pixmap."""
        radius = max(1, int(radius))
        qcolor: QColor = ProceduralGraphics._to_qcolor(color)
        diameter: int = radius * 2

        pixmap = QPixmap(diameter, diameter)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(qcolor)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, diameter, diameter)
        painter.end()

        return pixmap

    @staticmethod
    def create_square(size: int, color: QtColor) -> QPixmap:
        """Generates a solid square pixmap."""
        size = max(1, int(size))
        qcolor: QColor = ProceduralGraphics._to_qcolor(color)

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(0, 0, size, size, qcolor)
        painter.end()

        return pixmap

    @staticmethod
    def create_ring(radius: int, thickness: int, color: QtColor) -> QPixmap:
        """Generates an anti-aliased hollow ring pixmap."""
        radius = max(1, int(radius))
        thickness = max(1, int(thickness))
        qcolor: QColor = ProceduralGraphics._to_qcolor(color)
        diameter: int = radius * 2

        pixmap = QPixmap(diameter, diameter)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pen = QPen(qcolor, float(thickness))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        half_th: float = thickness / 2.0
        rect = QRectF(half_th, half_th, diameter - thickness, diameter - thickness)
        painter.drawEllipse(rect)
        painter.end()

        return pixmap

    @staticmethod
    def create_glow_circle(
        radius: int,
        core_color: QtColor,
        outer_color: QtColor = Qt.GlobalColor.transparent
    ) -> QPixmap:
        """Generates a radial gradient glowing circular particle texture."""
        radius = max(1, int(radius))
        core_clr: QColor = ProceduralGraphics._to_qcolor(core_color)
        outer_clr: QColor = ProceduralGraphics._to_qcolor(outer_color)
        diameter: int = radius * 2

        pixmap = QPixmap(diameter, diameter)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        center = QPointF(float(radius), float(radius))
        gradient = QRadialGradient(center, float(radius))
        gradient.setColorAt(0.0, core_clr)
        gradient.setColorAt(1.0, outer_clr)

        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, diameter, diameter)
        painter.end()

        return pixmap
    
    # FIXME: Update resolve_texture to guarantee QPixmap return or raise error if not
    @classmethod
    def resolve_texture(cls, texture: Union[QPixmap, str, tuple, Any]) -> QPixmap:
        """Resolves raw pixmaps, image paths, or procedural shape descriptors into cached QPixmaps."""
        if isinstance(texture, QPixmap):
            return texture

        if isinstance(texture, tuple) and len(texture) >= 2:
            cache_key = tuple(str(x) for x in texture)
            if cache_key in cls._CACHE:
                return cls._CACHE[cache_key]

            shape = str(texture[0]).lower()
            pixmap: Optional[QPixmap] = None

            if shape == "dot":
                pixmap = cls.create_dot(int(texture[1]), texture[2] if len(texture) > 2 else "white")
            elif shape == "square":
                pixmap = cls.create_square(int(texture[1]), texture[2] if len(texture) > 2 else "white")
            elif shape == "ring":
                pixmap = cls.create_ring(
                    int(texture[1]),
                    int(texture[2]) if len(texture) > 2 else 2,
                    texture[3] if len(texture) > 3 else "white"
                )
            elif shape in ("glow_circle", "glow"):
                pixmap = cls.create_glow_circle(
                    int(texture[1]),
                    texture[2] if len(texture) > 2 else "white",
                    texture[3] if len(texture) > 3 else "transparent"
                )

            if pixmap is not None:
                cls._CACHE[cache_key] = pixmap
                return pixmap

        if isinstance(texture, str):
            if texture.startswith("procedural:"):
                cache_key = (texture,)
                if cache_key in cls._CACHE:
                    return cls._CACHE[cache_key]

                parts = texture.split(":")
                shape = parts[1].lower() if len(parts) > 1 else "dot"
                pixmap = None

                if shape == "dot":
                    radius = int(parts[2]) if len(parts) > 2 else 6
                    color = parts[3] if len(parts) > 3 else "white"
                    pixmap = cls.create_dot(radius, color)
                elif shape == "square":
                    size = int(parts[2]) if len(parts) > 2 else 10
                    color = parts[3] if len(parts) > 3 else "white"
                    pixmap = cls.create_square(size, color)
                elif shape == "ring":
                    radius = int(parts[2]) if len(parts) > 2 else 10
                    th = int(parts[3]) if len(parts) > 3 else 2
                    color = parts[4] if len(parts) > 4 else "white"
                    pixmap = cls.create_ring(radius, th, color)
                elif shape in ("glow_circle", "glow"):
                    radius = int(parts[2]) if len(parts) > 2 else 15
                    core = parts[3] if len(parts) > 3 else "white"
                    outer = parts[4] if len(parts) > 4 else "transparent"
                    pixmap = cls.create_glow_circle(radius, core, outer)

                if pixmap is not None:
                    cls._CACHE[cache_key] = pixmap
                    return pixmap

            if Path(texture).is_file():
                return QPixmap(texture)

        return QPixmap(texture)

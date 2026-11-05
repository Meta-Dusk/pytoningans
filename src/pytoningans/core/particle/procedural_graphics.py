from __future__ import annotations

from typing import TYPE_CHECKING, Union, Optional
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPen, QPixmap, QRadialGradient, QColor

if TYPE_CHECKING:
    from .types import QtColor, TupleTextureDescriptor, PixmapTypes


class ProceduralGraphics:
    """
    Static helper class generating lightweight procedural particle textures on the fly.
    """
    _CACHE: dict[tuple, QPixmap] = {}

    @staticmethod
    def _to_qcolor(color: Union[QtColor, tuple, int]) -> QColor:
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
    
    @classmethod
    def resolve_texture(cls, texture: PixmapTypes) -> QPixmap:
        """
        Resolves raw pixmaps, image paths, or procedural shape descriptors into cached QPixmaps.\n
        
        ### Texture Mapping
        
        Passing a QPixmap will just return the same object.\n
        For generating _procedural shapes_, you can either pass it as a `tuple`,
        or a string in oneline.
        
        #### Syntax
        
        **shape** : _str_ \nChoose between: "dot, square, ring, glow_circle, or glow."
        **radius** : _int_
        **size** : _int_
        **color** : _QtColor_ \nCan be of type `QColor`, `str`, or `GlobalColor`.
        **core_color** : _QtColor_
        **outer_color** : _QtColor_
        
        #### Formatting
        
        Passing a `tuple` for the `texture` will need the first member as the **shape**.
        You can omit the rest, which will have defaults.\n
        The following possible formats are (with **shape** filled in):\n
        **("dot", radius, color)**; defaults to `radius=6, color="white"`\n
        **("square", size, color)**; defaults to `size=10, color="white"`\n
        **("ring", radius, color)**; defaults to `radius=10, color="white"`\n
        **("glow_circle" or "glow", size, core_color, outer_color)**; defaults to\n
        `size=15, core_color="white", outer_color="transparent"`\n\n
        
        An alternative is a oneline string, that is colon-separated. Except, it must start
        with 'procedural:'.\n
        `"procedural:dot:radius:color"`\n
        `"procedural:square:shape:color"`\n
        `"procedural:ring:radius:color"`\n
        `"procedural:glow_circle:radius:core_color:outer_color"`\n
        `"procedural:glow:radius:core_color:outer_color"`\n
        
        ---

        Args:
            texture (Union[QPixmap, str, tuple, Any]):
                Refer to the examples section below for what you can pass here.

        Raises:
            TypeError: If provided `texture` is unresolvable.

        Returns:
            QPixmap: The resolved `QPixmap`.
        """
        if isinstance(texture, QPixmap):
            return texture

        if isinstance(texture, tuple) and len(texture) >= 2:
            cache_key = tuple(str(x) for x in texture)
            if cache_key in cls._CACHE:
                return cls._CACHE[cache_key]

            pixmap: Optional[QPixmap] = cls._resolve_tuple_texture(texture)
            if pixmap is not None:
                cls._CACHE[cache_key] = pixmap
                return pixmap

        if isinstance(texture, str):
            if texture.startswith("procedural:"):
                cache_key = (texture,)
                if cache_key in cls._CACHE:
                    return cls._CACHE[cache_key]

                pixmap: Optional[QPixmap] = cls._resolve_procedural_texture(texture)
                if pixmap is not None:
                    cls._CACHE[cache_key] = pixmap
                    return pixmap

            if Path(texture).is_file():
                return QPixmap(texture)
        
        raise TypeError(
            "[ProceduralGraphics::resolve_texture] "
            f"Texture '{texture}' is unresolvable!"
        )

    @classmethod
    def _resolve_procedural_texture(cls, texture: str) -> Optional[QPixmap]:
        parts: list[str] = texture.split(":")
        shape: str = parts[1].lower() if len(parts) > 1 else "dot"
        match shape:
            case "dot":
                return cls.create_dot(
                    radius=int(parts[2]) if len(parts) > 2 else 6,
                    color=parts[3] if len(parts) > 3 else "white"
                )
            case "square":
                return cls.create_square(
                    size=int(parts[2]) if len(parts) > 2 else 10,
                    color=parts[3] if len(parts) > 3 else "white"
                )
            case "ring":
                return cls.create_ring(
                    radius=int(parts[2]) if len(parts) > 2 else 10,
                    thickness=int(parts[3]) if len(parts) > 3 else 2,
                    color=parts[4] if len(parts) > 4 else "white"
                )
            case "glow_circle" | "glow":
                return cls.create_glow_circle(
                    radius=int(parts[2]) if len(parts) > 2 else 15,
                    core_color=parts[3] if len(parts) > 3 else "white",
                    outer_color=parts[4] if len(parts) > 4 else "transparent"
                )
            case _:
                return None

    @classmethod
    def _resolve_tuple_texture(cls, texture: TupleTextureDescriptor) -> Optional[QPixmap]:
        shape: str = texture[0].lower()
        match shape:
            case "dot":
                return cls.create_dot(
                    radius=int(texture[1]),
                    color=texture[2] if len(texture) > 2 else "white"
                )
            case "square":
                return cls.create_square(
                    size=int(texture[1]),
                    color=texture[2] if len(texture) > 2 else "white"
                )
            case "ring":
                return cls.create_ring(
                    radius=int(texture[1]),
                    thickness=int(texture[2]) if len(texture) > 2 else 2,
                    color=texture[3] if len(texture) > 3 else "white"
                )
            case "glow_circle" | "glow":
                return cls.create_glow_circle(
                    radius=int(texture[1]),
                    core_color=texture[2] if len(texture) > 2 else "white",
                    outer_color=texture[3] if len(texture) > 3 else "transparent"
                )
            case _:
                return None

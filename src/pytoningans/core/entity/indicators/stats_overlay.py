from __future__ import annotations

import collections
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem

if TYPE_CHECKING:
    from PySide6.QtWidgets import QStyleOptionGraphicsItem, QWidget
    from ...entity_manager import EntityManager


_WIDTH: float = 180.0
_HEIGHT: float = 64.0
_PADDING: float = 10.0
_CORNER_RADIUS: float = 8.0
_UPDATE_INTERVAL_MS: int = 500   # repaint at most twice per second

_BG_COLOR = QColor(10, 10, 10, 180)
_BORDER_COLOR = QColor(255, 255, 255, 40)
_FPS_COLOR = QColor(100, 220, 100)
_TEXT_COLOR = QColor(220, 220, 220)
_WARN_COLOR = QColor(255, 180, 60)
_BAD_COLOR = QColor(255, 80, 80)

_FONT_TITLE = QFont("Pixel Code", 7, QFont.Weight.Bold)
_FONT_VALUE = QFont("Pixel Code", 10, QFont.Weight.Bold)
_FONT_LABEL = QFont("Pixel Code", 7)

_BOUNDING = QRectF(0.0, 0.0, _WIDTH, _HEIGHT)


def _fps_color(fps: float) -> QColor:
    if fps >= 50:
        return _FPS_COLOR
    if fps >= 30:
        return _WARN_COLOR
    return _BAD_COLOR


class StatsOverlayItem(QGraphicsItem):
    """A draggable, always-on-top overlay that displays FPS and entity count.

    It is designed to be added to a ``QGraphicsScene`` at a very high Z-value
    so it renders above all other scene items.  It updates its content at most
    twice per second to minimise paint overhead.
    """

    def __init__(self, entity_manager: EntityManager) -> None:
        super().__init__()
        self.entity_manager = entity_manager
        self._fps_samples: collections.deque[float] = collections.deque(maxlen=60)
        self._repaint_acc: int = 0
        self._display_fps: float = 0.0
        self._display_entities: int = 0

        self.setZValue(99_999)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, False)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setToolTip("FPS / System Stats  —  drag to reposition")

    # ------------------------------------------------------------------
    # QGraphicsItem interface
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return _BOUNDING

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem, /,
        widget: Optional[QWidget] = None
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        path = QPainterPath()
        path.addRoundedRect(_BOUNDING, _CORNER_RADIUS, _CORNER_RADIUS)
        painter.fillPath(path, _BG_COLOR)
        painter.setPen(QPen(_BORDER_COLOR, 1.0))
        painter.drawPath(path)

        fps: float = self._display_fps
        entities: int = self._display_entities

        x: float = _PADDING
        # Title row
        painter.setFont(_FONT_TITLE)
        painter.setPen(_TEXT_COLOR)
        painter.drawText(
            QRectF(x, 7, _WIDTH - x * 2, 12),
            Qt.AlignmentFlag.AlignLeft, "SYSTEM STATS"
        )

        # FPS row
        painter.setFont(_FONT_VALUE)
        painter.setPen(_fps_color(fps))
        fps_str: str = f"{fps:.1f} FPS"
        painter.drawText(
            QRectF(x, 20, _WIDTH - x * 2, 18),
            Qt.AlignmentFlag.AlignLeft, fps_str
        )

        # Entity row
        painter.setFont(_FONT_LABEL)
        painter.setPen(_TEXT_COLOR)
        painter.drawText(
            QRectF(x, 42, _WIDTH - x * 2, 14),
            Qt.AlignmentFlag.AlignLeft,
            f"Entities: {entities}",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_stats(self, dt: int) -> None:
        """
        Called every global tick with the elapsed milliseconds since last tick.
        """
        if dt > 0:
            self._fps_samples.append(1000.0 / dt)

        self._repaint_acc += dt
        if self._repaint_acc < _UPDATE_INTERVAL_MS: return
        
        self._repaint_acc = 0
        if self._fps_samples:
            self._display_fps = sum(self._fps_samples) / len(self._fps_samples)
        self._display_entities = len(self.entity_manager.active_entities)
        self.setCacheMode(QGraphicsItem.CacheMode.NoCache)   # bust cache
        self.update()
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

import random
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget


class DamageNumberItem(QGraphicsItem):
    """
    Lightweight floating combat text item.
    Rises upward with a slight spread and fades out smoothly.
    """
    def __init__(
        self, amount: int, start_pos: QPointF, is_heal: bool = False
    ) -> None:
        super().__init__()
        self.amount: int = amount
        self.is_heal: bool = is_heal
        self.start_pos: QPointF = start_pos
        self.setPos(start_pos)
        self.setZValue(10.0)

        self.lifetime: int = 700  # ms
        self.elapsed: int = 0
        self.total_rise: float = 38.0
        self.drift_x: float = random.uniform(-12.0, 12.0)

        self.text: str = f"+{self.amount}" if is_heal else f"-{self.amount}"
        self.font: QFont = QFont("Pixel Code", 11)
        self.font.setBold(True)

    def boundingRect(self) -> QRectF:
        return QRectF(-45.0, -25.0, 90.0, 50.0)

    def paint(
        self, painter: QPainter, _: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None
    ) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font)

        font_metrics = painter.fontMetrics()
        text_w: int = font_metrics.horizontalAdvance(self.text)
        text_h: int = font_metrics.capHeight()

        # Center path around local origin (0, 0)
        path = QPainterPath()
        path.addText(-text_w / 2.0, text_h / 2.0, self.font, self.text)

        # Pass 1: Draw high-contrast dark outline behind the text
        outline_pen = QPen(
            QColor(12, 12, 12, 240), 2.6,
            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin
        )
        painter.strokePath(path, outline_pen)

        # Pass 2: Draw vivid combat color on top so the number is immediately vibrant
        if self.is_heal:
            fill_color = QColor(46, 204, 113)   # Emerald green
        elif self.amount >= 25:
            fill_color = QColor(255, 65, 65)    # Critical red
        else:
            fill_color = QColor(255, 120, 45)   # Combat orange

        painter.fillPath(path, QBrush(fill_color))
        painter.restore()

    def tick(self, dt: int) -> bool:
        """
        Advances the floating animation. Returns True when expired and ready to remove.
        """
        self.elapsed += dt
        if self.elapsed >= self.lifetime:
            return True

        progress: float = min(1.0, self.elapsed / self.lifetime)

        # Smooth upward rise with deceleration
        rise_progress: float = 1.0 - ((1.0 - progress) ** 2)
        y: float = self.start_pos.y() - (self.total_rise * rise_progress)
        x: float = self.start_pos.x() + (self.drift_x * progress)
        self.setPos(x, y)

        # Initial punch scale pop: 1.25 -> 1.0 in first 15% of lifetime
        if progress < 0.15:
            scale: float = 1.25 - ((progress / 0.15) * 0.25)
            self.setScale(scale)
        else:
            self.setScale(1.0)

        # Fade out during the last 40% of lifetime
        if progress > 0.6:
            fade: float = (progress - 0.6) / 0.4
            self.setOpacity(max(0.0, 1.0 - fade))
        else:
            self.setOpacity(1.0)

        return False
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity


class HighlightOutlineItem(QGraphicsItem):
    """
    Visual highlight box drawn around an entity when its context menu is open.
    Renders an antialiased glowing rounded outline with corner brackets to clearly
    indicate which entity is targeted.
    """
    def __init__(self, parent_entity: BaseEntity) -> None:
        super().__init__(parent_entity)
        self.entity: BaseEntity = parent_entity
        self.setZValue(parent_entity.zValue() + 0.05)
        self.setVisible(False)

    def boundingRect(self) -> QRectF:
        if not self.entity:
            return QRectF()
        rect: QRectF = self.entity.boundingRect()
        return rect.adjusted(-5.0, -5.0, 5.0, 5.0)

    def paint(
        self, painter: QPainter, _: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None
    ) -> None:
        if not self.entity:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r: QRectF = self.boundingRect().adjusted(1.5, 1.5, -1.5, -1.5)

        # Soft translucent background fill
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(74, 144, 226, 30)))
        painter.drawRoundedRect(r, 6.0, 6.0)

        # Glowing cyan/blue dashed outline
        glow_pen = QPen(QColor(74, 144, 226, 210), 1.8, Qt.PenStyle.DashLine)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(r, 6.0, 6.0)

        # Corner bracket accents (crisp high-contrast white corners)
        bracket_pen = QPen(QColor(255, 255, 255, 240), 2.2, Qt.PenStyle.SolidLine)
        painter.setPen(bracket_pen)
        corner_len: float = 8.0

        # Top-left corner
        painter.drawLine(QPointF(r.left(), r.top() + corner_len), QPointF(r.left(), r.top()))
        painter.drawLine(QPointF(r.left(), r.top()), QPointF(r.left() + corner_len, r.top()))

        # Top-right corner
        painter.drawLine(QPointF(r.right() - corner_len, r.top()), QPointF(r.right(), r.top()))
        painter.drawLine(QPointF(r.right(), r.top()), QPointF(r.right(), r.top() + corner_len))

        # Bottom-left corner
        painter.drawLine(QPointF(r.left(), r.bottom() - corner_len), QPointF(r.left(), r.bottom()))
        painter.drawLine(QPointF(r.left(), r.bottom()), QPointF(r.left() + corner_len, r.bottom()))

        # Bottom-right corner
        painter.drawLine(QPointF(r.right() - corner_len, r.bottom()), QPointF(r.right(), r.bottom()))
        painter.drawLine(QPointF(r.right(), r.bottom()), QPointF(r.right(), r.bottom() - corner_len))

        painter.restore()
from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity


class DebugHitboxOverlayItem(QGraphicsItem):
    """
    Renders visual debug overlays directly over an entity in scene coordinates:
    - Physics collision hitbox (green rectangle)
    - Attack hitbox if present (red rectangle)
    - Aggro / attack range (red dashed circle)
    Zero overhead when hidden or not active.
    """

    def __init__(self, parent_entity: BaseEntity) -> None:
        super().__init__(parent_entity)
        self.entity: BaseEntity = parent_entity
        self.show_hitboxes: bool = False
        self.show_attack_range: bool = False
        self.setZValue(10.0)
        self.setVisible(False)

    def boundingRect(self) -> QRectF:
        if not self.entity or not self.isVisible():
            return QRectF()

        rects: list[QRectF] = []

        if self.show_hitboxes:
            hitbox: QRect = self.entity.current_hitbox
            if hitbox.width() > 0 and hitbox.height() > 0:
                rects.append(QRectF(hitbox))

            atk_hb: QRect = self.entity.current_attack_hitbox
            if atk_hb.width() > 0 and atk_hb.height() > 0:
                rects.append(QRectF(atk_hb))

        if self.show_attack_range:
            mod_manager = self.entity.mod_manager
            range_radius: int = mod_manager.attack_range if mod_manager is not None else 0
            if range_radius > 0:
                hitbox = self.entity.current_hitbox
                cx: float = hitbox.x() + hitbox.width() / 2.0
                cy: float = hitbox.y() + hitbox.height() / 2.0
                rects.append(QRectF(cx - range_radius, cy - range_radius, range_radius * 2, range_radius * 2))

        if not rects:
            return QRectF(self.entity.boundingRect())

        bounding: QRectF = rects[0]
        for r in rects[1:]:
            bounding = bounding.united(r)

        return bounding.adjusted(-4.0, -4.0, 4.0, 4.0)

    def paint(
        self,
        painter: QPainter,
        _: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        if not self.entity or not self.isVisible():
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Attack Range Circle
        if self.show_attack_range:
            mod_manager = self.entity.mod_manager
            range_radius: int = mod_manager.attack_range if mod_manager is not None else 0
            if range_radius > 0:
                hitbox: QRect = self.entity.current_hitbox
                cx: float = hitbox.x() + hitbox.width() / 2.0
                cy: float = hitbox.y() + hitbox.height() / 2.0
                center = QPointF(cx, cy)

                range_pen = QPen(QColor(239, 68, 68, 200), 1.5, Qt.PenStyle.DashLine)
                range_brush = QBrush(QColor(239, 68, 68, 18))
                painter.setPen(range_pen)
                painter.setBrush(range_brush)
                painter.drawEllipse(center, range_radius, range_radius)

        # Physics & Attack Hitboxes
        if self.show_hitboxes:
            # Physics Collision Hitbox (Green)
            hitbox: QRect = self.entity.current_hitbox
            if hitbox.width() > 0 and hitbox.height() > 0:
                hitbox_pen = QPen(QColor(34, 197, 94, 230), 1.6, Qt.PenStyle.SolidLine)
                hitbox_brush = QBrush(QColor(34, 197, 94, 45))
                painter.setPen(hitbox_pen)
                painter.setBrush(hitbox_brush)
                painter.drawRect(hitbox)

            # Attack Hitbox (Red)
            atk_hb: QRect = self.entity.current_attack_hitbox
            if atk_hb.width() > 0 and atk_hb.height() > 0:
                atk_hb_pen = QPen(QColor(239, 68, 68, 230), 1.6, Qt.PenStyle.SolidLine)
                atk_hb_brush = QBrush(QColor(239, 68, 68, 55))
                painter.setPen(atk_hb_pen)
                painter.setBrush(atk_hb_brush)
                painter.drawRect(atk_hb)

        painter.restore()

    def update_overlay(self) -> None:
        """Notifies the graphics scene of bounds updates and triggers repaint."""
        self.prepareGeometryChange()
        self.update()

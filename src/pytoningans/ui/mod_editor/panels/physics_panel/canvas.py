from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPaintEvent, QPainter, QColor, QMouseEvent, QPixmap, QPen, QWheelEvent
)
from PySide6.QtCore import Qt, QPoint, QRect, Signal, QPointF


class PhysicsCanvas(QWidget):
    physics_changed = Signal(QPoint, QRect, QRect, QPoint, bool)
    zoom_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)
        self.zoom: int = 4
        self.pan_offset: QPoint = QPoint(0, 0)
        self._is_panning: bool = False
        self._pan_start: QPoint = QPoint()
        self._first_load: bool = True

        self.frame_pixmap: QPixmap = QPixmap()
        self.anchor: QPoint = QPoint(0, 0)
        self.hitbox: QRect = QRect(0, 0, 0, 0)
        self.atk_hitbox: QRect = QRect(0, 0, 0, 0)
        self.is_attack_frame: bool = False
        self.hold_anchor: QPoint = QPoint(0, 0)
        self.has_hold_point: bool = False

        self._dragging_anchor: bool = False
        self._dragging_hitbox: bool = False
        self._dragging_attack: bool = False
        self._dragging_hold: bool = False
        self._drag_offset: QPoint = QPoint()

        self.attack_range: int = 0
        self.show_attack_range: bool = False

    def update_data(
        self, pixmap: QPixmap, anchor: QPoint,
        hitbox: QRect, atk_hitbox: QRect,
        hold_anchor: Optional[QPoint] = None,
        has_hold_point: bool = False,
        is_attack_frame: bool = False
    ) -> None:
        was_null: bool = self.frame_pixmap.isNull()
        self.frame_pixmap = pixmap
        self.anchor = anchor
        self.hitbox = hitbox
        self.atk_hitbox = atk_hitbox
        self.is_attack_frame = is_attack_frame
        self.hold_anchor = hold_anchor if hold_anchor is not None else QPoint(0, 0)
        self.has_hold_point = has_hold_point

        if (was_null or self._first_load) and not self.frame_pixmap.isNull():
            self._first_load = False
            self.reset_view()
        self.update()

    def reset_view(self) -> None:
        """Centers the frame pixmap in the canvas viewport."""
        if not self.frame_pixmap.isNull():
            sw: int = self.frame_pixmap.width() * self.zoom
            sh: int = self.frame_pixmap.height() * self.zoom
            self.pan_offset = QPoint((self.width() - sw) // 2, (self.height() - sh) // 2)
        else:
            self.pan_offset = QPoint(0, 0)
        self.update()

    def _to_screen(self, pt: QPoint) -> QPoint:
        return QPoint(
            pt.x() * self.zoom + self.pan_offset.x(),
            pt.y() * self.zoom + self.pan_offset.y()
        )

    def _to_screen_rect(self, rect: QRect) -> QRect:
        return QRect(
            rect.x() * self.zoom + self.pan_offset.x(),
            rect.y() * self.zoom + self.pan_offset.y(),
            rect.width() * self.zoom,
            rect.height() * self.zoom
        )

    def _to_frame(self, screen_pt: QPoint) -> QPoint:
        return QPoint(
            int((screen_pt.x() - self.pan_offset.x()) / self.zoom),
            int((screen_pt.y() - self.pan_offset.y()) / self.zoom)
        )

    def paintEvent(self, _: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().base().color())

        painter.setPen(self.palette().shadow().color())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        if self.frame_pixmap.isNull():
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Frame Loaded")
            return

        painter.setClipRect(self.rect())

        pan_x: int = self.pan_offset.x()
        pan_y: int = self.pan_offset.y()
        scaled_w: int = self.frame_pixmap.width() * self.zoom
        scaled_h: int = self.frame_pixmap.height() * self.zoom

        # Draw frame pixmap
        painter.drawPixmap(pan_x, pan_y, scaled_w, scaled_h, self.frame_pixmap)

        # Subtle frame cell outline
        painter.setPen(QPen(QColor(120, 120, 120, 120), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(pan_x, pan_y, scaled_w - 1, scaled_h - 1)

        # Hitbox (Red)
        scaled_hitbox = self._to_screen_rect(self.hitbox)
        painter.setPen(Qt.GlobalColor.red)
        painter.setBrush(QColor(255, 0, 0, 60))
        painter.drawRect(scaled_hitbox)

        # Attack Hitbox (Orange) - only when configured and marked as attack frame
        if self.is_attack_frame and not self.atk_hitbox.isNull() and self.atk_hitbox.width() > 0:
            scaled_attack = self._to_screen_rect(self.atk_hitbox)
            painter.setPen(QColor("#ffa500"))
            painter.setBrush(QColor(255, 165, 0, 80))
            painter.drawRect(scaled_attack)

        # Primary Anchor (Cyan Crosshair)
        anchor_s: QPoint = self._to_screen(self.anchor)
        ax: int = anchor_s.x()
        ay: int = anchor_s.y()
        painter.setPen(QPen(Qt.GlobalColor.cyan, 2))
        painter.drawLine(ax - 10, ay, ax + 10, ay)
        painter.drawLine(ax, ay - 10, ax, ay + 10)

        # Item Hold Anchor (Gold Crosshair)
        if self.has_hold_point:
            hold_s: QPoint = self._to_screen(self.hold_anchor)
            hx: int = hold_s.x()
            hy: int = hold_s.y()
            painter.setPen(QPen(QColor("#fbbf24"), 2))
            painter.drawLine(hx - 8, hy, hx + 8, hy)
            painter.drawLine(hx, hy - 8, hx, hy + 8)
            painter.setBrush(QColor(251, 191, 36, 120))
            painter.drawRect(hx - 3, hy - 3, 6, 6)
            painter.setPen(QColor("#fbbf24"))
            painter.setFont(self.font())
            painter.drawText(hx + 7, hy - 5, "Hold")

        # Aggro Range Circle
        if self.show_attack_range and self.attack_range > 0 and not self.hitbox.isEmpty():
            center_x: float = (self.hitbox.x() + self.hitbox.width() / 2.0) * self.zoom + pan_x
            center_y: float = (self.hitbox.y() + self.hitbox.height() / 2.0) * self.zoom + pan_y
            scaled_radius: int = self.attack_range * self.zoom

            pen = QPen(QColor(255, 50, 50, 180), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(center_x, center_y), scaled_radius, scaled_radius)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.frame_pixmap.isNull(): return

        # Middle or Right mouse button drag pans the viewport
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            click_pos: QPoint = self._to_frame(event.pos())
            click_x: int = click_pos.x()
            click_y: int = click_pos.y()

            # Priority 1: Hold anchor drag
            if self.has_hold_point and (
                abs(click_x - self.hold_anchor.x()) <= 4 and
                abs(click_y - self.hold_anchor.y()) <= 4
            ):
                self._dragging_hold = True
            # Priority 2: Standard anchor drag
            elif abs(click_x - self.anchor.x()) <= 4 and abs(click_y - self.anchor.y()) <= 4:
                self._dragging_anchor = True
            # Priority 3: Attack hitbox drag (only if attack frame)
            elif self.is_attack_frame and self.atk_hitbox.contains(click_pos):
                self._dragging_attack = True
                self._drag_offset = click_pos - self.atk_hitbox.topLeft()
            # Priority 4: Hitbox drag
            elif self.hitbox.contains(click_pos):
                self._dragging_hitbox = True
                self._drag_offset = click_pos - self.hitbox.topLeft()
            elif event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
                self._is_panning = True
                self._pan_start = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_panning:
            delta: QPoint = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.pan_offset += delta
            self.update()
            return

        if not (self._dragging_anchor or self._dragging_hitbox or self._dragging_attack or self._dragging_hold):
            return

        frame_pos: QPoint = self._to_frame(event.pos())
        new_x: int = frame_pos.x()
        new_y: int = frame_pos.y()

        if self._dragging_hold:
            self.hold_anchor = QPoint(new_x, new_y)
        elif self._dragging_anchor:
            self.anchor = QPoint(
                max(0, min(new_x, self.frame_pixmap.width())),
                max(0, min(new_y, self.frame_pixmap.height()))
            )
        elif self._dragging_attack:
            self.atk_hitbox.moveTo(new_x - self._drag_offset.x(), new_y - self._drag_offset.y())
        elif self._dragging_hitbox:
            self.hitbox.moveTo(new_x - self._drag_offset.x(), new_y - self._drag_offset.y())

        self.physics_changed.emit(self.anchor, self.hitbox, self.atk_hitbox, self.hold_anchor, self.has_hold_point)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton) or self._is_panning:
            self._is_panning = False
            self.unsetCursor()
        self._dragging_anchor = False
        self._dragging_hitbox = False
        self._dragging_attack = False
        self._dragging_hold = False

    def wheelEvent(self, event: QWheelEvent) -> None:
        angle: int = event.angleDelta().y()
        if angle == 0: return
        old_zoom: int = self.zoom
        delta: int = 1 if angle > 0 else -1
        new_zoom: int = max(1, min(20, self.zoom + delta))
        if new_zoom != old_zoom:
            cursor_pos: QPoint = event.position().toPoint()
            fx: float = (cursor_pos.x() - self.pan_offset.x()) / float(old_zoom)
            fy: float = (cursor_pos.y() - self.pan_offset.y()) / float(old_zoom)
            self.zoom = new_zoom
            self.pan_offset = QPoint(
                int(cursor_pos.x() - fx * new_zoom),
                int(cursor_pos.y() - fy * new_zoom)
            )
            self.zoom_changed.emit(self.zoom)
            self.update()

    def set_zoom(self, zoom: int) -> None:
        if self.zoom == zoom: return
        old_zoom: int = self.zoom
        center_x: float = self.width() / 2.0
        center_y: float = self.height() / 2.0
        fx: float = (center_x - self.pan_offset.x()) / float(old_zoom)
        fy: float = (center_y - self.pan_offset.y()) / float(old_zoom)
        self.zoom = zoom
        self.pan_offset = QPoint(
            int(center_x - fx * self.zoom),
            int(center_y - fy * self.zoom)
        )
        self.update()


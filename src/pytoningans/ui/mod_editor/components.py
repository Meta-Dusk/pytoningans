from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSizeGrip, QHBoxLayout, QSpinBox, QDoubleSpinBox, QFrame
)
from PySide6.QtCore import Qt, QRect, Signal, QPoint, QPointF
from PySide6.QtGui import QImage, QPaintEvent, QPainter, QPen, QColor, QMouseEvent, QWheelEvent, QPixmap, QResizeEvent

from pytoningans.ui.tool_tip import ToolTipLabel

def create_info_widget(widget: QWidget, tooltip_text: str) -> QWidget:
    combined_widget = QWidget()
    layout = QHBoxLayout(combined_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(widget)
    layout.addWidget(ToolTipLabel(text="[?]", tooltip_text=tooltip_text))
    layout.addStretch()
    return combined_widget

def create_info_label(text: str, tooltip_text: str) -> QWidget:
    return create_info_widget(QLabel(text), tooltip_text)

def create_spinbox(min_val: int, max_val: int) -> QSpinBox:
    spin = QSpinBox(); spin.setRange(min_val, max_val)
    return spin

def create_double_spinbox(
    min_val: float, max_val: float, step: float = 0.1, decimals: int = 1
) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(min_val, max_val); spin.setSingleStep(step)
    spin.setDecimals(decimals)
    return spin

class PreviewLabel(QLabel):
    """Custom label that draws debug borders, interactive cropping overlays, and supports pan/zoom."""
    
    crop_updated = Signal(int, int, int, int)
    """Emits the raw coordinates whenever the red box is dragged"""
    
    zoom_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.show_borders: bool = False
        self.show_crop: bool = False
        self.crop_rect: QRect = QRect()
        
        # Pan and Zoom variables
        self.zoom: int = 2
        self.pan_offset: QPoint = QPoint(0, 0)
        self._is_panning: bool = False
        self._pan_start: QPoint = QPoint()
        self._first_load: bool = True

        # Mouse tracking variables
        self.setMouseTracking(True) 
        self._drag_edge: str = ""
        self._drag_start_pos: QPoint = QPoint()
        self._original_rect: QRect = QRect()
        
        # Attack Range Debug
        self.show_attack_range: bool = False
        self.current_anchor: QPoint = QPoint(0, 0)
        self.attack_range: int = 0
        self.current_hitbox: QRect = QRect()

    def setPixmap(self, pixmapOrImage: QPixmap | QImage) -> None:
        super().setPixmap(pixmapOrImage)
        if (
            (self.pixmap().isNull() or self._first_load) and
            not pixmapOrImage.isNull() and self.width() > 10
        ):
            self._first_load = False
            self.reset_view()
        else:
            self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        old_h: int = event.oldSize().height()
        old_w: int = event.oldSize().width()
        super().resizeEvent(event)
        if self._first_load and not self.pixmap().isNull() and self.width() > 10:
            self._first_load = False
            self.reset_view()
        elif old_h > 0 and old_w > 0:
            dw: int = (self.width() - old_w) // 2
            dh: int = (self.height() - old_h) // 2
            self.pan_offset += QPoint(dw, dh)
            self.update()

    def reset_view(self) -> None:
        """Centers the preview pixmap in the viewport."""
        if not self.pixmap().isNull():
            sw: int = self.pixmap().width() * self.zoom
            sh: int = self.pixmap().height() * self.zoom
            self.pan_offset = QPoint((self.width() - sw) // 2, (self.height() - sh) // 2)
        else:
            self.pan_offset = QPoint(0, 0)
        self.update()

    def paintEvent(self, _: QPaintEvent) -> None:
        if self.pixmap().isNull():
            painter = QPainter(self)
            painter.fillRect(self.rect(), self.palette().base().color())
            painter.setPen(self.palette().shadow().color())
            painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Preview")
            painter.end()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.fillRect(self.rect(), self.palette().base().color())
        painter.setPen(self.palette().shadow().color())
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        painter.setClipRect(self.rect().adjusted(1, 1, -1, -1))

        px_w: int = self.pixmap().width()
        px_h: int = self.pixmap().height()
        scaled_w: int = px_w * self.zoom
        scaled_h: int = px_h * self.zoom

        pan_x: int = self.pan_offset.x()
        pan_y: int = self.pan_offset.y()

        # Draw frame pixmap scaled with nearest neighbor for crisp pixel art
        painter.drawPixmap(pan_x, pan_y, scaled_w, scaled_h, self.pixmap())

        if self.show_borders:
            painter.setPen(QPen(QColor(0, 150, 255), 2, Qt.PenStyle.DashLine))
            painter.drawRect(pan_x, pan_y, scaled_w - 1, scaled_h - 1)

        if self.show_crop and not self.crop_rect.isNull():
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine))
            cx: int = pan_x + int(self.crop_rect.x() * self.zoom)
            cy: int = pan_y + int(self.crop_rect.y() * self.zoom)
            cw: int = int(self.crop_rect.width() * self.zoom)
            ch: int = int(self.crop_rect.height() * self.zoom)

            painter.drawRect(cx, cy, cw - 1, ch - 1)

            # Dim the cropped-out areas to make the red box pop
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 120))

            crop_top_scaled: int = int(self.crop_rect.y() * self.zoom)
            crop_left_scaled: int = int(self.crop_rect.x() * self.zoom)

            # Top
            painter.drawRect(pan_x, pan_y, scaled_w, crop_top_scaled)
            # Bottom
            painter.drawRect(
                pan_x, cy + ch,
                scaled_w, max(0, scaled_h - (crop_top_scaled + ch))
            )
            # Left
            painter.drawRect(pan_x, cy, crop_left_scaled, ch)
            # Right
            painter.drawRect(
                cx + cw, cy,
                max(0, scaled_w - (crop_left_scaled + cw)), ch
            )

        if self.show_attack_range and self.attack_range > 0 and not self.current_hitbox.isEmpty():
            center_x: float = pan_x + (self.current_hitbox.x() + self.current_hitbox.width() / 2.0) * self.zoom
            center_y: float = pan_y + (self.current_hitbox.y() + self.current_hitbox.height() / 2.0) * self.zoom
            scaled_range: float = self.attack_range * self.zoom

            pen = QPen(QColor(255, 50, 50, 180), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(center_x, center_y), scaled_range, scaled_range)

        painter.end()

    # --- Interactive Mouse Controls ---
    def _get_edge_under_mouse(self, pos: QPoint) -> str:
        """Determines if the mouse is hovering over an edge, corner, or the center of the crop rect."""
        if not self.show_crop or self.crop_rect.isNull(): return ""

        cx: int = self.pan_offset.x() + int(self.crop_rect.x() * self.zoom)
        cy: int = self.pan_offset.y() + int(self.crop_rect.y() * self.zoom)
        cw: int = int(self.crop_rect.width() * self.zoom)
        ch: int = int(self.crop_rect.height() * self.zoom)
        rect = QRect(cx, cy, cw, ch)

        margin: int = 6
        edges: str = ""
        if abs(pos.y() - rect.top()) <= margin: edges += "t"
        elif abs(pos.y() - rect.bottom()) <= margin: edges += "b"

        if abs(pos.x() - rect.left()) <= margin: edges += "l"
        elif abs(pos.x() - rect.right()) <= margin: edges += "r"

        if not edges and rect.contains(pos): edges = "c" # Center drag
        return edges

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.pixmap().isNull(): return

        # Middle or Right mouse button drag pans the viewport
        if event.button() in (
            Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton
        ):
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() & (
                Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier
            ):
                self._is_panning = True
                self._pan_start = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                return

            if self.show_crop:
                self._drag_edge = self._get_edge_under_mouse(event.pos())
                if self._drag_edge:
                    self._drag_start_pos = event.pos()
                    self._original_rect = QRect(self.crop_rect)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_panning:
            delta: QPoint = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.pan_offset += delta
            self.update()
            return

        if not self.show_crop:
            self.unsetCursor()
            return

        if self._drag_edge:
            # Apply translations based on the starting drag position and zoom
            dx: int = int((event.pos().x() - self._drag_start_pos.x()) / self.zoom)
            dy: int = int((event.pos().y() - self._drag_start_pos.y()) / self.zoom)
            new_rect = QRect(self._original_rect)

            if "c" in self._drag_edge:
                new_rect.translate(dx, dy)
            else:
                if "t" in self._drag_edge: new_rect.setTop(new_rect.top() + dy)
                if "b" in self._drag_edge: new_rect.setBottom(new_rect.bottom() + dy)
                if "l" in self._drag_edge: new_rect.setLeft(new_rect.left() + dx)
                if "r" in self._drag_edge: new_rect.setRight(new_rect.right() + dx)

            # Prevent the user from collapsing the box into itself
            if new_rect.width() >= 1 and new_rect.height() >= 1:
                self.crop_rect = new_rect
                self.update() # Force instant visual refresh

                # Broadcast the new math back to the UI panel
                self.crop_updated.emit(new_rect.x(), new_rect.y(), new_rect.width(), new_rect.height())
        else:
            # Dynamically update the mouse cursor icon based on hover position
            edge: str = self._get_edge_under_mouse(event.pos())
            if edge in ("tl", "br"): self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif edge in ("tr", "bl"): self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif edge in ("t", "b"): self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif edge in ("l", "r"): self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif edge == "c": self.setCursor(Qt.CursorShape.SizeAllCursor)
            else: self.unsetCursor()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() in (
                Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton
            ) or self._is_panning
        ):
            self._is_panning = False
            self.unsetCursor()
        self._drag_edge = ""

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

class CollapsibleSection(QWidget):
    """A reusable UI component that expands and collapses its contents."""
    def __init__(self, title: str, checked: bool = False):
        super().__init__()
        self.title = title
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        
        self.btn = QPushButton(f"▼  {title}")
        self.btn.setCheckable(True)
        self.btn.setChecked(True)
        self.btn.toggled.connect(self._on_toggle)
        self.btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                font-size: 16px;
                font-family: 'Pixel Code', monospace;
                padding: 6px; background-color: rgba(150, 150, 150, 40);
                border-radius: 4px;
            }
            QPushButton:hover { background-color: rgba(150, 150, 150, 80); }
        """)
        
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(10, 10, 10, 15)
        
        layout.addWidget(self.btn)
        layout.addWidget(self.content)
        self._on_toggle(checked)
        
    def _on_toggle(self, checked: bool) -> None:
        self.content.setVisible(checked)
        self.btn.setText(f"▼  {self.title}" if checked else f"▶  {self.title}")

class CustomSizeGrip(QSizeGrip):
    """A foolproof size grip that manually paints its own diagonal lines."""
    def paintEvent(self, _: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor("#888888")) 
        pen.setWidth(2)
        painter.setPen(pen)
        
        w, h = self.width(), self.height()
        
        # Draw two diagonal lines in the bottom right corner
        painter.drawLine(w - 12, h, w, h - 12)
        painter.drawLine(w - 6, h, w, h - 6)

class VerticalResizeHandle(QFrame):
    """
    A sleek, draggable handle bar that resizes a target widget vertically.
    Supports mouse dragging to resize and double-clicking to reset to default height.
    """

    height_changed = Signal(int)

    def __init__(
        self,
        target_widget: QWidget,
        default_height: int = 200,
        min_height: int = 120,
        max_height: int = 800,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.target_widget: QWidget = target_widget
        self.default_height: int = default_height
        self.min_height: int = min_height
        self.max_height: int = max_height
        self._dragging: bool = False
        self._drag_start_y: int = 0
        self._start_height: int = default_height

        self.setFixedHeight(12)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.setToolTip("Drag up/down to resize preview height • Double-click to reset")
        self.setObjectName("VerticalResizeHandle")

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx: int = self.width() // 2
        cy: int = self.height() // 2
        is_active: bool = self.underMouse() or self._dragging
        dot_color = QColor("#89b4fa" if is_active else "#6c7086")
        painter.setBrush(dot_color)
        painter.setPen(Qt.PenStyle.NoPen)
        for offset in (-12, 0, 12):
            painter.drawEllipse(cx + offset - 2, cy - 2, 4, 4)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_y = event.globalPosition().toPoint().y()
            self._start_height = self.target_widget.height()
            self.update()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            dy: int = event.globalPosition().toPoint().y() - self._drag_start_y
            new_h: int = max(self.min_height, min(self.max_height, self._start_height + dy))
            self.target_widget.setFixedHeight(new_h)
            self.height_changed.emit(new_h)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.update()
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.target_widget.setFixedHeight(self.default_height)
            self.height_changed.emit(self.default_height)
            self.update()
            event.accept()

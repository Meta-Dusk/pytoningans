from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSizeGrip, QHBoxLayout, QSpinBox
)
from PySide6.QtCore import Qt, QRect, Signal, QPoint
from PySide6.QtGui import QPaintEvent, QPainter, QPen, QColor, QMouseEvent

from pytoningans.ui.tool_tip import ToolTipLabel

def create_info_label(text: str, tooltip_text: str) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(QLabel(text))
    layout.addWidget(ToolTipLabel(text="[?]", tooltip_text=tooltip_text))
    layout.addStretch()
    return widget

def create_info_widget(widget: QWidget, tooltip_text: str) -> QWidget:
    combined_widget = QWidget()
    layout = QHBoxLayout(combined_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(widget)
    layout.addWidget(ToolTipLabel(text="[?]", tooltip_text=tooltip_text))
    layout.addStretch()
    return combined_widget

def create_spinbox(min_val: int, max_val: int) -> QSpinBox:
    spin = QSpinBox()
    spin.setRange(min_val, max_val)
    return spin

class PreviewLabel(QLabel):
    """Custom label that draws debug borders and interactive cropping overlays."""
    
    crop_updated = Signal(int, int, int, int) 
    """Emits the raw coordinates whenever the red box is dragged"""

    def __init__(self) -> None:
        super().__init__()
        self.show_borders: bool = False
        self.show_crop: bool = False
        self.crop_rect: QRect = QRect()
        
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

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if not self.pixmap(): return
        
        painter = QPainter(self)
        px_w: int = self.pixmap().width()
        px_h: int = self.pixmap().height()
        
        offset_x: int = (self.width() - px_w) // 2
        offset_y: int = (self.height() - px_h) // 2
        
        if self.show_borders:
            painter.setPen(QPen(QColor(0, 150, 255), 2, Qt.PenStyle.DashLine))
            painter.drawRect(offset_x, offset_y, px_w - 1, px_h - 1)
            
        if self.show_crop and not self.crop_rect.isNull():
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine))
            cx: int = offset_x + self.crop_rect.x()
            cy: int = offset_y + self.crop_rect.y()
            cw: int = self.crop_rect.width()
            ch: int = self.crop_rect.height()
            
            painter.drawRect(cx, cy, cw - 1, ch - 1)
            
            # Dim the cropped-out areas to make the red box pop
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 120))
            
            # Top
            painter.drawRect(
                offset_x, offset_y,
                px_w, self.crop_rect.y()
            )
            # Bottom
            painter.drawRect(
                offset_x, offset_y + self.crop_rect.y() + ch,
                px_w, px_h - self.crop_rect.y() - ch
            )
            # Left
            painter.drawRect(
                offset_x, offset_y + self.crop_rect.y(),
                self.crop_rect.x(), ch
            )
            # Right
            painter.drawRect(
                offset_x + self.crop_rect.x() + cw, offset_y + self.crop_rect.y(),
                px_w - self.crop_rect.x() - cw, ch
            )
        
        if self.show_attack_range and self.attack_range > 0 and self.pixmap():
            # Calculate the offset to center the drawing over the pixmap
            pixmap_rect: QRect = self.pixmap().rect()
            pixmap_rect.moveCenter(self.rect().center())
            
            # Map the center of the hitbox to the UI scale
            hx: int = pixmap_rect.x() + self.current_hitbox.center().x()
            hy: int = pixmap_rect.y() + self.current_hitbox.center().y()
            
            # Draw a semi-transparent dashed red circle
            pen = QPen(QColor(255, 50, 50, 180), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPoint(hx, hy), self.attack_range, self.attack_range)
            
        painter.end()

    # --- Interactive Mouse Controls ---
    def _get_pixmap_offset(self) -> tuple[int, int]:
        if not self.pixmap(): return 0, 0
        return (self.width() - self.pixmap().width()) // 2, (self.height() - self.pixmap().height()) // 2

    def _get_edge_under_mouse(self, pos: QPoint) -> str:
        """Determines if the mouse is hovering over an edge, corner, or the center of the crop rect."""
        if not self.show_crop or self.crop_rect.isNull(): return ""
        
        ox, oy = self._get_pixmap_offset()
        rect = QRect(
            ox + self.crop_rect.x(), oy + self.crop_rect.y(),
            self.crop_rect.width(), self.crop_rect.height()
        )
        
        margin: int = 6
        edges: str = ""
        if abs(pos.y() - rect.top()) <= margin: edges += "t"
        elif abs(pos.y() - rect.bottom()) <= margin: edges += "b"
        
        if abs(pos.x() - rect.left()) <= margin: edges += "l"
        elif abs(pos.x() - rect.right()) <= margin: edges += "r"
        
        if not edges and rect.contains(pos): edges = "c" # Center drag
        return edges

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.show_crop:
            self._drag_edge = self._get_edge_under_mouse(event.pos())
            if self._drag_edge:
                self._drag_start_pos = event.pos()
                self._original_rect = QRect(self.crop_rect)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.show_crop:
            self.unsetCursor()
            return

        if self._drag_edge:
            # Apply translations based on the starting drag position
            dx: int = event.pos().x() - self._drag_start_pos.x()
            dy: int = event.pos().y() - self._drag_start_pos.y()
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
        self._drag_edge = ""

class CollapsibleSection(QWidget):
    """A reusable UI component that expands and collapses its contents."""
    def __init__(self, title: str, checked: bool = False):
        super().__init__()
        self.title = title
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
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
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSizeGrip,
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPaintEvent, QPainter, QPen, QColor

class PreviewLabel(QLabel):
    """Custom label that draws debug borders and cropping overlays."""
    def __init__(self) -> None:
        super().__init__()
        self.show_borders: bool = False
        self.show_crop: bool = False
        self.crop_rect: QRect = QRect()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if not self.pixmap(): return
        
        painter = QPainter(self)
        px_w: int = self.pixmap().width()
        px_h: int = self.pixmap().height()
        
        # QLabel AlignCenter offsets the pixmap to the middle of the widget
        offset_x: int = (self.width() - px_w) // 2
        offset_y: int = (self.height() - px_h) // 2
        
        # --- BLUE DEBUG BORDER ---
        if self.show_borders:
            painter.setPen(QPen(QColor(0, 150, 255), 2, Qt.PenStyle.DashLine))
            painter.drawRect(offset_x, offset_y, px_w - 1, px_h - 1)
            
        # --- RED CROP OVERLAY ---
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
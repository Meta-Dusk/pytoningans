from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtGui import QPainterPath, QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtCore import QRectF, Qt

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import Entity

class SpeechBubble(QGraphicsItem):
    def __init__(self, parent_entity: Entity) -> None:
        super().__init__(parent_entity)
        self.entity = parent_entity
        
        #? The text is a child item so it automatically moves with the bubble
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setDefaultTextColor(QColor("#FFFFFF"))
        
        font = QFont("Pixel Code", 11)
        self.text_item.setFont(font)
        
        self.time_left: int = 0
        self.hide()

    def speak(self, text: str, duration_ms: int = 4000) -> None:
        # Reset width to allow natural sizing
        self.text_item.setTextWidth(-1)
        self.text_item.setPlainText(text)
        
        # Configure text document alignment and margins
        doc = self.text_item.document()
        doc.setDocumentMargin(0) # Removes the default internal gap
        
        option = doc.defaultTextOption()
        option.setAlignment(Qt.AlignmentFlag.AlignCenter)
        doc.setDefaultTextOption(option)
        
        # Apply wrapping only if the text is too long
        if doc.idealWidth() > 200:
            self.text_item.setTextWidth(200)
            
        # Notify the scene that the bounding box is about to change
        self.prepareGeometryChange()
        text_rect = self.text_item.boundingRect()
        
        # Center text and distribute padding evenly
        #? (15 tail + 10 padding = 25)
        self.text_item.setPos(-text_rect.width() / 2, -text_rect.height() - 25)
        
        self.show()
        self.update_position()
        self.setZValue(1.0)
        self.time_left = duration_ms

    def boundingRect(self) -> QRectF:
        text_rect: QRectF = self.text_item.boundingRect()
        
        padding: int = 10
        width: float = text_rect.width() + (padding * 2) + 4        #? +4 for stroke width bounds
        height: float = text_rect.height() + (padding * 2) + 15 + 4 #? +15 for the tail
        
        #? The bounds encompass the text, the padding, and the tail resting at (0,0)
        return QRectF(-width / 2, -height, width, height)

    def paint(
        self, painter: QPainter, _: QStyleOptionGraphicsItem,
        /, widget: Optional[QWidget] = None
    ) -> None:
        text_rect: QRectF = self.text_item.boundingRect()
        padding: int = 10
        w: float = text_rect.width() + (padding * 2)
        h: float = text_rect.height() + (padding * 2)
        
        # Shift the main rectangle up by 15px to leave room for the tail
        x: float = -w / 2
        y: float = -h - 15 
        
        path = QPainterPath()
        path.addRoundedRect(x, y, w, h, 8, 8)
        
        # Draw the comic tail pointing exactly to local coordinate (0,0)
        path.moveTo(-8, y + h)
        path.lineTo(0, 0)
        path.lineTo(8, y + h)
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor("#2D2D2D")))
        painter.setPen(QPen(QColor("#555555"), 2))
        painter.drawPath(path)

    def tick(self, dt: int) -> None:
        if self.time_left <= 0: return
        self.time_left -= dt
        if self.time_left <= 0: self.hide()

    def update_position(self) -> None:
        if not self.isVisible(): return
        
        pet_width: float = self.entity.boundingRect().width()
        
        # Place the bubble's local (0,0) point (the tip of the tail) 
        # exactly at the top-center of the pet's sprite
        x: float = pet_width / 2
        y: float = -10
        
        self.setPos(x, y)
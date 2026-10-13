from __future__ import annotations
import math
from typing import TYPE_CHECKING, Optional

from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtGui import (
    QPainterPath, QPainter, QColor, QPen, QBrush, QFont, QTextDocument, QTextOption
)
from PySide6.QtCore import QRectF, Qt

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import Entity

class SpeechBubble(QGraphicsItem):
    """Interactive speech bubble with typewriter animation, impact shake, and interruption override."""
    def __init__(self, parent_entity: Entity) -> None:
        super().__init__(parent_entity)
        self.entity: Entity = parent_entity
        
        # Child text item moves and transforms with the speech bubble
        self.text_item: QGraphicsTextItem = QGraphicsTextItem(self)
        self.text_item.setDefaultTextColor(QColor("#FFFFFF"))
        
        font = QFont("Pixel Code", 11)
        self.text_item.setFont(font)
        
        # Target layout bounds
        self._target_w: float = 0.0
        self._target_h: float = 0.0
        self.time_left: int = 0
        
        # Typewriter animation state
        self._full_text: str = ""
        self._char_index: int = 0
        self._char_accumulator: int = 0
        self._char_delay_ms: int = 50
        self.is_typewriting: bool = False
        
        # Interruption / override state
        self._interrupt_hold_left: int = 0
        self._pending_override_text: Optional[str] = None
        self._pending_override_duration: int = 4000
        
        # Impact shake state
        self.shake_time_left: int = 0
        self.shake_duration: int = 0
        self.shake_amplitude: float = 0.0
        self._shake_offset_x: float = 0.0
        self._shake_offset_y: float = 0.0
        
        self.hide()

    def speak(self, text: str, duration_ms: int = 4000) -> None:
        """Starts displaying dialogue with typewriter animation."""
        self._interrupt_hold_left = 0
        self._pending_override_text = None
        self._full_text = text
        self._char_index = 0
        self._char_accumulator = 0
        self.time_left = duration_ms

        # Configure document and measure full text bounds
        self.text_item.setTextWidth(-1)
        self.text_item.setPlainText(text)
        
        doc: QTextDocument = self.text_item.document()
        doc.setDocumentMargin(0)
        
        option: QTextOption = doc.defaultTextOption()
        option.setAlignment(Qt.AlignmentFlag.AlignLeft)
        doc.setDefaultTextOption(option)
        
        if doc.idealWidth() > 200:
            self.text_item.setTextWidth(200)
        else:
            self.text_item.setTextWidth(doc.idealWidth())
            
        self.prepareGeometryChange()
        text_rect: QRectF = self.text_item.boundingRect()
        self._target_w = text_rect.width()
        self._target_h = text_rect.height()
        
        # Center the text item horizontally within the bubble and position above comic tail
        # (15 tail + 10 padding = 25)
        self.text_item.setPos(-self._target_w / 2.0, -self._target_h - 25.0)
        
        # Start typewriter animation
        if len(text) > 0:
            self.is_typewriting = True
            self.text_item.setPlainText("")
        else:
            self.is_typewriting = False
            self.text_item.setPlainText("")
            
        self.show()
        self.update_position()
        self.setZValue(1.0)

    def interrupt_with(self, new_text: Optional[str], duration_ms: int = 4000) -> None:
        """
        Visually cuts the ongoing dialogue with a '-' and
        transitions to new_text after a dramatic pause.
        """
        if self.is_typewriting and self._char_index < len(self._full_text):
            # Visually cut the visible dialogue text at the interrupted character
            current_visible: str = self._full_text[:self._char_index].rstrip()
            interrupted_text: str = (
                f"{current_visible}-"
                if not current_visible.endswith("-") else
                current_visible
            )
            self._full_text = interrupted_text
            self.is_typewriting = False
            
            self.text_item.setTextWidth(-1)
            self.text_item.setPlainText(interrupted_text)
            
            doc: QTextDocument = self.text_item.document()
            doc.setDocumentMargin(0)
            option: QTextOption = doc.defaultTextOption()
            option.setAlignment(Qt.AlignmentFlag.AlignLeft)
            doc.setDefaultTextOption(option)
            
            if doc.idealWidth() > 200:
                self.text_item.setTextWidth(200)
            else:
                self.text_item.setTextWidth(doc.idealWidth())
                
            self.prepareGeometryChange()
            text_rect: QRectF = self.text_item.boundingRect()
            self._target_w = text_rect.width()
            self._target_h = text_rect.height()
            self.text_item.setPos(-self._target_w / 2.0, -self._target_h - 25.0)
            
            # Violent impact shake
            self.shake(amplitude=7.0, duration_ms=400)
            
            # Pause on the interrupted text before injecting the death dialogue
            self._interrupt_hold_left = 450
            self._pending_override_text = new_text
            self._pending_override_duration = duration_ms
            self.show()
            self.update_position()
        else:
            # Typewriter was not running or was already completed
            if new_text:
                if self.isVisible():
                    self.shake(amplitude=5.0, duration_ms=250)
                self.speak(new_text, duration_ms)
            else:
                self.hide()

    def shake(self, amplitude: float = 4.0, duration_ms: int = 250) -> None:
        """Triggers a decaying directional impact shake on the speech bubble."""
        self.shake_amplitude = amplitude
        self.shake_duration = duration_ms
        self.shake_time_left = duration_ms
        self.update_position()

    def reset(self) -> None:
        """Resets all internal speech bubble state."""
        self._interrupt_hold_left = 0
        self._pending_override_text = None
        self.is_typewriting = False
        self.shake_time_left = 0
        self._shake_offset_x = 0.0
        self._shake_offset_y = 0.0
        self.time_left = 0

    def boundingRect(self) -> QRectF:
        padding: int = 10
        w: float = (self._target_w if self._target_w > 0 else self.text_item.boundingRect().width()) + (padding * 2) + 4
        height: float = (self._target_h if self._target_h > 0 else self.text_item.boundingRect().height()) + (padding * 2) + 15 + 4
        return QRectF(-w / 2.0, -height, w, height)

    def paint(
        self, painter: QPainter, _: QStyleOptionGraphicsItem,
        /, widget: Optional[QWidget] = None
    ) -> None:
        padding: int = 10
        w: float = (self._target_w if self._target_w > 0 else self.text_item.boundingRect().width()) + (padding * 2)
        h: float = (self._target_h if self._target_h > 0 else self.text_item.boundingRect().height()) + (padding * 2)
        
        # Shift the main rectangle up by 15px to leave room for the comic tail
        x: float = -w / 2.0
        y: float = -h - 15.0 
        
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
        if not self.isVisible() and self._interrupt_hold_left <= 0:
            return

        # Update impact shake
        if self.shake_time_left > 0:
            self.shake_time_left -= dt
            if self.shake_time_left <= 0:
                self._shake_offset_x = 0.0
                self._shake_offset_y = 0.0
            else:
                progress: float = 1.0 - (self.shake_time_left / max(1, self.shake_duration))
                damping: float = (1.0 - progress) ** 1.2
                self._shake_offset_x = math.sin(progress * 35.0) * self.shake_amplitude * damping
                self._shake_offset_y = math.cos(progress * 25.0) * (self.shake_amplitude * 0.4) * damping
            self.update_position()
            self.update()

        # Update interrupt hold pause
        if self._interrupt_hold_left > 0:
            self._interrupt_hold_left -= dt
            if self._interrupt_hold_left <= 0:
                if self._pending_override_text is not None:
                    text_to_speak = self._pending_override_text
                    duration = self._pending_override_duration
                    self._pending_override_text = None
                    self.speak(text_to_speak, duration)
            return

        # Update typewriter animation
        if self.is_typewriting:
            self._char_accumulator += dt
            advanced: bool = False
            while self._char_accumulator >= self._char_delay_ms and self._char_index < len(self._full_text):
                self._char_accumulator -= self._char_delay_ms
                self._char_index += 1
                advanced = True

            if advanced:
                self.text_item.setPlainText(self._full_text[:self._char_index])

            if self._char_index >= len(self._full_text):
                self.is_typewriting = False
                self._char_accumulator = 0

        # Bubble lifetime (counts down once typewriter finishes)
        else:
            if self.time_left > 0:
                self.time_left -= dt
                if self.time_left <= 0:
                    self.hide()

    def update_position(self) -> None:
        if not self.isVisible() and self._interrupt_hold_left <= 0: return
        
        pet_width: float = self.entity.boundingRect().width()
        
        # Place the bubble's local (0,0) point (the tip of the tail) 
        # above the pet's sprite, giving clearance to the health bar if visible
        x: float = pet_width / 2.0
        y: float = -10.0
        if (
            hasattr(self.entity, "health_bar")
            and self.entity.health_bar is not None
            and self.entity.health_bar.isVisible()
            and self.entity.health_bar.opacity() > 0.1
        ):
            y = -18.0
        
        self.setPos(x + self._shake_offset_x, y + self._shake_offset_y)
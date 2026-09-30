from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import QRect, Qt

if TYPE_CHECKING:
    from pytoningans.core.pet.window import PetWindow

class SpeechBubble(QWidget):
    def __init__(self, parent_pet: PetWindow) -> None:
        super().__init__()
        self.pet = parent_pet
        
        flags: Qt.WindowType = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel("")
        self.label.setObjectName("SpeechBubbleLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        self.time_left: int = 0

    def speak(self, text: str, duration_ms: int = 4000) -> None:
        self.label.setText(text)
        self.adjustSize()
        self.update_position()
        self.show()
        self.raise_()
        self.time_left = duration_ms

    def tick(self, dt: int) -> None:
        """Called by the parent pet's update_systems loop."""
        if self.time_left <= 0: return
        self.time_left -= dt
        if self.time_left <= 0: self.hide()

    def update_position(self) -> None:
        if not self.isVisible(): return
        # Anchor the bubble centered above the pet's head
        pet_geom: QRect = self.pet.geometry()
        x: int = pet_geom.center().x() - (self.width() // 2)
        y: int = pet_geom.top() - self.height() - 10
        self.move(x, y)
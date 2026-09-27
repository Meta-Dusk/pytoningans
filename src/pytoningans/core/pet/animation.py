from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTransform, QPixmap

from pytoningans.core.constants import PetState

if TYPE_CHECKING:
    from pytoningans.core.pet.window import PetWindow

class AnimationSystem:
    def __init__(self, pet: PetWindow) -> None:
        self.pet = pet
        self.current_frame = 0
        
        self.timer = QTimer(self.pet)
        self.timer.timeout.connect(self._update_frame)
        
        # Manually bootstrap the first animation using the Pet's starting state
        meta = self.pet.mod_manager.animations.get(self.pet.state)
        if meta:
            self.timer.setInterval(1000 // max(1, meta.fps))
        
        self.timer.start()
        self._update_frame()

    def set_state(self, new_state: PetState) -> None:
        """Helper to cleanly swap animation states and update speed dynamically."""
        if self.pet.state is not new_state:
            self.pet.state = new_state
            self.current_frame = 0
            
            # Fetch the new speed and update the running timer
            meta = self.pet.mod_manager.animations.get(new_state)
            if meta:
                self.timer.setInterval(1000 // max(1, meta.fps))
            self.timer.start()
            self._update_frame()

    def _update_frame(self) -> None:
        self.current_frame += 1
        frame: Optional[QPixmap] = self.pet.mod_manager.get_frame(
            self.pet.state, self.current_frame
        )

        if frame is not None:
            # Mirror the frame horizontally if facing left
            if self.pet.facing_left:
                frame = frame.transformed(QTransform().scale(-1, 1))

            self.pet.sprite_label.setPixmap(frame)
            self.pet.sprite_label.setStyleSheet("")
            self.pet.sprite_label.setText("")
            self.pet.resize(frame.width(), frame.height())
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict, Tuple
from PySide6.QtGui import QTransform, QPixmap

from pytoningans.core.constants import PetState

if TYPE_CHECKING:
    from pytoningans.core.pet.window import PetWindow

class AnimationSystem:
    def __init__(self, pet: PetWindow) -> None:
        self.pet = pet
        self.current_frame = 0
        self.time_since_last_frame = 0
        
        # Cache for flipped frames to prevent C++ memory leaks
        self._flipped_cache: Dict[Tuple[PetState, int], QPixmap] = {}
        
        # Clear the placeholder text
        self.pet.sprite_label.setStyleSheet("")
        self.pet.sprite_label.setText("")
        
        self._update_frame()

    def update(self, dt: int) -> None:
        self.time_since_last_frame += dt
        
        meta = self.pet.mod_manager.animations.get(self.pet.state)
        if not meta: return
        
        frame_duration = 1000 // max(1, meta.fps)
        
        if self.time_since_last_frame >= frame_duration:
            # Keep leftover time for perfectly smooth animations
            self.time_since_last_frame -= frame_duration 
            self._update_frame()

    def set_state(self, new_state: PetState) -> None:
        if self.pet.state is new_state: return
        self.pet.state = new_state
        self.current_frame = 0
        self.time_since_last_frame = 0
        self._update_frame()

    def _update_frame(self) -> None:
        self.current_frame += 1
        frame: Optional[QPixmap] = self.pet.mod_manager.get_frame(
            self.pet.state, self.current_frame
        )

        if frame is None: return
        # Mirror the frame horizontally if facing left
        if self.pet.facing_left:
            cache_key = (self.pet.state, self.current_frame)
            
            # Generate the flipped C++ pixmap only once and cache it
            if cache_key not in self._flipped_cache:
                self._flipped_cache[cache_key] = frame.transformed(QTransform().scale(-1, 1))
                
            frame = self._flipped_cache[cache_key]

        self.pet.sprite_label.setPixmap(frame)
        if self.pet.size() != frame.size(): self.pet.resize(frame.size())
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict, Tuple
from PySide6.QtGui import QTransform, QPixmap
from PySide6.QtCore import Qt

from pytoningans.core.constants import AnimationMeta, PetState

if TYPE_CHECKING:
    from pytoningans.core.pet.window import PetWindow

type PetTransforms = Tuple[int, PetState, int, bool, int]

class AnimationSystem:
    # Class-level cache shared by EVERY pet instance
    _shared_transform_cache: Dict[PetTransforms, QPixmap] = {}

    @classmethod
    def clear_shared_cache(cls) -> None:
        """Flushes the C++ image buffers from memory."""
        cls._shared_transform_cache.clear()
        
    def __init__(self, pet: PetWindow) -> None:
        self.pet: PetWindow = pet
        self.current_frame: int = 0
        self.time_since_last_frame: int = 0
        
        # Clear the placeholder text
        self.pet.sprite_label.setStyleSheet("")
        self.pet.sprite_label.setText("")
        
        self._update_frame()

    def update(self, dt: int) -> None:
        self.time_since_last_frame += dt
        
        meta: Optional[AnimationMeta] = self.pet.mod_manager.animations.get(self.pet.state)
        if not meta: return
        
        frame_duration: int = 1000 // max(1, meta.fps)
        
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
        frame: Optional[QPixmap] = self.pet.mod_manager.get_frame(self.pet.state, self.current_frame)
        if frame is None: return
        
        # Get raw pitch rounded to the nearest 5 degrees
        raw_angle = int(round(self.pet.rotation / 5.0) * 5.0)
        
        # Normalize to 0-359 for consistent cache keys
        normalized_angle = raw_angle % 360
        
        if self.pet.facing_left or normalized_angle != 0:
            cache_key: PetTransforms = (
                id(self.pet.mod_manager),
                self.pet.state,
                self.current_frame,
                self.pet.facing_left, normalized_angle
            )
            
            if cache_key not in self._shared_transform_cache:
                transform = QTransform()
                
                if self.pet.facing_left: transform.scale(-1, 1)
                    
                if normalized_angle != 0: transform.rotate(normalized_angle)
                    
                self._shared_transform_cache[cache_key] = frame.transformed(
                    transform, Qt.TransformationMode.SmoothTransformation
                )
            
            frame = self._shared_transform_cache[cache_key]

        self.pet.sprite_label.setPixmap(frame)
        if self.pet.size() != frame.size(): self.pet.resize(frame.size())
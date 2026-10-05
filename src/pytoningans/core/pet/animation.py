from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Tuple
from PySide6.QtGui import QTransform, QPixmap
from PySide6.QtCore import Qt, QPoint, QObject, Signal, QRect

from pytoningans.core.constants import AnimationMeta, PetState

if TYPE_CHECKING:
    from pytoningans.core.pet.window import PetWindow

type PetTransforms = Tuple[int, bool, int]

class AnimationSystem(QObject):
    attack_frame_hit = Signal()
    
    # Class-level cache shared by EVERY pet instance
    _shared_transform_cache: dict[PetTransforms, QPixmap] = {}

    @classmethod
    def clear_shared_cache(cls) -> None:
        """Flushes the C++ image buffers from memory."""
        cls._shared_transform_cache.clear()
        
    def __init__(self, pet: Optional[PetWindow] = None) -> None:
        super().__init__(pet)
        self.pet: Optional[PetWindow] = pet
        self.current_frame: int = 0
        self.time_since_last_frame: int = 0
        self._last_anchor: Optional[QPoint] = None
        
        # Clear the placeholder text
        if self.pet:
            self.pet.sprite_label.setStyleSheet("")
            self.pet.sprite_label.setText("")
        
        self._update_frame()

    def update(self, dt: int) -> None:
        self.time_since_last_frame += dt
        
        meta: Optional[AnimationMeta]
        if self.pet is None or self.pet.mod_manager is None:
            meta = None
        else:
            meta = self.pet.mod_manager.animations.get(self.pet.state)
        if not meta: return
        
        frame_duration: int = 1000 // max(1, meta.fps)
        
        if self.time_since_last_frame >= frame_duration:
            # Keep leftover time for perfectly smooth animations
            self.time_since_last_frame -= frame_duration 
            self._update_frame()

    def set_state(self, new_state: PetState) -> None:
        if self.pet is None: return
        if self.pet.state is new_state: return
        self.pet.state = new_state
        self.current_frame = 0
        self.time_since_last_frame = 0
        self._update_frame()

    def _update_frame(self) -> None:
        if self.pet is None or self.pet.mod_manager is None: return
        meta: Optional[AnimationMeta] = self.pet.mod_manager.animations.get(self.pet.state)
        if not meta: return
        
        total_play_frames: int = max(1, (meta.end_frame - meta.start_frame) + 1)
        
        if meta.loop:
            self.current_frame = (self.current_frame + 1) % total_play_frames
        else:
            self.current_frame = min(self.current_frame + 1, total_play_frames - 1)

        frame: Optional[QPixmap] = self.pet.mod_manager.get_frame(self.pet.state, self.current_frame)
        if frame is None: return

        # Extract Physics and Handle Mirroring
        raw_anchor, current_hitbox = self.pet.mod_manager.get_frame_physics(self.pet.state, self.current_frame)
        ax, ay = raw_anchor.x(), raw_anchor.y()
        
        # Extract attack hitbox from the current frame override
        mapped_index: int = (
            self.current_frame % total_play_frames
            if meta.loop else
            min(self.current_frame, total_play_frames - 1)
        )
        if meta.reverse: mapped_index = (total_play_frames - 1) - mapped_index
        frame_key: str = str(mapped_index)
        
        # Check if this specific frame is tagged as an attack frame
        atk_rect: QRect = QRect(0, 0, 0, 0)
        is_attack: bool = False
        if frame_key in meta.frame_overrides:
            overrides: dict[str, Any] = meta.frame_overrides[frame_key]
            is_attack = overrides.get("is_attack_frame", False)
            atk_rect = QRect(
                overrides.get("attack_x", 0),
                overrides.get("attack_y", 0),
                overrides.get("attack_w", 0),
                overrides.get("attack_h", 0)
            )
        
        if self.pet.facing_left:
            ax: int = frame.width() - ax
            
            flipped_hitbox_x: int = frame.width() - (current_hitbox.x() + current_hitbox.width())
            current_hitbox.moveLeft(flipped_hitbox_x)
            
            if atk_rect.width() > 0:
                flipped_atk_x = frame.width() - (atk_rect.x() + atk_rect.width())
                atk_rect.moveLeft(flipped_atk_x)
        
        self.pet.current_attack_hitbox = atk_rect

        # Calculate New Position (Do not move yet)
        new_x: int = self.pet.x()
        new_y: int = self.pet.y()
        
        if self._last_anchor is not None:
            dx: int = ax - self._last_anchor.x()
            dy: int = ay - self._last_anchor.y()
            new_x -= dx
            new_y -= dy

        self._last_anchor = QPoint(ax, ay)
        self.pet.current_hitbox = current_hitbox 
        
        # Apply Rotations and Cache
        raw_angle: int = int(round(self.pet.rotation / 5.0) * 5.0)
        normalized_angle: int = raw_angle % 360
        
        if self.pet.facing_left or normalized_angle != 0:
            cache_key: PetTransforms = (
                frame.cacheKey(),
                self.pet.facing_left, 
                normalized_angle
            )
            
            if cache_key not in self._shared_transform_cache:
                if len(self._shared_transform_cache) > 500:
                    self._shared_transform_cache.clear()

                transform = QTransform()
                if self.pet.facing_left: transform.scale(-1, 1)
                if normalized_angle != 0: transform.rotate(normalized_angle)
                    
                self._shared_transform_cache[cache_key] = frame.transformed(
                    transform, Qt.TransformationMode.SmoothTransformation
                )
            
            frame = self._shared_transform_cache[cache_key]

        self.pet.sprite_label.setPixmap(frame)
        
        # Tell the OS to update the position and dimensions in one single instruction
        current_geom: object = self.pet.geometry().getRect()
        target_geom: Tuple[int, int, int, int] = (new_x, new_y, frame.width(), frame.height())
        
        if current_geom != target_geom:
            self.pet.setGeometry(*target_geom)
        
        self.pet.sprite_label.setPixmap(frame)
        
        if is_attack: self.attack_frame_hit.emit()
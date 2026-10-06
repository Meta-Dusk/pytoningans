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
        super().__init__()
        self.pet: Optional[PetWindow] = pet
        self.current_frame: int = 0
        self.time_since_last_frame: int = 0
        self._last_anchor: Optional[QPoint] = None
        
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

        # Physics Extraction
        raw_anchor, current_hitbox = self.pet.mod_manager.get_frame_physics(self.pet.state, self.current_frame)
        ax, ay = raw_anchor.x(), raw_anchor.y()
        
        # Attack Hitbox Extraction
        mapped_index: int = (
            self.current_frame % total_play_frames
            if meta.loop else
            min(self.current_frame, total_play_frames - 1)
        )
        if meta.reverse: mapped_index = (total_play_frames - 1) - mapped_index
        frame_key: str = str(mapped_index)
        
        atk_rect = QRect(0, 0, 0, 0)
        is_attack: bool = False
        if frame_key in meta.frame_overrides:
            overrides: dict[str, Any] = meta.frame_overrides[frame_key]
            is_attack = overrides.get("is_attack_frame", False)
            atk_rect = QRect(
                overrides.get("attack_x", 0), overrides.get("attack_y", 0), 
                overrides.get("attack_w", 0), overrides.get("attack_h", 0)
            )

        # Unified Transform Mapping using the renamed sprite_rotation
        raw_angle: int = int(round(self.pet.sprite_rotation / 5.0) * 5.0)
        
        transform = QTransform()
        if self.pet.facing_left: transform.scale(-1, 1)
            
        current_anchor_pt: QPoint = transform.map(QPoint(ax, ay))
        if raw_angle != 0:
            transform.translate(current_anchor_pt.x(), current_anchor_pt.y())
            transform.rotate(raw_angle)
            transform.translate(-current_anchor_pt.x(), -current_anchor_pt.y())

        # Track exactly where the anchor and hitboxes end up in the final pixmap
        final_anchor_pt: QPoint = transform.map(QPoint(ax, ay))
        mapped_rect: QRect = transform.mapRect(frame.rect())
        
        final_ax: int = final_anchor_pt.x() - mapped_rect.x()
        final_ay: int = final_anchor_pt.y() - mapped_rect.y()
        
        mapped_hitbox: QRect = transform.mapRect(current_hitbox)
        mapped_hitbox.translate(-mapped_rect.x(), -mapped_rect.y())
        current_hitbox = mapped_hitbox
        
        if atk_rect.width() > 0:
            mapped_atk = transform.mapRect(atk_rect)
            mapped_atk.translate(-mapped_rect.x(), -mapped_rect.y())
            atk_rect = mapped_atk
            
        self.pet.current_attack_hitbox = atk_rect
        self.pet.current_hitbox = current_hitbox

        # Calculate New Item Position (Returns float in QGraphicsItem)
        new_x: float = self.pet.x()
        new_y: float = self.pet.y()
        
        if self._last_anchor is not None:
            # Shift the item perfectly based on how the anchor moved
            dx: int = final_ax - self._last_anchor.x()
            dy: int = final_ay - self._last_anchor.y()
            new_x -= dx
            new_y -= dy

        self._last_anchor = QPoint(final_ax, final_ay)

        # Apply Transform and Cache
        if self.pet.facing_left or raw_angle != 0:
            cache_key: Tuple[int, bool, int] = (frame.cacheKey(), self.pet.facing_left, raw_angle)
            if cache_key not in self._shared_transform_cache:
                if len(self._shared_transform_cache) > 500:
                    self._shared_transform_cache.clear()

                self._shared_transform_cache[cache_key] = frame.transformed(
                    transform, Qt.TransformationMode.SmoothTransformation
                )
            frame = self._shared_transform_cache[cache_key]

        # Apply Position and Pixmap to the Item
        self.pet.setPos(new_x, new_y)
        self.pet.setPixmap(frame)
        
        if is_attack: self.attack_frame_hit.emit()
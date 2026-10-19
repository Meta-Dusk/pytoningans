from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
from PySide6.QtGui import QTransform, QPixmap
from PySide6.QtCore import Qt, QPoint, QPointF, QObject, Signal, QRect

from pytoningans.core.constants import AnimationMeta, EntityState

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity
    from pytoningans.core.entity.base_item import BaseItem
    from pytoningans.core.entity.indicators import DebugHitboxOverlayItem

type _EntityTransforms = tuple[int, bool, int]

class AnimationSystem(QObject):
    attack_frame_hit = Signal()
    
    # Class-level cache shared by EVERY entity instance
    _shared_transform_cache: dict[_EntityTransforms, QPixmap] = {}

    @classmethod
    def clear_shared_cache(cls) -> None:
        """Flushes the C++ image buffers from memory."""
        cls._shared_transform_cache.clear()
        
    def __init__(self, entity: Optional[BaseEntity] = None) -> None:
        super().__init__()
        self.entity: Optional[BaseEntity] = entity
        self.current_frame: int = 0
        self.time_since_last_frame: int = 0
        self._last_anchor: Optional[QPoint] = None
        self._last_rot_offset: QPoint = QPoint(0, 0)
        
        self._update_frame(advance=False)

    def refresh_frame(self) -> None:
        """Re-applies transforms (facing_left, rotation) to the current frame without advancing."""
        self._update_frame(advance=False)

    def update(self, dt: int) -> None:
        if self.entity is not None and self.entity.is_static:
            return

        self.time_since_last_frame += dt
        
        meta: Optional[AnimationMeta]
        if self.entity is None or self.entity.mod_manager is None:
            meta = None
        else:
            meta = self.entity.mod_manager.animations.get(self.entity.state)
        if not meta: return
        
        frame_duration: int = 1000 // max(1, meta.fps)
        
        if self.time_since_last_frame >= frame_duration:
            # Keep leftover time for perfectly smooth animations
            self.time_since_last_frame -= frame_duration 
            self._update_frame(advance=True)

    def has_state(self, state: str) -> bool:
        """Returns True if the entity's mod defines an animation for the given state."""
        if self.entity is None or self.entity.mod_manager is None:
            return False
        return state in self.entity.mod_manager.animations

    def set_state(self, new_state: str) -> None:
        if self.entity is None: return
        if self.entity.state == new_state: return
        
        self.entity._state = new_state
        self.current_frame = 0
        self.time_since_last_frame = 0
        self._update_frame(advance=False)

    def _update_frame(self, advance: bool = True) -> None:
        if self.entity is None or self.entity.mod_manager is None: return
        meta: Optional[AnimationMeta] = self.entity.mod_manager.animations.get(self.entity.state)
        if not meta: return
        
        total_play_frames: int = max(1, (meta.end_frame - meta.start_frame) + 1)
        
        if advance:
            if meta.loop:
                self.current_frame = (self.current_frame + 1) % total_play_frames
            else:
                self.current_frame = min(self.current_frame + 1, total_play_frames - 1)
        else:
            if meta.loop:
                self.current_frame = self.current_frame % total_play_frames
            else:
                self.current_frame = min(self.current_frame, total_play_frames - 1)

        frame: Optional[QPixmap] = self.entity.mod_manager.get_frame(self.entity.state, self.current_frame)
        if frame is None: return

        # Physics Extraction
        raw_anchor, current_hitbox = self.entity.mod_manager.get_frame_physics(self.entity.state, self.current_frame)
        ax, ay = raw_anchor.x(), raw_anchor.y()
        hw, hh = current_hitbox.width(), current_hitbox.height()
        hb_cx: float = current_hitbox.x() + hw / 2.0
        hb_cy: float = current_hitbox.y() + hh / 2.0
        
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

        # Enforce that rotation is only allowed during active movement, interact, attack, or climbing
        if self.entity.state not in (
            EntityState.MOVING,
            EntityState.INTERACT,
            EntityState.ATTACK,
            EntityState.CLIMBING,
        ):
            self.entity.sprite_rotation = 0.0

        raw_angle: int = int(round(self.entity.sprite_rotation / 5.0) * 5.0)

        # Base transform (horizontal flip if facing left, upright)
        t_base = QTransform()
        if self.entity.facing_left:
            t_base.scale(-1, 1)

        base_m_rect: QRect = t_base.mapRect(frame.rect())
        base_center: QPointF = t_base.map(QPointF(hb_cx, hb_cy))
        base_anchor_pt: QPoint = t_base.map(QPoint(ax, ay))

        base_final_ax: int = base_anchor_pt.x() - base_m_rect.x()
        base_final_ay: int = base_anchor_pt.y() - base_m_rect.y()

        base_final_cx: float = base_center.x() - base_m_rect.x()
        base_final_cy: float = base_center.y() - base_m_rect.y()
        base_local_hb = QRect(
            int(round(base_final_cx - hw / 2.0)),
            int(round(base_final_cy - hh / 2.0)),
            hw, hh,
        )

        # Rotated transform (rotating around hitbox center)
        transform = QTransform(t_base)
        if raw_angle != 0:
            cur_cx = base_center.x()
            cur_cy = base_center.y()
            transform.translate(cur_cx, cur_cy)
            transform.rotate(raw_angle)
            transform.translate(-cur_cx, -cur_cy)

        mapped_rect: QRect = transform.mapRect(frame.rect())
        mapped_center: QPointF = transform.map(QPointF(hb_cx, hb_cy))

        final_cx: float = mapped_center.x() - mapped_rect.x()
        final_cy: float = mapped_center.y() - mapped_rect.y()

        # Place invariant, un-inflated hitbox centered at the rotated hitbox center
        current_hitbox = QRect(
            int(round(final_cx - hw / 2.0)),
            int(round(final_cy - hh / 2.0)),
            hw,
            hh,
        )
        self.entity.current_hitbox = current_hitbox

        # Attack Hitbox transformation
        if atk_rect.width() > 0 and atk_rect.height() > 0:
            atk_cx = atk_rect.x() + atk_rect.width() / 2.0
            atk_cy = atk_rect.y() + atk_rect.height() / 2.0
            mapped_atk_c = transform.map(QPointF(atk_cx, atk_cy))
            final_atk_cx = mapped_atk_c.x() - mapped_rect.x()
            final_atk_cy = mapped_atk_c.y() - mapped_rect.y()
            atk_rect = QRect(
                int(round(final_atk_cx - atk_rect.width() / 2.0)),
                int(round(final_atk_cy - atk_rect.height() / 2.0)),
                atk_rect.width(), atk_rect.height(),
            )
        self.entity.current_attack_hitbox = atk_rect

        # Item Hold Anchor Extraction and Transformation
        raw_hold: Optional[QPoint] = self.entity.mod_manager.get_frame_hold_point(
            self.entity.state, self.current_frame
        )
        if raw_hold is not None:
            final_hold_pt: QPoint = transform.map(raw_hold)
            final_hx: int = final_hold_pt.x() - mapped_rect.x()
            final_hy: int = final_hold_pt.y() - mapped_rect.y()
            self.entity.current_hold_offset = QPoint(final_hx, final_hy)
        else:
            self.entity.current_hold_offset = None

        # Calculate New Item Position (Returns float in QGraphicsItem)
        new_x: float = self.entity.x()
        new_y: float = self.entity.y()

        # Step A: Anchor shift compensation (for walk cycle sprite offsets and facing flips)
        if self._last_anchor is not None:
            dx: int = base_final_ax - self._last_anchor.x()
            dy: int = base_final_ay - self._last_anchor.y()
            new_x -= dx
            new_y -= dy
        self._last_anchor = QPoint(base_final_ax, base_final_ay)

        # Step B: Rotation compensation (keeps scene hitbox stationary when rotating)
        rot_off_x: float = float(current_hitbox.x() - base_local_hb.x())
        rot_off_y: float = float(current_hitbox.y() - base_local_hb.y())
        new_x += float(self._last_rot_offset.x()) - rot_off_x
        new_y += float(self._last_rot_offset.y()) - rot_off_y
        self._last_rot_offset = QPoint(int(rot_off_x), int(rot_off_y))

        # Apply Transform and Cache
        if self.entity.facing_left or raw_angle != 0:
            cache_key: _EntityTransforms = (frame.cacheKey(), self.entity.facing_left, raw_angle)
            if cache_key not in self._shared_transform_cache:
                if len(self._shared_transform_cache) > 500:
                    self._shared_transform_cache.clear()

                self._shared_transform_cache[cache_key] = frame.transformed(
                    transform, Qt.TransformationMode.SmoothTransformation
                )
            frame = self._shared_transform_cache[cache_key]

        # Apply Position and Pixmap to the Item
        self.entity.setPos(new_x, new_y)
        self.entity.setPixmap(frame)

        held_item: Optional[BaseItem] = getattr(self.entity, "held_item", None)
        if held_item is not None:
            held_item._update_held_position()

        # Notify visual debug overlay if visible
        debug_overlay: Optional[DebugHitboxOverlayItem] = getattr(self.entity, "_debug_overlay", None)
        if debug_overlay is not None and debug_overlay.isVisible():
            debug_overlay.update_overlay()

        if is_attack and advance: self.attack_frame_hit.emit()
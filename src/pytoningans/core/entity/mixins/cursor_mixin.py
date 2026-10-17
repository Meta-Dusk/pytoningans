from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, cast, Any

from PySide6.QtCore import QPoint, QPointF, QRect
from PySide6.QtGui import QCursor

from pytoningans.core.constants import EntityState
from pytoningans.core.api import (
    IEntity, BaseEntityBehavior, BaseBehavior
)

if TYPE_CHECKING:
    from pytoningans.core.mod_manager import ModManager
    from pytoningans.core.world import WorldOverlay
    from pytoningans.core.entity.animation import AnimationSystem
    from pytoningans.core.entity.base_entity import BaseEntity


class EntityCursorMixin:
    """Encapsulates mouse cursor following, grabbing, and struggle breakout mechanics."""

    _is_cursor_grabbed: bool
    _cursor_grab_offset: tuple[int, int]
    _cursor_grab_duration: Optional[int]
    _cursor_grab_time_left: int
    _last_synced_global_cursor: Optional[tuple[int, int]]
    _is_following_cursor: bool
    _follow_cursor_min_dist: float
    mod_manager: Optional[ModManager]
    world: Optional[WorldOverlay]
    anim_sys: Optional[AnimationSystem]
    facing_left: bool

    def _init_cursor(self) -> None:
        self._is_cursor_grabbed = False
        self._cursor_grab_offset = (0, 0)
        self._cursor_grab_duration = None
        self._cursor_grab_time_left = 0
        self._last_synced_global_cursor = None
        self._is_following_cursor = False
        self._follow_cursor_min_dist = 30.0

    @property
    def is_cursor_grabbed(self) -> bool:
        """Returns True if this entity is currently grabbing the OS mouse cursor."""
        return self._is_cursor_grabbed

    @property
    def is_following_cursor(self) -> bool:
        """Returns True if this entity is automatically pathfinding towards the mouse cursor."""
        return self._is_following_cursor

    def get_cursor_pos(self) -> tuple[float, float]:
        """Returns the current OS mouse cursor coordinates mapped into this entity's world scene space."""
        global_pos: QPoint = QCursor.pos()
        if self.world is not None and hasattr(self.world, "view"):
            local_pt = self.world.view.mapFromGlobal(global_pos)
            scene_pt = self.world.view.mapToScene(local_pt)
            return float(scene_pt.x()), float(scene_pt.y())
        return float(global_pos.x()), float(global_pos.y())

    def get_global_cursor_pos(self) -> tuple[int, int]:
        """Returns the current OS mouse cursor coordinates in virtual desktop space."""
        global_pos: QPoint = QCursor.pos()
        return global_pos.x(), global_pos.y()

    def set_cursor_pos(self, scene_x: float, scene_y: float) -> None:
        """Moves the OS mouse cursor to the specified position in this entity's world scene space."""
        if self.world is not None and hasattr(self.world, "view"):
            view_pt = self.world.view.mapFromScene(QPointF(scene_x, scene_y))
            global_pt = self.world.view.mapToGlobal(view_pt)
            QCursor.setPos(global_pt)
        else:
            QCursor.setPos(QPoint(int(round(scene_x)), int(round(scene_y))))

    def grab_cursor(
        self,
        offset_x: Optional[int] = None,
        offset_y: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """
        Grabs the OS mouse cursor, locking it to the entity's position (+ offset) as it moves.

        Args:
            offset_x: Optional X pixel offset from the entity root. If omitted, grabs at current cursor offset.
            offset_y: Optional Y pixel offset from the entity root. If omitted, grabs at current cursor offset.
            duration_ms: Optional duration in milliseconds before automatically releasing the cursor.
                         If None, stays grabbed until release_cursor() is called or the user breaks free.
        """
        if getattr(self, "is_dead", False) or getattr(self, "is_dragged", False):
            return
        cx, cy = self.get_cursor_pos()
        ox = int(round(cx - cast(Any, self).x())) if offset_x is None else offset_x
        oy = int(round(cy - cast(Any, self).y())) if offset_y is None else offset_y
        self._is_cursor_grabbed = True
        self._cursor_grab_offset = (ox, oy)
        self._cursor_grab_duration = duration_ms
        self._cursor_grab_time_left = duration_ms if duration_ms is not None else -1
        self._last_synced_global_cursor = None
        self._sync_grabbed_cursor()

        behavior: Optional[BaseBehavior] = getattr(self, "behavior", None)
        if isinstance(behavior, BaseEntityBehavior):
            try:
                behavior.on_cursor_grabbed(cast(IEntity, self))
            except Exception as e:
                print(f"Custom Behavior on_cursor_grabbed Error: {e}")

    def release_cursor(self) -> None:
        """Releases the OS mouse cursor if currently grabbed by this entity."""
        if not self._is_cursor_grabbed:
            return
        self._is_cursor_grabbed = False
        self._cursor_grab_offset = (0, 0)
        self._cursor_grab_duration = None
        self._cursor_grab_time_left = 0
        self._last_synced_global_cursor = None

        behavior: Optional[BaseBehavior] = getattr(self, "behavior", None)
        if isinstance(behavior, BaseEntityBehavior):
            try:
                behavior.on_cursor_released(cast(IEntity, self))
            except Exception as e:
                print(f"Custom Behavior on_cursor_released Error: {e}")

    def follow_cursor(self, enabled: bool = True, min_distance: float = 30.0) -> None:
        """Configures the entity to automatically follow / pathfind towards the mouse cursor."""
        self._is_following_cursor = enabled
        self._follow_cursor_min_dist = max(5.0, min_distance)
        if not enabled:
            if hasattr(self, "_target_pos"):
                self._target_pos = None
            if hasattr(self, "target_pos"):
                self.target_pos = None
            if getattr(self, "state", None) == EntityState.MOVING and self.anim_sys is not None:
                self.anim_sys.set_state(EntityState.IDLE)

    def _sync_grabbed_cursor(self) -> None:
        """Positions the OS mouse cursor at the entity's grab anchor point."""
        if not self._is_cursor_grabbed or getattr(self, "is_dead", False):
            return

        # Physical struggle / breakout check: if the user jerks their mouse away (> 120px) from where
        # it was last placed, release the cursor so users are never permanently locked.
        if self._last_synced_global_cursor is not None:
            curr_gx, curr_gy = self.get_global_cursor_pos()
            last_gx, last_gy = self._last_synced_global_cursor
            pull_dist: float = math.hypot(curr_gx - last_gx, curr_gy - last_gy)
            if pull_dist > 120.0:
                self.release_cursor()
                return

        target_scene_x: float = cast(Any, self).x() + self._cursor_grab_offset[0]
        target_scene_y: float = cast(Any, self).y() + self._cursor_grab_offset[1]
        self.set_cursor_pos(target_scene_x, target_scene_y)
        self._last_synced_global_cursor = self.get_global_cursor_pos()

    def _update_cursor_interaction(self, dt: int) -> None:
        """Ticks cursor-following pathfinding and synchronizes grabbed cursor with duration timeout."""
        # Cursor following pathfinding logic
        if (
            self._is_following_cursor and
            not self._is_cursor_grabbed and
            not getattr(self, "is_dead", False) and
            not getattr(self, "is_dragged", False) and
            not getattr(self, "is_force_idle", False)
        ):
            cx, cy = self.get_cursor_pos()
            
            from pytoningans.core.entity.physics.helpers import get_effective_hitbox
            hitbox: QRect = get_effective_hitbox(cast(Any, self))
            hitbox_center_x: float = hitbox.x() + hitbox.width() / 2.0
            hitbox_center_y: float = hitbox.y() + hitbox.height() / 2.0
            entity_center_x: float = cast(Any, self).x() + hitbox_center_x
            entity_center_y: float = cast(Any, self).y() + hitbox_center_y

            can_fly = bool(self.mod_manager is not None and getattr(self.mod_manager, "can_fly", False))
            dist: float = abs(cx - entity_center_x)
            if can_fly:
                dist = math.hypot(cx - entity_center_x, cy - entity_center_y)

            stop_dist: float = max(10.0, self._follow_cursor_min_dist)
            start_dist: float = stop_dist + max(12.0, stop_dist * 0.35)
            
            should_move: bool = dist > start_dist
            if getattr(self, "state", None) == EntityState.MOVING:
                should_move = dist > stop_dist

            if should_move:
                target_x: float = cx - hitbox_center_x
                target_y: float = cy - hitbox_center_y if can_fly else cast(Any, self).y()
                if hasattr(self, "target_pos"):
                    self.target_pos = (target_x, target_y)
                else:
                    self._target_pos = QPointF(target_x, target_y)

                if (
                    self.anim_sys is not None and
                    getattr(self, "state", None) not in (
                        EntityState.DRAG, EntityState.DYING, EntityState.CLIMBING, EntityState.ATTACK
                    ) and
                    not getattr(self, "is_climbing", False) and
                    getattr(self, "state", None) != EntityState.MOVING
                ):
                    self.anim_sys.set_state(EntityState.MOVING)
            else:
                if abs(cx - entity_center_x) > 1:
                    self.facing_left = (cx < entity_center_x)
                if getattr(self, "state", None) == EntityState.MOVING and getattr(self, "target_pos", None) is not None:
                    if hasattr(self, "target_pos"):
                        self.target_pos = None
                    else:
                        self._target_pos = None
                    if self.anim_sys is not None:
                        self.anim_sys.set_state(EntityState.IDLE)

        # Sync grabbed cursor with entity position and check timeout / breakout
        if self._is_cursor_grabbed:
            if getattr(self, "is_dead", False) or getattr(self, "is_dragged", False):
                self.release_cursor()
            elif self._cursor_grab_time_left > 0:
                self._cursor_grab_time_left -= dt
                if self._cursor_grab_time_left <= 0:
                    self.release_cursor()
                else:
                    self._sync_grabbed_cursor()
            else:
                self._sync_grabbed_cursor()


from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QPointF

from pytoningans.core.constants import EntityState
from .helpers import get_world_horizontal_range
from .window_collision import resolve_window_side_collisions

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity


def tick_movement(entity: BaseEntity, current_move_speed: float) -> None:
    """
    Computes horizontal translation towards target position 
    with window and boundary collision handling.
    """
    if (
        entity.mod_manager is None or
        entity.anim_sys is None
    ):
        return

    target_pos: Optional[QPointF] = entity.target_pos
    if entity.state != EntityState.MOVING or target_pos is None:
        return

    curr_x, curr_y = entity.x(), entity.y()
    target_x: float = float(target_pos.x())
    target_y: float = float(target_pos.y()) if entity.mod_manager.can_fly else curr_y

    dx, dy = target_x - curr_x, target_y - curr_y
    dist: float = math.hypot(dx, dy)

    if dist < max(current_move_speed, 5.0):
        entity.setPos(target_x, target_y)
        entity.target_pos = None
        entity.sprite_rotation = 0.0
        entity.anim_sys.set_state(EntityState.IDLE)
    else:
        step_x: float = curr_x + (dx / dist) * current_move_speed
        step_y: float = curr_y + (dy / dist) * current_move_speed if entity.mod_manager.can_fly else curr_y

        # Check side wall collisions against desktop windows for ground entities
        step_x, collided_side = resolve_window_side_collisions(entity, curr_x, step_x, dx)

        if not collided_side and abs(dx) > 1:
            entity.facing_left = (dx < 0)

        if entity.mod_manager.can_fly and dist > 5.0:
            entity.sprite_rotation = math.degrees(math.atan2(dy, abs(dx) if dx != 0 else 0.1))

        # Keep ground entities within world monitor horizontal boundaries
        x_range: Optional[tuple[float, float]] = get_world_horizontal_range(entity)
        if x_range is not None:
            min_step_x, max_step_x = x_range
            if step_x <= min_step_x:
                step_x = min_step_x
                entity.facing_left = False
                entity.target_pos = None
                entity.anim_sys.set_state(EntityState.IDLE)
            elif step_x >= max_step_x:
                step_x = max_step_x
                entity.facing_left = True
                entity.target_pos = None
                entity.anim_sys.set_state(EntityState.IDLE)

        entity.setPos(step_x, step_y)


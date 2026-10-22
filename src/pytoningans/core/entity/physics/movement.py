from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

from pytoningans.core.constants import EntityState
from .helpers import get_effective_hitbox, get_world_horizontal_range
from .window_collision import resolve_window_side_collisions, resolve_window_vertical_collisions

if TYPE_CHECKING:
    from PySide6.QtCore import QPointF, QRectF, QRect
    from pytoningans.core.entity.base_entity import BaseEntity


def tick_movement(entity: BaseEntity, current_move_speed: float) -> None:
    """
    Computes translation towards target position with window and boundary collision handling.
    """
    if entity.mod_manager is None or entity.anim_sys is None:
        return

    target_pos: Optional[QPointF] = entity.target_pos
    if entity.state != EntityState.MOVING or target_pos is None:
        return

    curr_x, curr_y = entity.x(), entity.y()
    target: tuple[float, float] = (
        float(target_pos.x()),
        float(target_pos.y()) if entity.mod_manager.can_fly else curr_y
    )

    dx, dy = target[0] - curr_x, target[1] - curr_y
    dist: float = math.hypot(dx, dy)

    if dist < max(current_move_speed, 5.0):
        entity.setPos(*target)
        entity.target_pos = None
        entity.sprite_rotation = 0.0
        entity.anim_sys.set_state(EntityState.IDLE)
    else:
        step_x: float = curr_x + (dx / dist) * current_move_speed
        step_y: float = (
            curr_y + (dy / dist) * current_move_speed if
            entity.mod_manager.can_fly else curr_y
        )

        # Check side wall collisions against desktop windows
        step_x, collided_side = resolve_window_side_collisions(entity, curr_x, step_x, dx)

        collided_vertical: bool = False
        if entity.mod_manager.can_fly:
            step_y, collided_vertical = resolve_window_vertical_collisions(
                entity, curr_y, step_y, dy, step_x=step_x
            )

        if not collided_side:
            if dx < -2.0:
                entity.facing_left = True
            elif dx > 2.0:
                entity.facing_left = False

        if (
            entity.mod_manager.can_fly and dist > 5.0 and
            not (collided_side or collided_vertical)
        ):
            pitch: float = math.degrees(math.atan2(dy, abs(dx) if dx != 0 else 0.1))
            entity.sprite_rotation = -pitch if entity.facing_left else pitch
        elif collided_side or collided_vertical:
            entity.sprite_rotation = 0.0

        # Keep ground entities within world monitor horizontal boundaries
        x_range: Optional[tuple[float, float]] = get_world_horizontal_range(entity)
        if x_range is not None:
            step_x = _bound_horizontally(entity, step_x, x_range)

        # Keep flying entities within world monitor vertical boundaries
        if entity.mod_manager.can_fly and entity.world is not None:
            step_y = _bound_vertically(entity, step_y)

        entity.setPos(step_x, step_y)

def _bound_vertically(entity: BaseEntity, step_y: float) -> float:
    if entity.world is None or entity.anim_sys is None:
        return step_y
    scene_rect: QRectF = entity.world.scene.sceneRect()
    hitbox: QRect = get_effective_hitbox(entity)
    min_step_y = float(scene_rect.top() - hitbox.y())
    max_step_y = float(scene_rect.bottom() - hitbox.y() - hitbox.height())
    if step_y <= min_step_y:
        step_y = min_step_y
        entity.target_pos = None
        entity.sprite_rotation = 0.0
        entity.anim_sys.set_state(EntityState.IDLE)
    elif step_y >= max_step_y:
        step_y = max_step_y
        entity.target_pos = None
        entity.sprite_rotation = 0.0
        entity.anim_sys.set_state(EntityState.IDLE)
    return step_y

def _bound_horizontally(
    entity: BaseEntity, step_x: float, x_range: tuple[float, float]
) -> float:
    if entity.anim_sys is None:
        return step_x
    min_step_x, max_step_x = x_range
    if step_x <= min_step_x:
        step_x = min_step_x
        entity.facing_left = False
        entity.target_pos = None
        entity.sprite_rotation = 0.0
        entity.anim_sys.set_state(EntityState.IDLE)
    elif step_x >= max_step_x:
        step_x = max_step_x
        entity.facing_left = True
        entity.target_pos = None
        entity.sprite_rotation = 0.0
        entity.anim_sys.set_state(EntityState.IDLE)
    return step_x

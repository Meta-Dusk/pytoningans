from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtCore import QRect

from pytoningans.core.constants import EntityState
from .helpers import get_effective_hitbox
from .window_collision import (
    resolve_window_depenetration,
    find_candidate_platforms,
    check_window_ceiling_collision,
)

if TYPE_CHECKING:
    from .system import PhysicsSystem


def tick_gravity_and_collisions(
    system: PhysicsSystem, ground_y: float, current_gravity: float
) -> None:
    """Performs vertical gravity accumulation, ceiling checks, window auto-scoop, and platform landing."""
    entity = system.entity
    if (
        entity is None or
        entity.mod_manager is None or
        entity.anim_sys is None
    ):
        return

    is_dead: bool = getattr(entity, "is_dead", False)
    if entity.mod_manager.can_fly and not is_dead:
        return

    # Check window penetration & auto-scoop
    was_handled, platform_rect = resolve_window_depenetration(entity, is_dead)
    if was_handled:
        if platform_rect is not None:
            system.current_platform_rect = platform_rect
        return

    hitbox: QRect = get_effective_hitbox(entity)
    hitbox_bottom_offset: int = hitbox.y() + hitbox.height()
    entity_bottom: float = entity.y() + hitbox_bottom_offset

    # Platform floor calculation
    effective_ground_y, matched_win = find_candidate_platforms(entity, ground_y, current_gravity)
    system.current_platform_rect = matched_win

    if entity_bottom < effective_ground_y or entity.velocity_y < 0:
        entity.velocity_y += current_gravity
        new_y: float = entity.y() + entity.velocity_y

        # Ceiling collision check
        if entity.velocity_y < 0:
            new_y, hit_ceiling = check_window_ceiling_collision(entity, new_y)
            if hit_ceiling:
                entity.velocity_y = 0.0

        # Landing collision check
        if new_y + hitbox_bottom_offset >= effective_ground_y:
            new_y = effective_ground_y - hitbox_bottom_offset
            entity.velocity_y = 0.0
            if entity.state == EntityState.JUMPING and not is_dead and entity.anim_sys is not None:
                entity.anim_sys.set_state(EntityState.IDLE)

        entity.setPos(entity.x(), new_y)
    else:
        entity.velocity_y = 0.0
        if entity_bottom > effective_ground_y:
            entity.setPos(entity.x(), effective_ground_y - hitbox_bottom_offset)
        if entity.state == EntityState.JUMPING and not is_dead and entity.anim_sys is not None:
            entity.anim_sys.set_state(EntityState.IDLE)


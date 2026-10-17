from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QRect

from pytoningans.core.constants import EntityState
from .helpers import get_effective_hitbox, get_world_horizontal_range

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity
    from pytoningans.core.entity.ai import AISystem


def resolve_window_side_collisions(
    entity: BaseEntity, curr_x: float, step_x: float, dx: float
) -> tuple[float, bool]:
    """
    Checks horizontal movement against active desktop windows for ground entities.
    Returns (adjusted_step_x, did_collide).
    """
    if (
        entity.mod_manager is None or
        entity.mod_manager.can_fly or
        entity.world is None or
        not getattr(entity, "should_use_window_physics", True)
    ):
        return step_x, False

    window_rects: list[QRect] = getattr(entity.world, "active_window_rects", [])
    if not window_rects:
        return step_x, False

    hitbox: QRect = get_effective_hitbox(entity)
    curr_left: float = curr_x + hitbox.x()
    curr_right: float = curr_left + hitbox.width()
    feet_y: float = entity.y() + hitbox.y() + hitbox.height()
    top_y: float = entity.y() + hitbox.y()

    can_climb: bool = (
        entity.mod_manager.can_climb_walls and
        entity.physics_sys is not None and
        not getattr(entity, "is_dead", False) and
        not getattr(entity, "is_dragged", False)
    )

    can_move_win: bool = (
        getattr(entity.mod_manager, "can_move_windows", False) and
        not getattr(entity, "is_dead", False) and
        not getattr(entity, "is_dragged", False)
    )
    move_mode: str = getattr(entity.mod_manager, "window_move_mode", "attack")

    for win in window_rects:
        if feet_y <= win.top() + 8 or top_y >= win.bottom() - 4:
            continue
        
        step_left: float = step_x + hitbox.x()
        step_right: float = step_left + hitbox.width()

        # Moving RIGHT: only trigger if entity was to the left of the window (entering from outside)
        if dx > 0 and curr_right <= win.left() + 6:
            if step_right < win.left(): continue
            if can_climb and entity.physics_sys is not None:
                entity.physics_sys.start_climb(win, side="left")
                return float(win.left() - hitbox.x() - hitbox.width()), True

            if can_move_win:
                if move_mode in ("push", "both"):
                    push_step: int = max(1, int(round(step_right - win.left())))
                    if entity.world.move_window(win, push_step, 0):
                        aligned_x = float(win.left() - hitbox.x() - hitbox.width())
                        return aligned_x, False
                if move_mode in ("attack", "both"):
                    if entity.anim_sys is not None and entity.anim_sys.has_state(EntityState.ATTACK):
                        ai_sys: Optional[AISystem] = getattr(entity, "ai_sys", None)
                        if ai_sys is not None and ai_sys.attack_cooldown <= 0:
                            entity.facing_left = False
                            entity.anim_sys.set_state(EntityState.ATTACK)
                            ai_sys.attack_time_left = 800
                            ai_sys.attack_cooldown = 1500
                            entity._target_pos = None
                            adjusted_x = float(win.left() - hitbox.x() - hitbox.width() - 1)
                            return adjusted_x, True

            adjusted_x = float(win.left() - hitbox.x() - hitbox.width() - 1)
            entity.facing_left = True
            entity._target_pos = None
            if entity.anim_sys is not None:
                entity.anim_sys.set_state(EntityState.IDLE)
            return adjusted_x, True

        # Moving LEFT: only trigger if entity was to the right of the window (entering from outside)
        elif dx < 0 and curr_left >= win.right() - 6:
            if step_left > win.right(): continue
            if can_climb and entity.physics_sys is not None:
                entity.physics_sys.start_climb(win, side="right")
                return float(win.right() - hitbox.x()), True

            if can_move_win and hasattr(entity.world, "move_window"):
                if move_mode in ("push", "both"):
                    push_step = min(-1, int(round(step_left - win.right())))
                    if entity.world.move_window(win, push_step, 0):
                        aligned_x = float(win.right() - hitbox.x())
                        return aligned_x, False
                if move_mode in ("attack", "both"):
                    if entity.anim_sys is not None and entity.anim_sys.has_state(EntityState.ATTACK):
                        ai_sys: Optional[AISystem] = getattr(entity, "ai_sys", None)
                        if ai_sys is not None and ai_sys.attack_cooldown <= 0:
                            entity.facing_left = True
                            entity.anim_sys.set_state(EntityState.ATTACK)
                            ai_sys.attack_time_left = 800
                            ai_sys.attack_cooldown = 1500
                            entity._target_pos = None
                            adjusted_x = float(win.right() - hitbox.x() + 1)
                            return adjusted_x, True

            adjusted_x = float(win.right() - hitbox.x() + 1)
            entity.facing_left = False
            entity._target_pos = None
            if entity.anim_sys is not None:
                entity.anim_sys.set_state(EntityState.IDLE)
            return adjusted_x, True

    return step_x, False


def resolve_window_depenetration(
    entity: BaseEntity, is_dead: bool
) -> tuple[bool, Optional[QRect]]:
    """
    Handles auto-scoop (near top edge) and lateral ejection for entities caught inside a window.
    Triggers squish death if lateral ejection pushes the entity out of the monitor boundaries.\n
    Returns `(was_handled, platform_rect_if_scooped)`.
    """
    if (
        entity.world is None or
        (entity.physics_sys and entity.physics_sys.is_climbing) or
        not getattr(entity, "should_use_window_physics", True)
    ):
        return False, None

    window_rects: list[QRect] = entity.world.active_window_rects
    if not window_rects:
        return False, None

    hitbox: QRect = get_effective_hitbox(entity)
    hitbox_bottom_offset: int = hitbox.y() + hitbox.height()
    entity_bottom: float = entity.y() + hitbox_bottom_offset
    entity_top: float = entity.y() + hitbox.y()
    entity_left: float = entity.x() + hitbox.x()
    entity_right: float = entity_left + hitbox.width()

    for win in window_rects:
        if entity_right <= win.left() + 4 or entity_left >= win.right() - 4:
            continue
        
        if entity_bottom <= win.top() + 6 or entity_top >= win.bottom() - 4:
            continue
        
        # Upper portion (<80px from top): auto-scoop onto the title bar ledge!
        if entity_top < win.top() + 80:
            scoop_y: float = float(win.top() - hitbox_bottom_offset)
            scoop_x: float = entity.x()
            x_range = get_world_horizontal_range(entity)
            if x_range is not None:
                min_x, max_x = x_range
                scoop_x = max(min_x, min(scoop_x, max_x))

            entity.setPos(scoop_x, scoop_y)
            entity.velocity_y = 0.0
            if entity.state == EntityState.JUMPING and not is_dead and entity.anim_sys is not None:
                entity.anim_sys.set_state(EntityState.IDLE)
            return True, win

        # Deep inside window: check lateral push to nearest exterior boundary
        dist_left: float = abs(entity_right - win.left())
        dist_right: float = abs(win.right() - entity_left)
        if dist_left < dist_right:
            eject_x: float = float(win.left() - hitbox.x() - hitbox.width() - 2)
            entity.facing_left = True
        else:
            eject_x: float = float(win.right() - hitbox.x() + 2)
            entity.facing_left = False

        # Check if being pushed to the side would place entity outside monitor bounds
        x_range: Optional[tuple[float, float]] = get_world_horizontal_range(entity)
        if x_range is not None:
            min_x, max_x = x_range
            if eject_x < min_x or eject_x > max_x:
                eject_x = max(min_x, min(eject_x, max_x))
                entity.setPos(eject_x, entity.y())
                entity._target_pos = None

                from pytoningans.core.entity.living_entity import Entity
                if not is_dead and isinstance(entity, Entity) and entity.mod_manager is not None:
                    death_lines: list[str] = entity.mod_manager.death_dialogue
                    if not death_lines:
                        entity.say("Squished!", duration_ms=3000, is_death=True)
                    entity.die()
                elif not is_dead and entity.anim_sys is not None:
                    entity.anim_sys.set_state(EntityState.IDLE)
                return True, None

        entity.setPos(eject_x, entity.y())
        entity._target_pos = None
        if not is_dead and entity.anim_sys is not None:
            entity.anim_sys.set_state(EntityState.IDLE)
        return True, None

    return False, None


def find_candidate_platforms(
    entity: BaseEntity, ground_y: float, current_gravity: float
) -> tuple[float, Optional[QRect]]:
    """
    Finds the highest applicable platform floor beneath or crossed by the entity during this frame.
    Returns (effective_ground_y, matched_platform_rect).
    """
    candidate_floors: list[float] = [ground_y]
    floor_to_win: dict[float, QRect] = {}

    if entity.world is not None and getattr(entity, "should_use_window_physics", True):
        window_rects: list[QRect] = getattr(entity.world, "active_window_rects", [])
        if window_rects:
            hitbox: QRect = get_effective_hitbox(entity)
            entity_bottom: float = entity.y() + hitbox.y() + hitbox.height()
            entity_left: float = entity.x() + hitbox.x()
            entity_right: float = entity_left + hitbox.width()
            fall_step: float = max(8.0, entity.velocity_y + current_gravity + 4.0)

            for win in window_rects:
                if entity_right <= win.left() + 4 or entity_left >= win.right() - 4:
                    continue
                
                win_top: float = float(win.top())
                if entity_bottom > win_top + fall_step or win_top >= ground_y:
                    continue
                
                if win_top >= entity_bottom - 12.0:
                    candidate_floors.append(win_top)
                    floor_to_win[win_top] = win

    effective_ground_y: float = min(candidate_floors)
    return effective_ground_y, floor_to_win.get(effective_ground_y, None)


def check_window_ceiling_collision(
    entity: BaseEntity, new_y: float
) -> tuple[float, bool]:
    """
    Checks if an upward moving entity hits the bottom of an active desktop window.
    Returns (adjusted_new_y, did_collide).
    """
    if (
        entity.velocity_y >= 0 or
        entity.world is None or
        not getattr(entity, "should_use_window_physics", True)
    ):
        return new_y, False

    window_rects: list[QRect] = getattr(entity.world, "active_window_rects", [])
    if not window_rects:
        return new_y, False

    hitbox: QRect = get_effective_hitbox(entity)
    entity_top: float = entity.y() + hitbox.y()
    entity_left: float = entity.x() + hitbox.x()
    entity_right: float = entity_left + hitbox.width()

    for win in window_rects:
        if entity_right <= win.left() + 4 or entity_left >= win.right() - 4:
            continue
        
        win_bottom: float = float(win.bottom())
        if (
            entity_top >= win_bottom - 6 and
            (entity_top + entity.velocity_y) <= win_bottom
        ):
            adjusted_new_y = win_bottom - hitbox.y()
            return adjusted_new_y, True

    return new_y, False


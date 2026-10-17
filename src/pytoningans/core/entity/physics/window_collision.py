from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass
from PySide6.QtCore import QRect

from pytoningans.core.constants import EntityState
from .helpers import get_effective_hitbox, get_world_horizontal_range

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity
    from pytoningans.core.entity.ai import AISystem


# =============================================================================
# Helper Functions for Side Collision Resolution
# =============================================================================

@dataclass(frozen=True, slots=True)
class _SideCollision:
    side: str
    aligned_x: float
    adjusted_x: float
    push_step: int
    atk_facing_left: bool
    block_facing_left: bool

@dataclass(frozen=True, slots=True)
class _WindowCeilingCollision:
    adjusted_new_y: float
    did_collide: bool

def _detect_side_collision(
    dx: float,
    win: QRect,
    hitbox: QRect,
    curr_left: float,
    curr_right: float,
    step_left: float,
    step_right: float,
) -> Optional[_SideCollision]:
    """
    Checks if horizontal step enters a window wall from outside.
    Returns (side, aligned_x, adjusted_x, push_step, atk_facing_left, block_facing_left) or None.
    """
    aligned_x: float = 0.0
    adjusted_x: float = 0.0
    push_step: int = 0
    # Moving RIGHT: entering window left wall from outside
    if dx > 0 and curr_right <= win.left() + 6:
        if step_right < win.left():
            return None
        aligned_x = float(win.left() - hitbox.x() - hitbox.width())
        adjusted_x = aligned_x - 1.0
        push_step = max(1, int(round(step_right - win.left())))
        return _SideCollision("left", aligned_x, adjusted_x, push_step, False, True)

    # Moving LEFT: entering window right wall from outside
    if dx < 0 and curr_left >= win.right() - 6:
        if step_left > win.right():
            return None
        aligned_x = float(win.right() - hitbox.x())
        adjusted_x = aligned_x + 1.0
        push_step = min(-1, int(round(step_left - win.right())))
        return _SideCollision("right", aligned_x, adjusted_x, push_step, True, False)

    return None


def _try_trigger_attack(entity: BaseEntity, facing_left: bool) -> bool:
    """Transitions entity to ATTACK state against a window obstacle if eligible."""
    if entity.anim_sys is None or not entity.anim_sys.has_state(EntityState.ATTACK):
        return False

    ai_sys: Optional[AISystem] = getattr(entity, "ai_sys", None)
    if ai_sys is None or ai_sys.attack_cooldown > 0:
        return False

    entity.facing_left = facing_left
    entity.anim_sys.set_state(EntityState.ATTACK)
    ai_sys.attack_time_left = 800
    ai_sys.attack_cooldown = 1500
    entity._target_pos = None
    return True


def _block_and_turn(
    entity: BaseEntity, facing_left: bool, adjusted_x: float
) -> tuple[float, bool]:
    """Stops the entity at the window wall, turns it around, and enters IDLE state."""
    entity.facing_left = facing_left
    entity._target_pos = None
    if entity.anim_sys is not None:
        entity.anim_sys.set_state(EntityState.IDLE)
    return adjusted_x, True


# =============================================================================
# Helper Functions for Depenetration Resolution
# =============================================================================

def _scoop_to_roof(
    entity: BaseEntity, win: QRect, hitbox_bottom_offset: int, is_dead: bool
) -> tuple[bool, Optional[QRect]]:
    """Auto-scoops an entity caught near the top of a window onto the roof platform."""
    scoop_y: float = float(win.top() - hitbox_bottom_offset)
    scoop_x: float = entity.x()
    x_range: Optional[tuple[float, float]] = get_world_horizontal_range(entity)
    if x_range is not None:
        min_x, max_x = x_range
        scoop_x = max(min_x, min(scoop_x, max_x))

    entity.setPos(scoop_x, scoop_y)
    entity.velocity_y = 0.0
    if entity.state == EntityState.JUMPING and not is_dead and entity.anim_sys is not None:
        entity.anim_sys.set_state(EntityState.IDLE)
    return True, win


def _trigger_squish_death(entity: BaseEntity, is_dead: bool) -> None:
    """Kills a living entity crushed against monitor boundaries by a window."""
    if is_dead:
        return
    from pytoningans.core.entity.living_entity import Entity
    if isinstance(entity, Entity) and entity.mod_manager is not None:
        death_lines: list[str] = entity.mod_manager.death_dialogue
        if not death_lines:
            entity.say("Squished!", duration_ms=3000, is_death=True)
        entity.die()
    elif entity.anim_sys is not None:
        entity.anim_sys.set_state(EntityState.IDLE)


def _eject_laterally(
    entity: BaseEntity, win: QRect, hitbox: QRect, is_dead: bool
) -> tuple[bool, Optional[QRect]]:
    """Ejects an entity caught deep inside a window to the nearest side exterior boundary."""
    entity_left: float = entity.x() + hitbox.x()
    entity_right: float = entity_left + hitbox.width()

    dist_left: float = abs(entity_right - win.left())
    dist_right: float = abs(win.right() - entity_left)

    if dist_left < dist_right:
        eject_x: float = float(win.left() - hitbox.x() - hitbox.width() - 2)
        entity.facing_left = True
    else:
        eject_x: float = float(win.right() - hitbox.x() + 2)
        entity.facing_left = False

    x_range: Optional[tuple[float, float]] = get_world_horizontal_range(entity)
    if x_range is not None:
        min_x, max_x = x_range
        if eject_x < min_x or eject_x > max_x:
            clamped_x: float = max(min_x, min(eject_x, max_x))
            entity.setPos(clamped_x, entity.y())
            entity._target_pos = None
            _trigger_squish_death(entity, is_dead)
            return True, None

    entity.setPos(eject_x, entity.y())
    entity._target_pos = None
    if not is_dead and entity.anim_sys is not None:
        entity.anim_sys.set_state(EntityState.IDLE)
    return True, None


# =============================================================================
# Primary Window Collision Handlers
# =============================================================================

def resolve_window_side_collisions(
    entity: BaseEntity, curr_x: float, step_x: float, dx: float
) -> tuple[float, bool]:
    """
    Checks horizontal movement against active desktop windows for ground entities.
    Returns (adjusted_step_x, did_collide).
    """
    if (
        dx == 0 or
        entity.mod_manager is None or
        entity.mod_manager.can_fly or
        entity.world is None or
        not entity.should_use_window_physics
    ):
        return step_x, False

    window_rects: list[QRect] = entity.world.active_window_rects
    if not window_rects: return step_x, False

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
        entity.mod_manager.can_move_windows and
        not getattr(entity, "is_dead", False) and
        not getattr(entity, "is_dragged", False)
    )
    move_mode: str = entity.mod_manager.window_move_mode

    step_left: float = step_x + hitbox.x()
    step_right: float = step_left + hitbox.width()

    for win in window_rects:
        # Ignore windows entirely if entity is strictly above or below the window
        if feet_y <= win.top() + 8 or top_y >= win.bottom() - 4:
            continue

        collision: Optional[_SideCollision] = _detect_side_collision(
            dx=dx,
            win=win,
            hitbox=hitbox,
            curr_left=curr_left,
            curr_right=curr_right,
            step_left=step_left,
            step_right=step_right,
        )
        if collision is None:
            continue

        #? Wall climbing
        if can_climb and entity.physics_sys is not None:
            entity.physics_sys.start_climb(win, side=collision.side)
            return collision.aligned_x, True

        #? Window pushing
        if can_move_win and move_mode in ("push", "both"):
            if entity.world.move_window(win, collision.push_step, 0):
                new_aligned_x = (
                    float(win.left() - hitbox.x() - hitbox.width())
                    if collision.side == "left" else
                    float(win.right() - hitbox.x())
                )
                return new_aligned_x, False

        #? Window attacking
        if can_move_win and move_mode in ("attack", "both"):
            if _try_trigger_attack(entity, collision.atk_facing_left):
                return collision.adjusted_x, True

        #? Blocked obstacle
        return _block_and_turn(entity, collision.block_facing_left, collision.adjusted_x)

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
            return _scoop_to_roof(entity, win, hitbox_bottom_offset, is_dead)

        # Deep inside window: check lateral push to nearest exterior boundary
        return _eject_laterally(entity, win, hitbox, is_dead)

    return False, None


def find_candidate_platforms(
    entity: BaseEntity, ground_y: float, current_gravity: float
) -> tuple[float, Optional[QRect]]:
    """
    Finds the highest applicable platform floor beneath or crossed by the entity during this frame.
    Returns (effective_ground_y, matched_platform_rect).
    """
    if entity.world is None or not getattr(entity, "should_use_window_physics", True):
        return ground_y, None

    window_rects: list[QRect] = getattr(entity.world, "active_window_rects", [])
    if not window_rects:
        return ground_y, None

    hitbox: QRect = get_effective_hitbox(entity)
    entity_bottom: float = entity.y() + hitbox.y() + hitbox.height()
    entity_left: float = entity.x() + hitbox.x()
    entity_right: float = entity_left + hitbox.width()
    fall_step: float = max(8.0, entity.velocity_y + current_gravity + 4.0)

    candidate_floors: list[float] = [ground_y]
    floor_to_win: dict[float, QRect] = {}

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
) -> _WindowCeilingCollision:
    """
    Checks if an upward moving entity hits the bottom of an active desktop window.
    Returns (adjusted_new_y, did_collide).
    """
    if (
        entity.velocity_y >= 0 or
        entity.world is None or
        not getattr(entity, "should_use_window_physics", True)
    ):
        return _WindowCeilingCollision(new_y, False)

    window_rects: list[QRect] = getattr(entity.world, "active_window_rects", [])
    if not window_rects:
        return _WindowCeilingCollision(new_y, False)

    hitbox: QRect = get_effective_hitbox(entity)
    entity_top: float = entity.y() + hitbox.y()
    entity_left: float = entity.x() + hitbox.x()
    entity_right: float = entity_left + hitbox.width()

    for win in window_rects:
        if entity_right <= win.left() + 4 or entity_left >= win.right() - 4:
            continue

        win_bottom: float = float(win.bottom())
        if win_bottom - 6 <= entity_top and (entity_top + entity.velocity_y) <= win_bottom:
            adjusted_new_y: float = win_bottom - hitbox.y()
            return _WindowCeilingCollision(adjusted_new_y, True)

    return _WindowCeilingCollision(new_y, False)

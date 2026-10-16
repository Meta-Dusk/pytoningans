from __future__ import annotations

from .system import PhysicsSystem
from .helpers import get_effective_hitbox, get_world_bounds, get_world_horizontal_range
from .movement import tick_movement
from .repulsion import apply_soft_repulsion
from .gravity import tick_gravity_and_collisions
from .window_collision import (
    resolve_window_side_collisions,
    resolve_window_depenetration,
    find_candidate_platforms,
    check_window_ceiling_collision,
)

__all__ = [
    "PhysicsSystem",
    "get_effective_hitbox",
    "get_world_bounds",
    "get_world_horizontal_range",
    "tick_movement",
    "apply_soft_repulsion",
    "tick_gravity_and_collisions",
    "resolve_window_side_collisions",
    "resolve_window_depenetration",
    "find_candidate_platforms",
    "check_window_ceiling_collision",
]


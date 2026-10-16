from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QPointF, QRect

from pytoningans.core.constants import EntityState
from .helpers import get_effective_hitbox

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity
    from pytoningans.core.entity.base_structure import BaseStructure
    from pytoningans.core.entity.living_entity import Entity


def apply_soft_repulsion(
    entity: BaseEntity,
    current_move_speed: float,
    centers: Optional[dict[BaseEntity, QPointF]] = None,
) -> None:
    """Gently repels overlapping entities and structures to prevent dense clustering."""
    if (
        entity.mod_manager is None or
        entity.world is None
    ):
        return
    if entity.state in (EntityState.DRAG, EntityState.MOVING):
        return

    hitbox: QRect = get_effective_hitbox(entity)

    fallback_center = QPointF(
        entity.x() + hitbox.center().x(),
        entity.y() + hitbox.center().y(),
    )
    my_center: Optional[QPointF] = centers.get(entity) if centers else fallback_center

    repel_x, repel_y = 0.0, 0.0
    min_dist: float = hitbox.width() * 0.6

    all_entities: list[BaseStructure | Entity] = (
        entity.world.active_entities + entity.world.active_structures
    )

    for other in all_entities:
        is_other_dead: bool = getattr(other, "is_dead", False)
        if other is entity or is_other_dead:
            continue

        other_fallback = QPointF(
            other.x() + other.current_hitbox.center().x(),
            other.y() + other.current_hitbox.center().y(),
        )
        other_center: Optional[QPointF] = centers.get(other) if centers else other_fallback
        if other_center is None or my_center is None:
            continue

        dx: float = my_center.x() - other_center.x()
        dy: float = my_center.y() - other_center.y()
        dist: float = math.hypot(dx, dy)

        if 0 < dist < min_dist:
            force: float = (min_dist - dist) / min_dist
            repel_x += (dx / dist) * force * (current_move_speed * 1.5)

            if entity.mod_manager.can_fly:
                repel_y += (dy / dist) * force * (current_move_speed * 1.5)

    if repel_x != 0 or repel_y != 0:
        new_x: float = entity.x() + repel_x
        new_y: float = entity.y() + repel_y if entity.mod_manager.can_fly else entity.y()
        entity.setPos(new_x, new_y)


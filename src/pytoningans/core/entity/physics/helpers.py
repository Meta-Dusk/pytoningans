from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QRect

if TYPE_CHECKING:
    from PySide6.QtCore import QRectF
    from pytoningans.core.entity.base_entity import BaseEntity


def get_effective_hitbox(entity: BaseEntity) -> QRect:
    """
    Returns the entity's hitbox, falling back to boundingRect or
    a 50x50 box if uninitialized.
    """
    hitbox: QRect = entity.current_hitbox
    if hitbox.width() <= 0 or hitbox.height() <= 0:
        b_rect: QRectF = entity.boundingRect()
        bounds: tuple[int, int] =  (
            int(b_rect.width()) if b_rect.width() > 0 else 50,
            int(b_rect.height()) if b_rect.height() > 0 else 50
        )
        hitbox = QRect(0, 0, *bounds)
    return hitbox


def get_world_bounds(entity: BaseEntity) -> Optional[QRectF]:
    """Returns the scene rectangle of the active world, if available."""
    if entity.world is not None and entity.world.scene is not None:
        return entity.world.scene.sceneRect()
    return None


def get_world_horizontal_range(entity: BaseEntity) -> Optional[tuple[float, float]]:
    """
    Returns `(min_x, max_x)` for entity's root origin within world scene boundaries.
    """
    bounds: Optional[QRectF] = get_world_bounds(entity)
    if bounds is None: return None
    hitbox: QRect = get_effective_hitbox(entity)
    min_x = float(bounds.left() - hitbox.x())
    max_x = float(bounds.right() - hitbox.x() - hitbox.width())
    return min_x, max_x


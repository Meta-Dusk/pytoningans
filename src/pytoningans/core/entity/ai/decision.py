from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional, cast

from PySide6.QtCore import QPointF, QRect, QRectF

from pytoningans.core.api import BaseBehavior, BaseEntityBehavior, IEntity
from pytoningans.core.constants import EntityState
from .item_seeking import check_item_seeking

if TYPE_CHECKING:
    from .system import AISystem


def ai_decision_tick(ai: AISystem) -> None:
    """
    Executes a periodic AI decision tick
    (custom hook -> item seeking -> default wandering).
    """
    if ai.entity is None:
        return
    if ai.entity.state in (
        EntityState.DRAG, EntityState.INTERACT, EntityState.CLIMBING
    ):
        return
    if ai.entity.is_climbing:
        return
    if on_ai_decision_tick(ai):
        return
    if ai.entity.is_following_cursor:
        return
    if check_item_seeking(ai):
        return
    default_ai_decision(ai)


def on_ai_decision_tick(ai: AISystem) -> bool:
    """Invokes custom modder on_decision_tick hook if present."""
    if ai.entity is None:
        return False

    behavior: Optional[BaseBehavior] = ai.entity.behavior
    if behavior is None or not isinstance(behavior, BaseEntityBehavior):
        return False
    try:
        entity_api: IEntity = cast(IEntity, ai.entity)
        if behavior.on_decision_tick(entity_api):
            return True
    except Exception as e:
        print(f"Custom AI Error (Decision): {e}")

    return False


def default_ai_decision(ai: AISystem) -> None:
    """Default wandering/jumping behavior for living entities."""
    if (
        ai.entity is None or
        ai.entity.mod_manager is None or
        ai.entity.anim_sys is None or
        ai.entity.world is None
    ):
        return

    if not ai.entity.mod_manager.can_fly and random.random() < 0.15:
        ai.entity.jump()
        return

    geom: QRectF = ai.entity.world.scene.sceneRect()
    platform_rect: Optional[QRect] = (
        ai.entity.physics_sys.current_platform_rect
        if ai.entity.physics_sys is not None else None
    )

    if random.random() < 0.60:
        dest_x: float = 0.0
        if (
            platform_rect is not None and
            not ai.entity.mod_manager.can_fly and
            random.random() < 0.70
        ):
            # Wander along the window platform ledge
            min_x: float = max(geom.left() + 20, float(platform_rect.left() + 10))
            max_x: float = min(
                geom.right() - ai.entity.boundingRect().width() - 20,
                float(platform_rect.right() - ai.entity.boundingRect().width() - 10)
            )
            if min_x < max_x:
                dest_x = random.uniform(min_x, max_x)
            else:
                dest_x = min_x
        else:
            # Wander across the whole screen (or walk off ledge)
            dest_x = random.uniform(
                geom.left() + 50,
                geom.right() - ai.entity.boundingRect().width() - 50
            )

        dest_y: float = 0.0
        if ai.entity.mod_manager.can_fly:
            dest_y = random.uniform(
                geom.top() + 50,
                geom.bottom() - ai.entity.boundingRect().height() - 50
            )
        else:
            dest_y = ai.entity.y()

        ai.entity.target_pos = QPointF(dest_x, dest_y)
        ai.entity.anim_sys.set_state(EntityState.MOVING)
    else:
        ai.entity.target_pos = None
        ai.entity.anim_sys.set_state(EntityState.IDLE)


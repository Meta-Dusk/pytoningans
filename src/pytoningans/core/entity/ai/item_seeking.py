from __future__ import annotations

import math, random
from typing import TYPE_CHECKING, Optional, cast

from PySide6.QtCore import QPointF

from pytoningans.core.api import BaseBehavior, BaseEntityBehavior, IEntity, IItem
from pytoningans.core.constants import EntityState

if TYPE_CHECKING:
    from pytoningans.core.entity.base_item import BaseItem
    from .system import AISystem


def check_item_seeking(ai: AISystem) -> bool:
    """Evaluates whether the entity should seek items or use held items."""
    if (
        ai.entity is None or
        ai.entity.world is None or
        ai.entity.mod_manager is None or
        ai.entity.anim_sys is None or
        getattr(ai.entity, "is_dead", False)
    ):
        return False

    # Gather ground items available in the world (excluding held, dragged, or cooldown items)
    world_items: list[BaseItem] = getattr(ai.entity.world, "active_items", [])
    ground_items: list[IItem] = [
        cast(IItem, item) for item in world_items
        if item.is_interactable and not (
            getattr(item, "_last_holder", None) is ai.entity and
            getattr(item, "_pickup_cooldown", 0) > 0
        )
    ]

    # Custom Modder Hook: on_seek_item
    behavior: Optional[BaseBehavior] = ai.entity.get_behavior
    if isinstance(behavior, BaseEntityBehavior):
        try:
            entity_api: IEntity = cast(IEntity, ai.entity)
            custom_result = behavior.on_seek_item(entity_api, ground_items)
            if custom_result is True:
                return True
            elif custom_result is not None and custom_result is not False:
                # Modder returned a specific IItem to seek towards
                navigate_towards_item(ai, custom_result)
                return True
        except Exception as e:
            print(f"Custom AI Error (Seek Item): {e}")

    # Engine Default Survival Seeking
    return default_survival_seeking(ai, ground_items)


def default_survival_seeking(ai: AISystem, ground_items: list[IItem]) -> bool:
    """Default survival behavior: seek or use healing items if HP < 50%."""
    if ai.entity is None or ai.entity.mod_manager is None or ai.entity.anim_sys is None:
        return False

    max_hp: int = ai.entity.mod_manager.max_health
    # Only seek survival items when injured (below 50% max HP)
    if ai.entity.current_health >= max_hp * 0.5:
        return False

    # A. Check if already holding a consumable healing item
    held: Optional[BaseItem] = ai.entity.held_item
    if held is not None and held.has_all_tags("consumable", "healing"):
        if random.random() < 0.35 and not (ai.entity.bubble and ai.entity.bubble.isVisible()):
            ai.entity.say("I need this!", duration_ms=2000)
        ai.entity.use_item()
        return True

    # B. Search for unheld ground items with "consumable" and "healing" tags
    healing_items: list[IItem] = [
        it for it in ground_items
        if it.has_all_tags("consumable", "healing")
    ]
    if not healing_items:
        return False

    # Find closest healing item
    my_pos: QPointF = ai.entity.pos()
    nearest: IItem = min(
        healing_items,
        key=lambda it: math.hypot(it.x() - my_pos.x(), it.y() - my_pos.y())
    )

    navigate_towards_item(ai, nearest)
    if random.random() < 0.25 and not (ai.entity.bubble and ai.entity.bubble.isVisible()):
        ai.entity.say("I need healing!", duration_ms=2000)
    return True


def navigate_towards_item(ai: AISystem, item: IItem) -> None:
    """Sets movement target towards a specified item."""
    if ai.entity is None or ai.entity.anim_sys is None:
        return

    target_x: float = item.x()
    target_y: float = (
        item.y() if (ai.entity.mod_manager and ai.entity.mod_manager.can_fly)
        else ai.entity.y()
    )

    ai.entity._target_pos = QPointF(target_x, target_y)
    ai.entity.anim_sys.set_state(EntityState.MOVING)


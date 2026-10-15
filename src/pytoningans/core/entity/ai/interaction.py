from __future__ import annotations

from typing import TYPE_CHECKING, Optional, cast

from PySide6.QtCore import QPointF

from pytoningans.core.api import BaseBehavior, BaseEntityBehavior, IEntity
from pytoningans.core.constants import BehaviorType, EntityState
from .combat import get_distance

if TYPE_CHECKING:
    from pytoningans.core.entity.living_entity import Entity
    from .system import AISystem


def check_interactions(ai: AISystem, centers: Optional[dict[Entity, QPointF]] = None) -> None:
    """Checks proximity to other entities to trigger friendly/social interactions."""
    if (
        ai.entity is None or
        ai.entity.mod_manager is None or
        ai.entity.mod_manager.behavior_type is BehaviorType.PASSIVE or
        ai.entity.entity_manager is None
    ):
        return
    
    if ai.interaction_cooldown > 0:
        ai.interaction_cooldown -= 1
        return

    if not ai.entity.is_interactable:
        return

    fallback_center: QPointF = ai.entity.pos() + ai.entity.current_hitbox.center()
    my_center: Optional[QPointF] = centers.get(ai.entity) if centers else fallback_center

    for other_entity in ai.entity.entity_manager.active_entities:
        if (
            other_entity.ai_sys is None or
            other_entity is ai.entity or
            not other_entity.is_interactable
        ):
            continue

        other_fallback: QPointF = other_entity.pos() + other_entity.current_hitbox.center()
        other_center: Optional[QPointF] = centers.get(other_entity) if centers else other_fallback
        if other_center is None or my_center is None:
            continue
        dist: float = get_distance(my_center, other_center)

        if dist >= 120:
            return
        override_default: bool = on_check_interactions(ai, other_entity)
        
        if not override_default:
            ai.entity.facing_left = other_center.x() < my_center.x()
            other_entity.facing_left = my_center.x() < other_center.x()
            start_interaction(ai)
            other_entity.ai_sys.start_interaction()
            
        break


def on_check_interactions(ai: AISystem, other_entity: Entity) -> bool:
    """Invokes custom modder on_interact hook if defined."""
    if ai.entity is None:
        return False
    behavior: Optional[BaseBehavior] = ai.entity.get_behavior
    if not isinstance(behavior, BaseEntityBehavior):
        return False
    try:
        entity_api: IEntity = cast(IEntity, ai.entity)
        other_entity_api: IEntity = cast(IEntity, other_entity)
        return behavior.on_interact(entity_api, other_entity_api)
    except Exception as e:
        print(f"Custom AI Error (Interact): {e}")
    return False


def start_interaction(ai: AISystem) -> None:
    """Puts entity into interaction state with cooldown."""
    if ai.entity is None or ai.entity.anim_sys is None:
        return
    ai.entity._target_pos = None
    ai.interact_time_left = 3000 
    ai.interaction_cooldown = 6000
    ai.entity.anim_sys.set_state(EntityState.INTERACT)


"""
PyToNingans Modding API - Behavior Base Classes and Modding Hooks
=================================================================
Abstract and base classes for authoring custom AI, combat interactions,
and environmental triggers in a mod's `behavior.py`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .protocols import IEntity, IStructure, IItem


# =============================================================================
#* Behavior Base Classes and Modding Hooks
# =============================================================================

class BaseEntityBehavior:
    """
    Inherit from this class in your entity's `behavior.py`.
    Override any of the hook methods below to implement custom AI logic, interactions,
    combat rules, or dialogue responses.
    """
    def on_spawn(self, entity: IEntity) -> None:
        """Called once when the entity is instantiated and placed in a world."""
        pass

    def on_update(self, entity: IEntity, dt: int) -> None:
        """Called every frame tick. Use for real-time timers and state monitoring."""
        pass

    def on_decision_tick(self, entity: IEntity) -> bool:
        """
        Called when the engine's AI brain evaluates a wander or action decision.
        Return True to override default engine movement/action behavior.
        """
        return False

    def on_interact(self, entity: IEntity, other_entity: IEntity) -> bool:
        """
        Called when this entity collides with or approaches another living entity.
        Return True to override the default social interaction.
        """
        return False

    def on_item_interact(self, entity: IEntity, item: IItem) -> bool:
        """
        Called when this entity collides with or touches an item on the ground.
        Return True to override default collision handling (e.g. automatically picking up).
        """
        return False

    def on_seek_item(self, entity: IEntity, available_items: list[IItem]) -> Optional[IItem] | bool:
        """
        Called when the entity evaluates seeking an item (e.g. survival or scavenging).
        - Return a specific IItem to actively pathfind towards it.
        - Return True to indicate custom seeking was handled (skips default search).
        - Return False or None to allow default survival seeking (e.g. seeking healing items when low on HP) to run.
        """
        return None

    def on_speak(self, entity: IEntity, text: str) -> None:
        """Called whenever this entity speaks dialogue via say() or force_talk()."""
        pass

    def on_damage(self, entity: IEntity, amount: int) -> None:
        """Called when the entity takes damage."""
        pass

    def on_death(self, entity: IEntity) -> None:
        """Called immediately after the entity's health drops to 0."""
        pass

    def on_revive(self, entity: IEntity) -> None:
        """Called when the entity is revived from death."""
        pass

    def on_attack(self, entity: IEntity, target: IEntity) -> bool:
        """
        Called when the entity initiates an attack against target.
        Return True to override engine combat resolution.
        """
        return False

    def on_state_change(self, entity: IEntity, old_state: str, new_state: str) -> None:
        """Called whenever the entity's state changes (e.g. idle -> moving)."""
        pass

    def on_hover_enter(self, entity: IEntity) -> None:
        """Called when the mouse cursor enters the entity's bounding area."""
        pass

    def on_hover_leave(self, entity: IEntity) -> None:
        """Called when the mouse cursor leaves the entity's bounding area."""
        pass


class BaseStructureBehavior:
    """
    Inherit from this class in your structure's `behavior.py`.
    Override hook methods below to implement custom structure activations, portal logic,
    and entity interaction triggers.
    """
    def on_spawn(self, structure: IStructure) -> None:
        """Called once when the structure is placed in a world. Ideal for attaching components."""
        pass

    def on_update(self, structure: IStructure, dt: int) -> None:
        """Called every frame tick."""
        pass

    def on_interact(self, structure: IStructure, entity: IEntity) -> None:
        """Called when a living entity overlaps or touches this structure."""
        pass

    def on_hover_enter(self, structure: IStructure) -> None:
        """Called when the mouse cursor enters the structure's bounding area."""
        pass

    def on_hover_leave(self, structure: IStructure) -> None:
        """Called when the mouse cursor leaves the structure's bounding area."""
        pass

    def on_state_change(self, structure: IStructure, old_state: str, new_state: str) -> None:
        """Called when the structure's operational state changes (e.g. idle <-> active)."""
        pass

    def on_destroy(self, structure: IStructure) -> None:
        """Called when the structure is removed or closed."""
        pass


class BaseItemBehavior:
    """
    Inherit from this class in your item's `behavior.py`.
    Override hook methods below to implement custom item effects, pickup validation,
    consumption logic, and entity interaction responses.
    """
    def on_spawn(self, item: IItem) -> None:
        """Called once when the item is instantiated and placed in a world."""
        pass

    def on_update(self, item: IItem, dt: int) -> None:
        """Called every frame tick."""
        pass

    def on_pickup(self, item: IItem, entity: IEntity) -> bool:
        """
        Called when a living entity attempts to pick up this item.
        Return True to allow pickup, False to cancel/reject it.
        """
        return True

    def on_use(self, item: IItem, entity: Optional[IEntity]) -> bool:
        """
        Called when the item is used by its holder or triggered via context menu.
        Return True if the item was successfully used/consumed.
        """
        return True

    def on_drop(self, item: IItem, entity: Optional[IEntity]) -> None:
        """Called when this item is dropped by its holder or released."""
        pass

    def on_interact(self, item: IItem, entity: IEntity) -> bool:
        """
        Called when a living entity collides with or touches this item on the ground.
        Return True to override default collision handling.
        """
        return False

    def on_state_change(self, item: IItem, old_state: str, new_state: str) -> None:
        """Called when the item's operational state changes."""
        pass

    def on_hover_enter(self, item: IItem) -> None:
        """Called when the mouse cursor enters the item's bounding area."""
        pass

    def on_hover_leave(self, item: IItem) -> None:
        """Called when the mouse cursor leaves the item's bounding area."""
        pass

    def on_destroy(self, item: IItem) -> None:
        """Called when the item is removed from the world or destroyed."""
        pass


type BaseBehavior = BaseEntityBehavior | BaseStructureBehavior | BaseItemBehavior


"""
PyToNingans Modding API - Behavior Base Classes and Modding Hooks
=================================================================
Abstract and base classes for authoring custom AI, combat interactions,
and environmental triggers in a mod's `behavior.py`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytoningans.core.api.protocols import IEntity, IStructure


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


type BaseBehavior = BaseEntityBehavior | BaseStructureBehavior


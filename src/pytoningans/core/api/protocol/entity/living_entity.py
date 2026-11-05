from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

from .base_entity import IBaseEntity

if TYPE_CHECKING:
    from ...types import BehaviorType, Pos2D
    from ..core import IEntityManager
    from .base_item import IItem


@runtime_checkable
class IEntity(IBaseEntity, Protocol):
    """Living desktop entity with health, AI, combat, and dialogue."""
    is_dead: bool
    current_health: int
    regen_rate: float
    target_pos: Optional[Pos2D]
    behavior_type: BehaviorType
    entity_manager: Optional[IEntityManager]
    held_item: Optional[IItem]

    def jump(self) -> None:
        """Causes the entity to jump upwards if grounded."""
        ...

    def take_damage(self, amount: int) -> None:
        """Inflicts damage on the entity, flashing tint effect and triggering death if depleted."""
        ...

    def heal(self, amount: int) -> None:
        """Restores health up to max health, updating health indicators and visuals."""
        ...

    def die(self) -> None:
        """Triggers the entity's death sequence and animations."""
        ...

    def revive(self) -> None:
        """Restores health to max and revives the entity to an idle state."""
        ...

    def force_talk(self) -> None:
        """Displays a random line from the mod's plain dialogue pool."""
        ...

    def say(self, text: str, duration_ms: int = 4000, is_death: bool = False) -> None:
        """Displays a speech bubble with the given text for duration_ms milliseconds."""
        ...

    def pick_up(self, item: IItem) -> bool:
        """Picks up an item if one is not already held."""
        ...

    def drop_item(self) -> Optional[IItem]:
        """Drops the currently held item."""
        ...

    def use_item(self) -> bool:
        """Uses the currently held item."""
        ...


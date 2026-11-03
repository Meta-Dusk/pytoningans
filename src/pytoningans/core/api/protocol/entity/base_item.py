from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

from .base_entity import IBaseEntity

if TYPE_CHECKING:
    from .living_entity import IEntity


@runtime_checkable
class IItem(IBaseEntity, Protocol):
    """Interactable item object on desktop that can be picked up, dropped, and used."""
    holder: Optional[IEntity]
    is_held: bool

    def pick_up(self, entity: IEntity) -> bool:
        """Picks up this item by the specified living entity."""
        ...

    def drop(self, entity: Optional[IEntity] = None) -> None:
        """Drops this item onto the ground/desktop."""
        ...

    def use(self, entity: Optional[IEntity] = None) -> bool:
        """Uses this item (invoking custom behavior hook or triggering interaction)."""
        ...


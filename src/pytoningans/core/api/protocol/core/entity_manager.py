from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..entity import IBaseEntity, IEntity, IItem, IStructure
    from .world import IWorld


@runtime_checkable
class IEntityManager(Protocol):
    """Global entity coordinator across all active monitor screens."""
    active_worlds: list[IWorld]
    active_entities: list[IEntity]
    active_structures: list[IStructure]
    active_items: list[IItem]

    def spawn_entity(
        self,
        x: float,
        y: float,
        mod_folder: str,
        target_world: Optional[IWorld] = None,
        instance_name: Optional[str] = None,
        fade_in: Optional[bool] = None,
    ) -> Optional[IBaseEntity]:
        """Spawns an entity or structure into the game world."""
        ...

    def remove_entity(self, entity: IBaseEntity) -> None:
        """Removes an entity or structure from all tracking and world scenes."""
        ...
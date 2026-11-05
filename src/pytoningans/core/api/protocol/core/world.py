from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .entity_manager import IEntityManager
    from ..particle import IParticleManager
    from ..entity import IEntity, IItem, IStructure
    from ...types import IRect


@runtime_checkable
class IWorld(Protocol):
    """Represents a fullscreen monitor overlay containing active entities."""
    entity_manager: IEntityManager
    particle_manager: IParticleManager
    active_entities: list[IEntity]
    active_structures: list[IStructure]
    active_items: list[IItem]
    active_window_rects: list[IRect]

    def move_window(self, win_rect: IRect, dx: int, dy: int) -> bool:
        """Moves the desktop window associated with win_rect by (dx, dy) pixels."""
        ...


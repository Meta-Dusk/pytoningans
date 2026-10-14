"""
PyToNingans Modding API - Component Architecture
================================================
Reusable entity and structure component protocols and base classes.
"""
from __future__ import annotations

from typing import Protocol, Optional, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:
    from pytoningans.core.api.protocols import IBaseEntity, IWorld, IEntity, IStructure


# =============================================================================
#* Component System
# =============================================================================

@runtime_checkable
class IComponent(Protocol):
    """Protocol representing a reusable entity component."""
    name: str
    enabled: bool
    owner: Optional[IBaseEntity]

    def on_attach(self) -> None:
        """Invoked when the component is bound to an entity."""
        ...

    def update(self, dt: int) -> None:
        """Invoked every engine tick (dt in milliseconds)."""
        ...

    def on_detach(self) -> None:
        """Invoked when the component is removed from an entity."""
        ...


class BaseComponent:
    """Base class for writing custom mod components in pure Python."""
    name: str = "custom"

    def __init__(self, owner: Optional[IBaseEntity] = None) -> None:
        self.owner: Optional[IBaseEntity] = owner
        self.enabled: bool = True

    def on_attach(self) -> None:
        """Called immediately after being attached to an owner entity."""
        pass

    def update(self, dt: int) -> None:
        """Called every frame update with the delta time in milliseconds."""
        pass

    def on_detach(self) -> None:
        """Called when the component is removed or the owner is destroyed."""
        pass


@runtime_checkable
class ITeleportationComponent(IComponent, Protocol):
    """Protocol for structures capable of teleporting entities across worlds."""
    target_world: Optional[IWorld]
    linked_portal: Optional[IStructure]
    exit_offset_x: float
    exit_offset_y: float

    def teleport_entity(self, entity: IEntity) -> None:
        """Transports the specified entity to the target world or linked structure."""
        ...


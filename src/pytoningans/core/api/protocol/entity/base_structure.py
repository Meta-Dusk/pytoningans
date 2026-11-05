from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

from .base_entity import IBaseEntity

if TYPE_CHECKING:
    from ...components import ITeleportationComponent
    from ..core import IWorld


@runtime_checkable
class IStructure(IBaseEntity, Protocol):
    """Environmental structure or portal on the desktop."""
    def toggle_active(self) -> None:
        """Toggles the structure between IDLE and ACTIVE operational states."""
        ...

    def toggle_physics(self) -> None:
        """Toggles whether the structure is affected by gravity."""
        ...

    def set_physics_enabled(self, enabled: bool) -> None:
        """Sets whether the structure is affected by gravity."""
        ...

    def attach_teleportation(
        self,
        target_world: Optional[IWorld] = None,
        exit_offset_x: float = 80.0,
        exit_offset_y: float = 0.0
    ) -> ITeleportationComponent:
        """Attaches a TeleportationComponent configuring this structure as a travel portal."""
        ...


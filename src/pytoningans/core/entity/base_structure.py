from __future__ import annotations

from typing import Optional, cast, TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF

from ..api import BaseStructureBehavior
from ..components.teleportation import TeleportationComponent
from ..constants import StructureState
from ..entity.base_entity import BaseEntity

if TYPE_CHECKING:
    from ..api import BaseBehavior, IEntity, IStructure
    from ..world import WorldOverlay
    from ..mod_manager import ModManager
    from ..components.base_component import BaseComponent


class BaseStructure(BaseEntity):
    """Static or animated environmental objects."""
    def __init__(
        self, start_x: float, start_y: float,
        mod_manager: Optional[ModManager], world: Optional[WorldOverlay]
    ) -> None:
        super().__init__(start_x, start_y, mod_manager, world)

        can_fly: bool = mod_manager.can_fly if mod_manager else False
        self.is_physics_enabled = not can_fly
        self.locks.physics = self.is_physics_enabled

    def set_physics_enabled(self, enabled: bool) -> None:
        """Sets whether the structure is affected by gravity."""
        self.is_physics_enabled = enabled
        self.locks.physics = enabled
        if not enabled: self.velocity_y = 0.0

    def toggle_physics(self) -> None:
        """Toggles whether the structure is affected by gravity."""
        self.set_physics_enabled(not self.is_physics_enabled)

    def toggle_active(self) -> None:
        """Toggles between IDLE and ACTIVE operational states, updating components."""
        new_state: str = (
            StructureState.IDLE
            if self.state == StructureState.ACTIVE else
            StructureState.ACTIVE
        )
        self.state = new_state
        teleport_comp: Optional[BaseComponent] = self.get_component("teleportation")
        if isinstance(teleport_comp, TeleportationComponent):
            teleport_comp.enabled = (new_state == StructureState.ACTIVE)

    def _set_linked_portal(self, target: Optional[BaseStructure]) -> None:
        teleport_comp: Optional[BaseComponent] = self.get_component("teleportation")
        if not isinstance(teleport_comp, TeleportationComponent):
            return
        teleport_comp.linked_portal = target
        if target is None or not target.has_component("teleportation"):
            return
        target_comp: Optional[BaseComponent] = target.get_component("teleportation")
        if isinstance(target_comp, TeleportationComponent):
            target_comp.linked_portal = self

    def update_systems(self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None) -> None:
        super().update_systems(dt, centers)

        if self.mod_manager is None or self.mod_manager.custom_behavior is None:
            return

        behavior: BaseBehavior = self.mod_manager.custom_behavior
        if not isinstance(behavior, BaseStructureBehavior): return
        try:
            behavior.on_update(cast("IStructure", self), dt)
        except Exception as e:
            print(f"Custom Structure on_update Error: {e}")

        # Check interaction collision with living entities
        if self.world is None: return
        
        struct_rect: QRectF = self.sceneBoundingRect()
        for entity in list(self.world.active_entities):
            if (
                entity.is_dead or
                not struct_rect.intersects(entity.sceneBoundingRect())
            ):
                return
            try:
                behavior.on_interact(cast("IStructure", self), cast("IEntity", entity))
            except Exception as e:
                print(f"Custom Structure on_interact Error: {e}")

    def attach_teleportation(
        self,
        target_world: Optional[WorldOverlay] = None,
        exit_offset_x: float = 80.0,
        exit_offset_y: float = 0.0
    ) -> TeleportationComponent:
        _target_world: Optional[WorldOverlay] = target_world or self.world
        comp = TeleportationComponent(self, _target_world, exit_offset_x, exit_offset_y)
        self.add_component(comp)
        return comp

    def destroy(self) -> None:
        self._on_destroy()

        # Clean up any other teleport components linking to this structure
        if self.world is not None and self.world.manager is not None:
            for other in list(self.world.manager.active_structures):
                if other is self: continue
                other_comp: Optional[BaseComponent] = other.get_component("teleportation")
                if isinstance(other_comp, TeleportationComponent) and other_comp.linked_portal is self:
                    other_comp.linked_portal = None
            self.world.manager.remove_entity(self)
        elif self.world is not None:
            if self in self.world.active_structures:
                self.world.active_structures.remove(self)
            if self.scene():
                self.scene().removeItem(self)

        super().destroy()

    def _on_destroy(self) -> None:
        if self.mod_manager is None or self.mod_manager.custom_behavior is None:
            return
        behavior: BaseBehavior = self.mod_manager.custom_behavior
        if isinstance(behavior, BaseStructureBehavior):
            try:
                behavior.on_destroy(cast("IStructure", self))
            except Exception as e:
                print(f"Custom Structure on_destroy Error: {e}")

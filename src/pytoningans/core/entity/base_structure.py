from typing import Optional, cast

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QGraphicsSceneContextMenuEvent, QMenu

from pytoningans.core.api import BaseBehavior, BaseStructureBehavior, IEntity, IStructure
from pytoningans.core.components.base_component import BaseComponent
from pytoningans.core.components.teleportation import TeleportationComponent
from pytoningans.core.constants import StructureState
from pytoningans.core.entity.base_entity import BaseEntity
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.world import WorldOverlay


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
            StructureState.IDLE.value
            if self.state == StructureState.ACTIVE.value else
            StructureState.ACTIVE.value
        )
        self.state = new_state
        teleport_comp: Optional[BaseComponent] = self.get_component("teleportation")
        if isinstance(teleport_comp, TeleportationComponent):
            teleport_comp.enabled = (new_state == StructureState.ACTIVE.value)

    def _set_linked_portal(self, target: Optional[BaseStructure]) -> None:
        teleport_comp: Optional[BaseComponent] = self.get_component("teleportation")
        if isinstance(teleport_comp, TeleportationComponent):
            teleport_comp.linked_portal = target
            if target is not None and target.has_component("teleportation"):
                target_comp: Optional[BaseComponent] = target.get_component("teleportation")
                if isinstance(target_comp, TeleportationComponent):
                    target_comp.linked_portal = self

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        self.is_force_idle = True
        menu = QMenu(self.world.view) if self.world else QMenu()

        # Close Structure
        menu.addAction("Close Structure", self.destroy)
        menu.addSeparator()

        # Flip Horizontally
        menu.addAction("Flip Horizontally", self.flip)

        # Toggle Active
        status_text: str = (
            "Deactivate"
            if self.state == StructureState.ACTIVE.value else
            "Activate"
        )
        menu.addAction(f"{status_text} Structure", self.toggle_active)

        # Toggle Physics / Gravity
        physics_action: QAction = menu.addAction("Affected by Gravity")
        physics_action.setCheckable(True)
        physics_action.setChecked(self.is_physics_enabled)
        physics_action.toggled.connect(self.set_physics_enabled)

        menu.addSeparator()

        # Component-specific actions
        teleport_comp: Optional[BaseComponent] = self.get_component("teleportation")
        if isinstance(teleport_comp, TeleportationComponent):
            portal_menu: QMenu = menu.addMenu("Change Linked Portal")

            # Unlink option
            unlink_action: QAction = portal_menu.addAction("None (Unlinked)")
            if teleport_comp.linked_portal is None:
                unlink_action.setCheckable(True)
                unlink_action.setChecked(True)
            unlink_action.triggered.connect(lambda: self._set_linked_portal(None))
            portal_menu.addSeparator()

            # Available other structures
            other_structures: list[BaseStructure] = []
            if self.world is not None and self.world.manager is not None:
                for struct in self.world.manager.active_structures:
                    if struct is self: continue
                    other_structures.append(struct)

            if other_structures:
                for idx, other in enumerate(other_structures):
                    other_name: str = (
                        other.mod_manager.current_mod_name
                        if other.mod_manager and other.mod_manager.current_mod_name
                        else (other.mod_manager.current_mod_folder if other.mod_manager else f"Structure #{idx + 1}")
                    )
                    world_info: str = (
                        f"World {self.world.manager.active_worlds.index(other.world) + 1}"
                        if self.world is not None and other.world in self.world.manager.active_worlds
                        else ""
                    )
                    label: str = f"{other_name} ({world_info} @ {int(other.x())}, {int(other.y())})"
                    action = portal_menu.addAction(label)
                    action.setCheckable(True)
                    if teleport_comp.linked_portal is other:
                        action.setChecked(True)
                    action.triggered.connect(lambda checked=False, target=other: self._set_linked_portal(target))
            else:
                empty_action = portal_menu.addAction("No other structures available")
                empty_action.setEnabled(False)

            menu.addAction("Remove Teleportation Component", lambda: self.remove_component("teleportation"))
        else:
            menu.addAction("Add Teleportation Component", lambda: self.attach_teleportation())

        menu.exec(event.screenPos())
        self.is_force_idle = False

    def update_systems(self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None) -> None:
        super().update_systems(dt, centers)

        if self.mod_manager is None or self.mod_manager.custom_behavior is None:
            return

        behavior: BaseBehavior = self.mod_manager.custom_behavior
        if isinstance(behavior, BaseStructureBehavior):
            try:
                behavior.on_update(cast(IStructure, self), dt)
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
                    behavior.on_interact(cast(IStructure, self), cast(IEntity, entity))
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
                behavior.on_destroy(cast(IStructure, self))
            except Exception as e:
                print(f"Custom Structure on_destroy Error: {e}")

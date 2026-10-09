from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from PySide6.QtCore import QRectF

from pytoningans.core.constants import EntityState
from pytoningans.core.components.base_component import BaseComponent

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseStructure, Entity
    from pytoningans.core.world import WorldOverlay

class TeleportationComponent(BaseComponent):
    """Handles collision detection and teleportation of entities between worlds or portals."""
    name: str = "teleportation"

    def __init__(
        self,
        owner: Optional[BaseStructure] = None,
        target_world: Optional[WorldOverlay] = None,
        exit_offset_x: float = 80.0,
        exit_offset_y: float = 0.0
    ) -> None:
        super().__init__(owner)
        self.target_world: Optional[WorldOverlay] = target_world
        self.linked_portal: Optional[BaseStructure] = None
        self.exit_offset_x: float = exit_offset_x
        self.exit_offset_y: float = exit_offset_y

    def update(self, dt: int) -> None:
        if not self.enabled or self.owner is None or self.owner.world is None:
            return

        portal_rect: QRectF = self.owner.sceneBoundingRect()
        for entity in list(self.owner.world.active_entities):
            if entity.is_dead or entity.state == EntityState.DRAG.value:
                continue
            if portal_rect.intersects(entity.sceneBoundingRect()):
                self.teleport_entity(entity)

    def teleport_entity(self, entity: Entity) -> None:
        if self.owner is None or self.owner.world is None:
            return

        # Target the linked portal's world, or fallback to the preset destination
        dest_world: WorldOverlay = (
            self.linked_portal.world 
            if self.linked_portal and self.linked_portal.world 
            else (self.target_world or self.owner.world)
        )

        if entity in self.owner.world.active_entities:
            self.owner.world.active_entities.remove(entity)
        self.owner.world.scene.removeItem(entity)

        entity.world = dest_world
        dest_world.scene.addItem(entity)
        dest_world.active_entities.append(entity)

        pet_w: int = entity.width()
        if self.linked_portal is not None:
            if self.exit_offset_x > 0:
                spawn_x = self.linked_portal.x() + self.linked_portal.width() + 10
            else:
                spawn_x = self.linked_portal.x() - pet_w - 10
            spawn_y = self.linked_portal.y() + self.exit_offset_y
        else:
            spawn_x = dest_world.scene.sceneRect().width() / 2
            spawn_y = dest_world.scene.sceneRect().height() / 2

        entity.setPos(spawn_x, spawn_y)
        entity.velocity_y = 0.0

        if entity.anim_sys is not None:
            entity.anim_sys.set_state(EntityState.IDLE)
        entity.target_pos = None
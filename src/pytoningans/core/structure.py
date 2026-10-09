from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPixmap, QColor

from pytoningans.core.entity.base_entity import BaseStructure
from pytoningans.core.constants import EntityState

if TYPE_CHECKING:
    from pytoningans.core.world import WorldOverlay
    from pytoningans.core.entity.base_entity import Entity
    from pytoningans.core.mod_manager import ModManager

class TeleportationComponent:
    """Reusable logic for handling collision and teleportation between worlds."""
    def __init__(self, owner: BaseStructure, target_world: WorldOverlay) -> None:
        self.owner: BaseStructure = owner
        self.target_world: WorldOverlay = target_world
        self.linked_portal: Optional[BaseStructure] = None
        
        # Positive: spit out to the right; Negative: spit out to the left
        self.exit_offset_x: float = 80.0
        self.exit_offset_y: float = 0.0

    def update(self) -> None:
        if self.linked_portal is None or self.owner.world is None:
            return
            
        portal_rect: QRectF = self.owner.sceneBoundingRect()
        for entity in list(self.owner.world.active_entities):
            if entity.is_dead or entity.state is EntityState.DRAG:
                continue
            if portal_rect.intersects(entity.sceneBoundingRect()):
                self.teleport_entity(entity)

    def teleport_entity(self, entity: Entity) -> None:
        if self.linked_portal is None or self.owner.world is None:
            return

        if entity in self.owner.world.active_entities:
            self.owner.world.active_entities.remove(entity)
        self.owner.world.scene.removeItem(entity)

        entity.world = self.target_world
        self.target_world.scene.addItem(entity)
        self.target_world.active_entities.append(entity)

        pet_w: int = entity.width()
        spawn_x: float
        if self.exit_offset_x > 0:
            spawn_x = self.linked_portal.x() + self.linked_portal.width() + 10
        else:
            spawn_x = self.linked_portal.x() - pet_w - 10

        spawn_y: float = self.linked_portal.y() + self.exit_offset_y

        entity.setPos(spawn_x, spawn_y)
        entity.velocity_y = 0.0

        if entity.anim_sys is not None:
            entity.anim_sys.set_state(EntityState.IDLE)
        entity.target_pos = None


class TravelPortal(BaseStructure):
    """Engine-level portal used for multi-monitor linking."""
    def __init__(
        self, x: float, y: float, 
        world: WorldOverlay, target_world: WorldOverlay,
        mod_manager: Optional[ModManager] = None
    ) -> None:
        super().__init__(x, y, mod_manager, world)
        self.teleport_comp = self.attach_teleportation(target_world)
        
        # Fallback colored box if no custom sprite sheet is present
        if not mod_manager or not mod_manager._global_sheet:
            pix = QPixmap(60, 120)
            pix.fill(QColor(138, 43, 226, 200))
            self.setPixmap(pix)

    @property
    def linked_portal(self) -> Optional[BaseStructure]:
        return self.teleport_comp.linked_portal

    @linked_portal.setter
    def linked_portal(self, portal: Optional[BaseStructure]) -> None:
        self.teleport_comp.linked_portal = portal

    @property
    def exit_offset_x(self) -> float:
        return self.teleport_comp.exit_offset_x

    @exit_offset_x.setter
    def exit_offset_x(self, val: float) -> None:
        self.teleport_comp.exit_offset_x = val

    @property
    def exit_offset_y(self) -> float:
        return self.teleport_comp.exit_offset_y

    @exit_offset_y.setter
    def exit_offset_y(self, val: float) -> None:
        self.teleport_comp.exit_offset_y = val

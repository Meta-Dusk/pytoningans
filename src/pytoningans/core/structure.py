from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPixmap, QColor

from pytoningans.core.entity.base import BaseEntity, BaseStructure
from pytoningans.core.constants import EntityState

if TYPE_CHECKING:
    from pytoningans.core.world import WorldOverlay
    from pytoningans.core.entity.base import Entity

class TravelPortal(BaseStructure):
    """Engine-level portal used for the automatic multi-monitor linking."""
    def __init__(self, x: float, y: float, world: WorldOverlay, target_world: WorldOverlay) -> None:
        super().__init__(x, y, None, world) 
        self.target_world = target_world
        
        # Now holds a direct reference to the destination portal
        self.linked_portal: Optional[TravelPortal] = None 
        
        # Positive means spit out to the right, negative means to the left
        self.exit_offset_x: float = 80.0 
        self.exit_offset_y: float = 0.0
        
        pix = QPixmap(60, 120)
        pix.fill(QColor(138, 43, 226, 200)) 
        self.setPixmap(pix)
        
    def update_systems(self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None) -> None:
        super().update_systems(dt, centers)
        if (
            self.linked_portal is None or
            self.world is None
        ):
            return
        
        portal_rect: QRectF = self.sceneBoundingRect()
        for entity in list(self.world.active_entities):
            if entity.is_dead or entity.state is EntityState.DRAG:
                continue
            if portal_rect.intersects(entity.sceneBoundingRect()):
                self.teleport_pet(entity)
                
    def teleport_pet(self, pet: Entity) -> None:
        if (
            self.linked_portal is None or
            self.world is None
        ):
            return
        
        self.world.active_entities.remove(pet)
        self.world.scene.removeItem(pet)
        
        pet.world = self.target_world
        self.target_world.scene.addItem(pet)
        self.target_world.active_entities.append(pet)
        
        pet_w = pet.width()
        
        # Dynamically calculate exit based on the linked portal's CURRENT position
        if self.exit_offset_x > 0:
            # Spit out safely to the right
            spawn_x = self.linked_portal.x() + self.linked_portal.width() + 10
        else:
            # Spit out safely to the left
            spawn_x = self.linked_portal.x() - pet_w - 10
            
        spawn_y = self.linked_portal.y() + self.exit_offset_y
        
        pet.setPos(spawn_x, spawn_y)
        pet.velocity_y = 0.0 # Reset velocity so they don't carry momentum through the portal
        
        if pet.anim_sys:
            pet.anim_sys.set_state(EntityState.IDLE)
        pet.target_pos = None
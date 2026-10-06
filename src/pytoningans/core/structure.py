from typing import TYPE_CHECKING

from PySide6.QtWidgets import QGraphicsPixmapItem
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPixmap, QColor

from pytoningans.core.constants import PetState

if TYPE_CHECKING:
    from pytoningans.core.world import WorldOverlay
    from pytoningans.core.pet.window import PetWindow

class BaseStructure(QGraphicsPixmapItem):
    """Base class for all static or animated game objects (Buildings, Portals, Props)."""
    def __init__(self, x: float, y: float, world: WorldOverlay) -> None:
        super().__init__()
        self.world = world
        self.setPos(x, y)
        self.hitbox = QRectF()
        
    def update_systems(self, dt: int) -> None:
        """Override this to add physics, animations, or collision logic."""
        pass

    def destroy(self) -> None:
        if self in self.world.active_structures:
            self.world.active_structures.remove(self)
        if self.scene():
            self.scene().removeItem(self)


class TravelPortal(BaseStructure):
    """A prototype structure that teleports pets to another monitor."""
    def __init__(self, x: float, y: float, world: WorldOverlay, target_world: WorldOverlay) -> None:
        super().__init__(x, y, world)
        self.target_world = target_world
        
        # Placeholder graphic: A purple vertical portal
        pix = QPixmap(60, 120)
        pix.fill(QColor(138, 43, 226, 200)) 
        self.setPixmap(pix)
        
    def update_systems(self, dt: int) -> None:
        # Hit-test against all pets in the current world
        portal_rect: QRectF = self.sceneBoundingRect()
        
        for pet in list(self.world.active_pets):
            # Exclude dead or currently dragged pets from teleporting
            if pet.is_dead or pet.state is PetState.DRAG:
                continue
                
            if portal_rect.intersects(pet.sceneBoundingRect()):
                self.teleport_pet(pet)
                
    def teleport_pet(self, pet: PetWindow) -> None:
        # Detach from current world
        self.world.active_pets.remove(pet)
        self.world.scene.removeItem(pet)
        
        # Attach to target world
        pet.world = self.target_world
        self.target_world.scene.addItem(pet)
        self.target_world.active_pets.append(pet)
        
        # Drop them from the top-center of the new monitor
        new_x: float = self.target_world.scene.sceneRect().width() / 2
        new_y: float = 50.0
        pet.setPos(new_x, new_y)
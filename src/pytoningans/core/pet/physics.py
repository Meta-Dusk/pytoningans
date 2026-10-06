from __future__ import annotations

import math

from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QRect, QPointF

from pytoningans.core.constants import PetState

if TYPE_CHECKING:
    from pytoningans.core.pet.window import PetWindow

class PhysicsSystem:
    def __init__(self, pet: Optional[PetWindow] = None) -> None:
        self.pet: Optional[PetWindow] = pet
        self.gravity: float = 0.8
        self.move_speed: float = 2.0

    def update(self, dt: int, centers: Optional[dict[PetWindow, QPointF]] = None) -> None:
        """Processes physics calculations based on elapsed time."""
        if self.pet is None or self.pet.world is None: return
        if not self.pet.locks.physics:
            self.pet.velocity_y = 0
            return

        # Use the World's exact scene boundaries instead of the raw screen geometry
        ground_y: float = self.pet.world.scene.sceneRect().bottom()
        
        time_scale: float = dt / 16.0
        current_gravity: float = self.gravity * time_scale
        current_move_speed: float = self.move_speed * time_scale

        self._tick_gravity_and_collisions(ground_y, current_gravity)

        if self.pet.is_dead: return

        self._tick_soft_collision(current_move_speed, centers)
        self._tick_movement(current_move_speed)

    def _tick_soft_collision(
        self, current_move_speed: float, centers: Optional[dict[PetWindow, QPointF]]= None
    ) -> None:
        """Gently repels overlapping pets to prevent dense clustering."""
        if (
            self.pet is None or
            self.pet.mod_manager is None or
            self.pet.pet_manager is None
        ):
            return
        if self.pet.state in (PetState.DRAG, PetState.MOVING):
            return

        hitbox: QRect = self.pet.current_hitbox
        
        fallback_center = QPointF(
            self.pet.x() + hitbox.center().x(),
            self.pet.y() + hitbox.center().y()
        )
        my_center: Optional[QPointF] = centers.get(self.pet) if centers else fallback_center
        
        repel_x, repel_y = 0.0, 0.0
        
        # Base the minimum distance on the physical hitbox width
        min_dist: float = hitbox.width() * 0.6
        
        for other in self.pet.pet_manager.active_pets:
            if other is self.pet or other.is_dead: continue
            
            other_center = centers.get(other) if centers else other.geometry().center()
            if other_center is None or my_center is None: continue
            dx: float = my_center.x() - other_center.x()
            dy: float = my_center.y() - other_center.y()
            dist: float = math.hypot(dx, dy)
            
            if 0 < dist < min_dist:
                force: float = (min_dist - dist) / min_dist
                repel_x += (dx / dist) * force * (current_move_speed * 1.5)
                
                if self.pet.mod_manager.can_fly:
                    repel_y += (dy / dist) * force * (current_move_speed * 1.5)
                    
        if repel_x != 0 or repel_y != 0:
            new_x: float = self.pet.x() + repel_x
            new_y: float = self.pet.y() + repel_y if self.pet.mod_manager.can_fly else self.pet.y()
            self.pet.setPos(new_x, new_y)

    def _tick_movement(self, current_move_speed: float) -> None:
        if (
            self.pet is None or
            self.pet.mod_manager is None or
            self.pet.anim_sys is None
        ):
            return
        if self.pet.state is not PetState.MOVING or self.pet._target_pos is None: return
        
        curr_x, curr_y = self.pet.x(), self.pet.y()
        target_x: float = float(self.pet._target_pos.x())
        target_y: float = float(self.pet._target_pos.y()) if self.pet.mod_manager.can_fly else curr_y

        dx, dy = target_x - curr_x, target_y - curr_y
        dist: float = math.hypot(dx, dy)

        if dist < max(current_move_speed, 5.0):
            self.pet.setPos(target_x, target_y)
            self.pet._target_pos = None
            self.pet.sprite_rotation = 0.0
            self.pet.anim_sys.set_state(PetState.IDLE)
        else:
            step_x: float = curr_x + (dx / dist) * current_move_speed
            step_y: float = curr_y + (dy / dist) * current_move_speed if self.pet.mod_manager.can_fly else curr_y
            
            # Only flip the sprite if the pet is actually moving a noticeable distance horizontally
            if abs(dx) > 1: self.pet.facing_left = (dx < 0)
            
            if self.pet.mod_manager.can_fly and dist > 5.0:
                self.pet.sprite_rotation = math.degrees(math.atan2(dy, abs(dx) if dx != 0 else 0.1))
            
            self.pet.setPos(step_x, step_y)

    def _tick_gravity_and_collisions(self, ground_y: float, current_gravity: float) -> None:
        if (
            self.pet is None or
            self.pet.mod_manager is None or
            self.pet.anim_sys is None
        ):
            return
        if self.pet.mod_manager.can_fly and not self.pet.is_dead: return
        
        hitbox: QRect = self.pet.current_hitbox
        hitbox_bottom_offset: int = hitbox.y() + hitbox.height()
        pet_bottom: float = self.pet.y() + hitbox_bottom_offset
        
        if pet_bottom < ground_y or self.pet.velocity_y < 0:
            self.pet.velocity_y += current_gravity
            new_y: float = self.pet.y() + self.pet.velocity_y
            
            # Snap to the ground if the next frame's velocity pushes the hitbox through the floor
            if new_y + hitbox_bottom_offset > ground_y:
                new_y = ground_y - hitbox_bottom_offset
                self.pet.velocity_y = 0
                if self.pet.state is PetState.JUMPING and not self.pet.is_dead:
                    self.pet.anim_sys.set_state(PetState.IDLE)
                    
            self.pet.setPos(self.pet.x(), new_y)
        else:
            self.pet.velocity_y = 0
            if self.pet.state is PetState.JUMPING and not self.pet.is_dead:
                self.pet.anim_sys.set_state(PetState.IDLE)
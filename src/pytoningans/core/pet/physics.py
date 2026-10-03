from __future__ import annotations

import math

from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QScreen

from pytoningans.core.constants import PetState

if TYPE_CHECKING:
    from pytoningans.core.pet.window import PetWindow

class PhysicsSystem:
    def __init__(self, pet: Optional[PetWindow] = None) -> None:
        self.pet: Optional[PetWindow] = pet
        self.gravity: float = 0.8
        self.move_speed: float = 2.0

    def update(self, dt: int, centers: Optional[dict[PetWindow, QPoint]] = None) -> None:
        """Processes physics calculations based on elapsed time."""
        if self.pet is None: return
        if not self.pet.locks.physics:
            self.pet.velocity_y = 0
            return

        screen: QScreen = self.pet.screen()
        if not screen: return

        ground_y: int = screen.availableGeometry().bottom()
        
        time_scale: float = dt / 16.0
        current_gravity: float = self.gravity * time_scale
        current_move_speed: float = self.move_speed * time_scale

        self._tick_gravity_and_collisions(ground_y, current_gravity)

        if self.pet.is_dead: return

        self._tick_soft_collision(current_move_speed, centers)
        self._tick_movement(current_move_speed)

    def _tick_soft_collision(
        self, current_move_speed: float, centers: Optional[dict[PetWindow, QPoint]]= None
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
        # Use the hitbox center instead of the window geometry center
        my_center: Optional[QPoint] = centers.get(self.pet) if centers else self.pet.pos() + hitbox.center()
        repel_x, repel_y = 0.0, 0.0
        
        # Base the minimum distance on the physical hitbox width
        min_dist: float = hitbox.width() * 0.6
        
        for other in self.pet.pet_manager.active_pets:
            if other is self.pet or other.is_dead: continue
            
            other_center = centers.get(other) if centers else other.geometry().center()
            if other_center is None or my_center is None: continue
            dx: int = my_center.x() - other_center.x()
            dy: int = my_center.y() - other_center.y()
            dist: float = math.hypot(dx, dy)
            
            if 0 < dist < min_dist:
                force = (min_dist - dist) / min_dist
                repel_x += (dx / dist) * force * (current_move_speed * 1.5)
                
                if self.pet.mod_manager.can_fly:
                    repel_y += (dy / dist) * force * (current_move_speed * 1.5)
                    
        if repel_x != 0 or repel_y != 0:
            new_x: int = int(self.pet.x() + repel_x)
            new_y: int = int(self.pet.y() + repel_y) if self.pet.mod_manager.can_fly else self.pet.y()
            self.pet.move(new_x, new_y)

    def _tick_movement(self, current_move_speed: float) -> None:
        if (
            self.pet is None or
            self.pet.mod_manager is None or
            self.pet.anim_sys is None
        ):
            return
        if self.pet.state is not PetState.MOVING or self.pet._target_pos is None: return
        
        curr_x, curr_y = self.pet.x(), self.pet.y()
        target_x: int = self.pet._target_pos.x()
        target_y: int = self.pet._target_pos.y() if self.pet.mod_manager.can_fly else curr_y

        dx, dy = target_x - curr_x, target_y - curr_y
        dist: float = math.hypot(dx, dy)

        if dist < max(current_move_speed, 5.0):
            self.pet.move(target_x, target_y)
            self.pet._target_pos = None
            self.pet.rotation = 0.0
            self.pet.anim_sys.set_state(PetState.IDLE)
        else:
            step_x = int(curr_x + (dx / dist) * current_move_speed)
            step_y = int(curr_y + (dy / dist) * current_move_speed) if self.pet.mod_manager.can_fly else curr_y
            
            # Only flip the sprite if the pet is actually moving a noticeable distance horizontally
            if abs(dx) > 1.0:
                self.pet.facing_left = (dx < 0)
            
            if self.pet.mod_manager.can_fly and dist > 5.0:
                self.pet.rotation = math.degrees(math.atan2(dy, abs(dx) if dx != 0 else 0.1))
            
            self.pet.move(step_x, step_y)

    def _tick_gravity_and_collisions(self, ground_y: int, current_gravity: float) -> None:
        if (
            self.pet is None or
            self.pet.mod_manager is None or
            self.pet.anim_sys is None
        ):
            return
        if self.pet.mod_manager.can_fly and not self.pet.is_dead: return
        
        hitbox = self.pet.current_hitbox
        hitbox_bottom_offset = hitbox.y() + hitbox.height()
        pet_bottom: int = self.pet.y() + hitbox_bottom_offset
        
        if pet_bottom < ground_y or self.pet.velocity_y < 0:
            self.pet.velocity_y += current_gravity
            new_y = int(self.pet.y() + self.pet.velocity_y)
            
            # Snap to the ground if the next frame's velocity pushes the hitbox through the floor
            if new_y + hitbox_bottom_offset > ground_y:
                new_y = ground_y - hitbox_bottom_offset + 1
                self.pet.velocity_y = 0
                if self.pet.state is PetState.JUMPING and not self.pet.is_dead:
                    self.pet.anim_sys.set_state(PetState.IDLE)
                    
            self.pet.move(self.pet.x(), new_y)
        else:
            self.pet.velocity_y = 0
            if self.pet.state is PetState.JUMPING and not self.pet.is_dead:
                self.pet.anim_sys.set_state(PetState.IDLE)
from __future__ import annotations

import math

from typing import TYPE_CHECKING

from pytoningans.core.constants import PetState

if TYPE_CHECKING:
    from pytoningans.core.pet.window import PetWindow

class PhysicsSystem:
    def __init__(self, pet: PetWindow) -> None:
        self.pet = pet
        self.gravity = 0.8
        self.move_speed = 2.0

    def update(self, dt: int) -> None:
        """Processes physics calculations based on elapsed time."""
        if not self.pet.enable_gravity:
            self.pet.velocity_y = 0
            return

        screen = self.pet.screen()
        if not screen: return

        ground_y = screen.availableGeometry().bottom()
        
        # Normalize delta time against the expected 60 FPS (~16.6ms)
        time_scale = dt / 16.0 
        current_gravity = self.gravity * time_scale
        current_move_speed = self.move_speed * time_scale

        self.tick_gravity_and_collisions(ground_y, current_gravity)

        if self.pet.is_dead: return
        if self.tick_interaction(): return

        self.pet.ai_sys.check_interactions()
        self.tick_movement(current_move_speed)

    def tick_interaction(self) -> bool:
        """Returns True if Pet is already Interacting."""
        if self.pet.state is PetState.INTERACT:
            self.pet.ai_sys.interact_time_left -= 1
            if self.pet.ai_sys.interact_time_left <= 0:
                self.pet.anim_sys.set_state(PetState.IDLE)
            return True
        return False

    def tick_movement(self, current_move_speed: float) -> None:
        if self.pet.state is not PetState.MOVING or self.pet._target_pos is None: return
        curr_x, curr_y = self.pet.x(), self.pet.y()
        target_x = self.pet._target_pos.x()
        target_y = self.pet._target_pos.y() if self.pet.mod_manager.can_fly else curr_y

        dx, dy = target_x - curr_x, target_y - curr_y
        dist = math.hypot(dx, dy)

        if dist < current_move_speed:
            self.pet.move(target_x, target_y)
            self.pet._target_pos = None
            self.pet.anim_sys.set_state(PetState.IDLE)
        else:
            step_x = int(curr_x + (dx / dist) * current_move_speed)
            step_y = int(curr_y + (dy / dist) * current_move_speed) if self.pet.mod_manager.can_fly else curr_y
            
            self.pet.facing_left = (dx < 0)
            self.pet.move(step_x, step_y)

    def tick_gravity_and_collisions(self, ground_y: int, current_gravity: float) -> None:
        if self.pet.mod_manager.can_fly: return
        pet_bottom = self.pet.geometry().bottom()
        
        if pet_bottom < ground_y or self.pet.velocity_y < 0:
            self.pet.velocity_y += current_gravity
            new_y = int(self.pet.y() + self.pet.velocity_y)
            
            if new_y + self.pet.height() > ground_y:
                new_y = ground_y - self.pet.height() + 1
                self.pet.velocity_y = 0
                if self.pet.state is PetState.JUMPING and not self.pet.is_dead:
                    self.pet.anim_sys.set_state(PetState.IDLE)
                    
            self.pet.move(self.pet.x(), new_y)
        else:
            self.pet.velocity_y = 0
            if self.pet.state is PetState.JUMPING and not self.pet.is_dead:
                self.pet.anim_sys.set_state(PetState.IDLE)
from __future__ import annotations

import math

from typing import TYPE_CHECKING
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication

from pytoningans.core.constants import PetState

if TYPE_CHECKING:
    from pytoningans.core.pet.window import PetWindow

class PhysicsSystem:
    def __init__(self, pet: PetWindow) -> None:
        self.pet = pet
        self.gravity = 0.8
        self.move_speed = 2.0
        
        self.timer = QTimer(self.pet)
        self.timer.timeout.connect(self._physics_tick)
        self.timer.start(16) # ~60 FPS

    def _physics_tick(self) -> None:
        if not self.pet.enable_gravity:
            self.pet.velocity_y = 0
            return

        screen = QGuiApplication.screenAt(self.pet.geometry().center()) or QGuiApplication.primaryScreen()
        if not screen: return

        ground_y = screen.availableGeometry().bottom()

        # Gravity & Collision
        if not self.pet.mod_manager.can_fly:
            pet_bottom = self.pet.geometry().bottom()
            
            if pet_bottom < ground_y or self.pet.velocity_y < 0:
                self.pet.velocity_y += self.gravity
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

        if self.pet.is_dead: return

        # Interaction Timer
        if self.pet.state is PetState.INTERACT:
            self.pet.ai_sys.interact_ticks_left -= 1
            if self.pet.ai_sys.interact_ticks_left <= 0:
                self.pet.anim_sys.set_state(PetState.IDLE)
            return

        self.pet.ai_sys.check_interactions()

        # Movement Execution
        if self.pet.state is PetState.MOVING and self.pet._target_pos is not None:
            curr_x, curr_y = self.pet.x(), self.pet.y()
            target_x = self.pet._target_pos.x()
            target_y = self.pet._target_pos.y() if self.pet.mod_manager.can_fly else curr_y

            dx, dy = target_x - curr_x, target_y - curr_y
            dist = math.hypot(dx, dy)

            if dist < self.move_speed:
                self.pet.move(target_x, target_y)
                self.pet._target_pos = None
                self.pet.anim_sys.set_state(PetState.IDLE)
            else:
                step_x = int(curr_x + (dx / dist) * self.move_speed)
                step_y = int(curr_y + (dy / dist) * self.move_speed) if self.pet.mod_manager.can_fly else curr_y
                
                self.pet.facing_left = (dx < 0)
                self.pet.move(step_x, step_y)
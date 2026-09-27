from __future__ import annotations

import random, math

from typing import TYPE_CHECKING
from PySide6.QtCore import QTimer, QPoint
from PySide6.QtGui import QGuiApplication

from pytoningans.core.constants import PetState

if TYPE_CHECKING:
    from pytoningans.core.pet.window import PetWindow

class AISystem:
    def __init__(self, pet: PetWindow) -> None:
        self.pet = pet
        self.interaction_cooldown: int = 0
        self.interact_ticks_left: int = 0
        
        self.timer = QTimer(self.pet)
        self.timer.timeout.connect(self._ai_decision_tick)
        self.timer.start(2500)

    def _ai_decision_tick(self) -> None:
        if self.pet.state in (PetState.DRAG, PetState.INTERACT): return

        # --- MODDER API HOOK ---
        if self.pet.mod_manager.custom_behavior and hasattr(self.pet.mod_manager.custom_behavior, "on_decision_tick"):
            try:
                self.pet.mod_manager.custom_behavior.on_decision_tick(self.pet)
                return
            except Exception as e:
                print(f"Custom AI Error (Decision): {e}")

        # --- DEFAULT LOGIC ---
        screen = QGuiApplication.screenAt(self.pet.geometry().center()) or QGuiApplication.primaryScreen()
        if not screen: return

        if not self.pet.mod_manager.can_fly and random.random() < 0.15:
            self.pet.jump()
            return

        geom = screen.availableGeometry()

        if random.random() < 0.60:
            dest_x = random.randint(geom.left() + 50, geom.right() - self.pet.width() - 50)
            if self.pet.mod_manager.can_fly:
                dest_y = random.randint(geom.top() + 50, geom.bottom() - self.pet.height() - 50)
            else:
                dest_y = self.pet.y()

            self.pet.target_pos = QPoint(dest_x, dest_y)
            self.pet.anim_sys.set_state(PetState.MOVING)
        else:
            self.pet.target_pos = None
            self.pet.anim_sys.set_state(PetState.IDLE)

    def check_interactions(self) -> None:
        if self.interaction_cooldown > 0:
            self.interaction_cooldown -= 1
            return

        if not self.pet.is_interactable: return

        my_center = self.pet.geometry().center()

        for other_pet in self.pet.pet_manager.active_pets:
            if other_pet is self.pet or not other_pet.is_interactable: continue

            other_center = other_pet.geometry().center()
            distance = math.hypot(my_center.x() - other_center.x(), my_center.y() - other_center.y())

            if distance < 120:
                # --- MODDER API HOOK ---
                if self.pet.mod_manager.custom_behavior and hasattr(self.pet.mod_manager.custom_behavior, "on_interact"):
                    try:
                        self.pet.mod_manager.custom_behavior.on_interact(self.pet, other_pet)
                        break
                    except Exception as e:
                        print(f"Custom AI Error (Interact): {e}")
                
                # --- DEFAULT LOGIC ---
                self.pet.facing_left = other_center.x() < my_center.x()
                other_pet.facing_left = my_center.x() < other_center.x()

                self.start_interaction()
                other_pet.ai_sys.start_interaction()
                break

    def start_interaction(self) -> None:
        self.pet.target_pos = None
        self.interact_ticks_left = 180
        self.interaction_cooldown = 400
        self.pet.anim_sys.set_state(PetState.INTERACT)
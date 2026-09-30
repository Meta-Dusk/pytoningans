from __future__ import annotations

import random, math

from typing import TYPE_CHECKING, cast, Optional, List
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QScreen

from pytoningans.core.constants import PetState, BehaviorType
from pytoningans.core.api import BasePetBehavior, IPet
from pytoningans.core.pet.speech_bubble import SpeechBubble

if TYPE_CHECKING:
    from pytoningans.core.pet.window import PetWindow

class AISystem:
    def __init__(self, pet: Optional[PetWindow] = None) -> None:
        self.pet: Optional[PetWindow] = pet
        
        # State Durations (in milliseconds)
        self.decision_accumulator: int = 0
        
        self.interact_time_left: int = 0
        self.interaction_cooldown: int = 0
        
        self.attack_time_left: int = 0
        self.attack_cooldown: int = 0
    
    def update(self, dt: int, centers: Optional[dict[PetWindow, QPoint]] = None) -> None:
        """Processes AI logic based on elapsed time.

        Args:
            dt (int): Delta time
            centers (dict[PetWindow, QPoint] | None): The centers of each active pet
        """
        if self.pet is None or self.pet.anim_sys is None: return
        self.decision_accumulator += dt
        
        # Decrement cooldowns
        if self.interaction_cooldown > 0: self.interaction_cooldown -= dt
        if self.attack_cooldown > 0: self.attack_cooldown -= dt
        
        # Freeze AI logic while performing actions, but tick down their duration
        if self.pet.state is PetState.INTERACT:
            self.interact_time_left -= dt
            if self.interact_time_left <= 0:
                self.pet.anim_sys.set_state(PetState.IDLE)
            return
            
        if self.pet.state is PetState.ATTACK:
            self.attack_time_left -= dt
            if self.attack_time_left <= 0:
                self.pet.anim_sys.set_state(PetState.IDLE)
            return

        # Trigger roaming AI every 2.5 seconds
        if self.decision_accumulator >= 2500:
            self.decision_accumulator = 0
            if self._check_environment(): return
            self._ai_decision_tick()
            
        # Priority 1: Check for enemies in range
        self.check_combat(centers)
        
        # Priority 2: Check for neutral interactions if not already attacking
        if self.pet.state is not PetState.ATTACK:
            self.check_interactions()
    
    def _ai_decision_tick(self) -> None:
        if self.pet is None: return
        if self.pet.state in (PetState.DRAG, PetState.INTERACT): return
        if self._on_ai_decision_tick(): return  # Modder API hook
        self._default_ai_decision()             # Default logic

    def _default_ai_decision(self) -> None:
        if (
            self.pet is None or
            self.pet.mod_manager is None or
            self.pet.anim_sys is None
            
        ): return
        if not self.pet.mod_manager.can_fly and random.random() < 0.15:
            self.pet.jump()
            return
        
        screen: QScreen = self.pet.screen()
        if not screen: return
        geom: QRect = screen.availableGeometry()

        if random.random() < 0.60:
            dest_x = random.randint(geom.left() + 50, geom.right() - self.pet.width() - 50)
            if self.pet.mod_manager.can_fly:
                dest_y = random.randint(geom.top() + 50, geom.bottom() - self.pet.height() - 50)
            else:
                dest_y = self.pet.y()

            self.pet._target_pos = QPoint(dest_x, dest_y)
            self.pet.anim_sys.set_state(PetState.MOVING)
        else:
            self.pet._target_pos = None
            self.pet.anim_sys.set_state(PetState.IDLE)
    
    def _on_ai_decision_tick(self) -> bool:
        """Returns True if the AI decision should end."""
        if self.pet is None or self.pet.mod_manager is None: return False
        behavior: Optional[BasePetBehavior] = self.pet.mod_manager.custom_behavior
        if behavior is None: return False
        try:
            # If the modder returns True, skip the default roaming logic
            pet_api: IPet = cast(IPet, self.pet)
            if behavior.on_decision_tick(pet_api): return True
        except Exception as e:
            print(f"Custom AI Error (Decision): {e}")
            
        return False
    
    def check_combat(self, centers: Optional[dict[PetWindow, QPoint]] = None) -> None:
        if (
            self.pet is None or
            self.pet.mod_manager is None or
            self.pet.pet_manager is None
        ): return
        # Only HOSTILE pets initiate attacks
        if self.pet.mod_manager.behavior_type is not BehaviorType.HOSTILE:
            return
        
        if self.attack_cooldown > 0 or not self.pet.is_interactable: 
            return

        my_center = centers.get(self.pet) if centers else self.pet.geometry().center()

        for other_pet in self.pet.pet_manager.active_pets:
            if (
                other_pet is self.pet or not
                other_pet.is_interactable or
                other_pet is None or
                other_pet.mod_manager is None or
                other_pet.pet_manager is None
            ):
                continue
            
            # TODO: Add aggresion modifiers soon
            # Prevent Hostiles from attacking other pets of the exact same mod (friendly fire)
            if other_pet.mod_manager.current_mod_name == self.pet.mod_manager.current_mod_name:
                continue
            
            other_center = centers.get(other_pet) if centers else other_pet.geometry().center()
            if other_center is None or my_center is None: continue
            distance: float = self._get_distance(my_center, other_center)

            # Evaluate against the mod's specific attack range
            if distance > self.pet.mod_manager.attack_range: continue
            
            # --- MODDER API HOOK ---
            override_default: bool = self._on_combat_check(other_pet)

            # --- DEFAULT COMBAT LOGIC ---
            if not override_default:
                self._default_combat_logic(my_center, other_pet, other_center)
                    
            break # Only initiate one attack per tick

    def _get_distance(self, my_center: QPoint, other_center: QPoint) -> float:
        return math.hypot(my_center.x() - other_center.x(), my_center.y() - other_center.y())

    def _default_combat_logic(
        self, my_center: QPoint, other_pet: PetWindow, other_center: QPoint
    ) -> None:
        if (
            self.pet is None or
            self.pet.mod_manager is None or
            self.pet.anim_sys is None
        ): return
        dx: int = other_center.x() - my_center.x()
        dy: int = other_center.y() - my_center.y()
                
        self.pet.facing_left = (dx < 0)
                
        if self.pet.mod_manager.can_fly:
            self.pet.rotation = math.degrees(math.atan2(dy, abs(dx) if dx != 0 else 0.1))
                
        other_pet.take_damage(self.pet.mod_manager.attack_damage)
                
        # Start attack animation (lasts 800ms) with a 2-second cooldown
        self.pet._target_pos = None
        self.attack_time_left = 800 
        self.attack_cooldown = 2000 
        self.pet.anim_sys.set_state(PetState.ATTACK)

    def _on_combat_check(self, other_pet: PetWindow) -> bool:
        """Modder API hook."""
        if self.pet is None or self.pet.mod_manager is None: return False
        if not self.pet.mod_manager.custom_behavior: return False
        try:
            pet_api: IPet = cast(IPet, self.pet)
            other_api: IPet = cast(IPet, other_pet)
            return self.pet.mod_manager.custom_behavior.on_attack(pet_api, other_api)
        except Exception as e:
            print(f"Custom AI Error (Attack): {e}")
        return False
    
    def check_interactions(self, centers: Optional[dict[PetWindow, QPoint]] = None) -> None:
        # TODO: Add sociability modifiers soon
        # PASSIVE pets do not initiate social interactions
        if (
            self.pet is None or
            self.pet.mod_manager is None or
            self.pet.mod_manager.behavior_type is BehaviorType.PASSIVE or
            self.pet.pet_manager is None
        ): return
        
        if self.interaction_cooldown > 0:
            self.interaction_cooldown -= 1
            return

        if not self.pet.is_interactable: return

        my_center = centers.get(self.pet) if centers else self.pet.geometry().center()

        for other_pet in self.pet.pet_manager.active_pets:
            if (
                other_pet.ai_sys is None or
                other_pet is self.pet or not
                other_pet.is_interactable
            ): continue

            other_center = centers.get(other_pet) if centers else other_pet.geometry().center()
            if other_center is None or my_center is None: continue
            distance: float = self._get_distance(my_center, other_center)

            if distance >= 120: return
            # --- MODDER API HOOK ---
            override_default: bool = self._on_check_interactions(other_pet)
            
            # --- DEFAULT LOGIC ---
            if not override_default:
                self.pet.facing_left = other_center.x() < my_center.x()
                other_pet.facing_left = my_center.x() < other_center.x()
                self.start_interaction()
                other_pet.ai_sys.start_interaction()
                
            break

    def _on_check_interactions(self, other_pet: PetWindow) -> bool:
        if (
            self.pet is None or
            self.pet.mod_manager is None or
            self.pet.mod_manager.custom_behavior is None
        ): return False
        try:
            pet_api: IPet = cast(IPet, self.pet)
            other_pet_api: IPet = cast(IPet, other_pet)
            return self.pet.mod_manager.custom_behavior.on_interact(pet_api, other_pet_api)
        except Exception as e:
            print(f"Custom AI Error (Interact): {e}")
        return False

    def start_interaction(self) -> None:
        if self.pet is None or self.pet.anim_sys is None: return
        self.pet._target_pos = None
        self.interact_time_left = 3000 
        self.interaction_cooldown = 6000
        self.pet.anim_sys.set_state(PetState.INTERACT)
    
    def _check_environment(self) -> bool:
        """Evaluates active windows and triggers personality dialogue. Returns True if speaking."""
        if (
            self.pet is None or
            self.pet.mod_manager is None or
            self.pet.pet_manager is None
        ): return False
        
        # Prevent overlapping dialogues
        if self.pet.bubble is not None and self.pet.bubble.isVisible():
            return False
        
        if random.random() < 0.5: return False
            
        windows: List[str] = self.pet.pet_manager.active_window_titles
        
        # --- Dynamic Environmental Triggers ---
        for trigger in self.pet.mod_manager.window_triggers:
            matches: List[str] = trigger.get("title_matches", [])
            chance: float = trigger.get("chance", 1.0)
            
            # Check if ANY of the trigger words are in ANY of the open windows (case-insensitive)
            if any(m.lower() in w.lower() for m in matches for w in windows):
                if random.random() < chance:
                    text: str = trigger.get("text", "...")
                    duration: int = trigger.get("duration", 4000)
                    self._trigger_dialogue(text, duration)
                    return True

        # --- Random Plain Dialogue ---
        if random.random() < 0.05 and self.pet.mod_manager.plain_dialogue:
            text: str = random.choice(self.pet.mod_manager.plain_dialogue)
            self._trigger_dialogue(text, 3000)
            return True
            
        return False
        
    def _trigger_dialogue(self, text: str, duration_ms: int) -> None:
        """Helper to push text to the UI and freeze movement."""
        if self.pet is None or self.pet.anim_sys is None: return
        if self.pet.bubble is None:
            self.pet.bubble = SpeechBubble(self.pet)
            
        self.pet.bubble.speak(text, duration_ms)
        self.pet.anim_sys.set_state(PetState.IDLE)
        self.pet._target_pos = None
        self.pet.bubble.update_position()
        self.pet.raise_()
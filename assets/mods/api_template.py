"""
PyToNingans Modding API Reference
Open the 'mods' folder as a workspace in VS Code for full autocompletion.
"""
from typing import Protocol, Optional, List
from enum import StrEnum, unique
from dataclasses import dataclass

@dataclass
class Pos2D:
    x: int
    y: int

@unique
class PetState(StrEnum):
    """The current animation and behavioral state of the pet."""
    DRAG = "drag"
    IDLE = "idle"
    CLICKED = "clicked"
    INTERACT = "interact"
    MOVING = "moving"
    JUMPING = "jumping"
    DYING = "dying"
    CLIMBING = "climbing"
    REVIVING = "reviving"
    ATTACK = "attack"

@unique
class BehaviorType(StrEnum):
    PASSIVE = "passive"
    NEUTRAL = "neutral"
    HOSTILE = "hostile"

class IPetManager(Protocol):
    """Provides access to the global pet ecosystem."""
    active_pets: List['IPet']
    
    def spawn_pet(self, x: int, y: int, mod_folder: str) -> None:
        """Spawns a new pet at the target coordinates using the specified mod."""
        ...

    def remove_pet(self, pet: 'IPet') -> None:
        """Despawns and removes a pet from the screen."""
        ...

class IPet(Protocol):
    """
    The primary interface for manipulating a pet inside `behavior.py`.
    """
    # Properties
    x: int
    y: int
    state: PetState
    is_dead: bool
    current_health: int
    target_pos: Optional[Pos2D]
    facing_left: bool
    behavior_type: BehaviorType
    
    # Access to the global manager
    pet_manager: IPetManager
    
    def jump(self) -> None:
        """Forces the pet to jump. Ignored if dead or if the pet can fly."""
        ...
    
    def take_damage(self, amount: int) -> None:
        """Reduces the pet's health by the specified amount and triggers a red flash."""
        ...

    def die(self) -> None:
        """Immediately kills the pet, stopping AI and playing the death animation."""
        ...

    def revive(self) -> None:
        """Restores the pet to full health and resumes AI processing."""
        ...

    def move(self, x: int, y: int) -> None:
        """Teleports the pet instantly to the absolute screen coordinates."""
        ...
        
    def width(self) -> int:
        """Returns the current pixel width of the pet's sprite."""
        ...
        
    def height(self) -> int:
        """Returns the current pixel height of the pet's sprite."""
        ...

class BasePetBehavior:
    """
    Inherit from this class in your behavior.py to define custom AI.
    """
    def on_spawn(self, pet: IPet) -> None:
        """Triggered exactly once when the pet is spawned."""
        pass

    def on_decision_tick(self, pet: IPet) -> bool:
        """
        Triggered every 2.5 seconds. 
        Return True to block the default wandering AI.
        """
        return False

    def on_interact(self, pet: IPet, other_pet: IPet) -> bool:
        """
        Triggered when touching another interactable pet.
        Return True to block the default facing/pausing interaction.
        """
        return False

    def on_death(self, pet: IPet) -> None:
        """Triggered instantly when the pet's health reaches 0."""
        pass
    
    def on_revive(self, pet: IPet) -> None:
        """Triggered when a pet who was once dead, is no longer."""
        pass
    
    def on_attack(self, pet: IPet, target: IPet) -> bool:
        """
        Triggered when a target enters attack range.
        Return True to block the default damage and attack animation.
        """
        return False
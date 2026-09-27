import random

from PySide6.QtCore import QPoint
from pytoningans.core.constants import PetState

# TODO: Test auto-completion in modding environment

def on_decision_tick(pet):
    """
    A custom behavior script where the pet is hyperactive:
    It never idles, jumps extremely often, and runs in small bursts.
    """
    # 50% chance to jump
    if random.random() < 0.50:
        pet.jump()
    
    # Always pick a target nearby
    target_x = pet.x() + random.randint(-150, 150)
    
    # Set the target and enforce the MOVING state
    pet.target_pos = QPoint(target_x, pet.y())
    pet.anim_sys.set_state(PetState.MOVING)

def on_interact(pet, other_pet):
    """Custom interaction: Instantly kills the other pet on contact!"""
    other_pet.die()
    
    # Do a little jump to celebrate
    pet.jump()
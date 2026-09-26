from typing import List

from pytoningans.ui.pet_window import PetWindow
from pytoningans.core.mod_manager import ModManager

class PetManager:
    def __init__(self, mod_manager: ModManager) -> None:
        self.mod_manager: ModManager = mod_manager
        self.active_pets: List[PetWindow] = []

    def spawn_pet(self, x: int, y: int) -> None:
        # Pass the global mod manager to the new window
        pet: PetWindow = PetWindow(x, y, self.mod_manager)
        pet.show()
        self.active_pets.append(pet)
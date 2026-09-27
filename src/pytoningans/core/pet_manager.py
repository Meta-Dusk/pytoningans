from typing import List, cast

from pytoningans.core.pet.window import PetWindow
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.api import IPet

class PetManager:
    def __init__(self, mod_manager: ModManager) -> None:
        self.mod_manager: ModManager = mod_manager
        self.active_pets: List[PetWindow] = []

    def spawn_pet(self, x: int, y: int, mod_folder: str) -> None:
        pet_mod = ModManager(self.mod_manager.mods_dir)
        pet_mod.load_mod(mod_folder)
        
        pet: PetWindow = PetWindow(x, y, pet_mod, self)
        pet.show()
        
        # --- MODDER API HOOK ---
        pet_api = cast(IPet, pet)
        if pet.mod_manager.custom_behavior:
            pet.mod_manager.custom_behavior.on_spawn(pet_api)
            
        self.active_pets.append(pet)
    
    def remove_pet(self, pet: PetWindow) -> None:
        """Unregisters the pet from memory when closed."""
        if pet in self.active_pets:
            self.active_pets.remove(pet)
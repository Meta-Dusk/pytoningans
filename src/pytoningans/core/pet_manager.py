from typing import List, cast

from PySide6.QtCore import QTimer, QElapsedTimer

from pytoningans.core.pet.window import PetWindow
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.api import IPet
from pytoningans.core.pet.animation import AnimationSystem
from pytoningans.core.mod_manager import ModManager

class PetManager:
    def __init__(self, mod_manager: ModManager) -> None:
        self.mod_manager: ModManager = mod_manager
        self.active_pets: List[PetWindow] = []
        
        # Central Game Loop
        self.clock = QElapsedTimer()
        self.timer = QTimer()
        self.timer.timeout.connect(self._global_tick)
        
        # ~60 FPS (1000ms / 60 = ~16.6ms)
        self.timer.start(16) 
        self.clock.start()

    def _global_tick(self) -> None:
        """The heartbeat of the entire application."""
        dt = self.clock.restart()
        
        # Update all systems for all active pets
        for pet in list(self.active_pets):
            pet.update_systems(dt)

    def spawn_pet(self, x: int, y: int, mod_folder: str) -> None:
        pet_mod = ModManager(self.mod_manager.mods_dir)
        pet_mod.load_mod(mod_folder)
        
        pet: PetWindow = PetWindow(x, y, pet_mod, self)
        pet.show()
        
        self._on_spawn(pet)
        self.active_pets.append(pet)

    def _on_spawn(self, pet: PetWindow) -> None:
        """Modding API hook."""
        pet_api: IPet = cast(IPet, pet)
        if pet.mod_manager.custom_behavior:
            pet.mod_manager.custom_behavior.on_spawn(pet_api)
    
    def remove_pet(self, pet: PetWindow) -> None:
        """Unregisters the pet from memory when closed."""
        if pet in self.active_pets:
            self.active_pets.remove(pet)
        
        # Free up memory when the screen is completely empty
        if not self.active_pets:
            AnimationSystem.clear_shared_cache()
            ModManager.clear_shared_cache()
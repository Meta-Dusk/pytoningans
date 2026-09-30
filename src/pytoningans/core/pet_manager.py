import ctypes, gc
from typing import List, cast

from PySide6.QtCore import QTimer, QElapsedTimer, QRunnable, QThreadPool, QObject, Signal, QPoint

from pytoningans.core.pet.window import PetWindow
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.api import IPet
from pytoningans.core.pet.animation import AnimationSystem

def fetch_visible_windows_worker() -> List[str]:
    """Background worker function querying visible window titles."""
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    titles: List[str] = []

    def foreach_window(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                if buff.value:
                    titles.append(buff.value)
        return True

    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return titles


class VisionWorkerSignals(QObject):
    finished = Signal(list)


class VisionWorker(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = VisionWorkerSignals()

    def run(self) -> None:
        titles = fetch_visible_windows_worker()
        self.signals.finished.emit(titles)


class PetManager:
    def __init__(self, mod_manager: ModManager) -> None:
        self.mod_manager: ModManager = mod_manager
        self.active_pets: List[PetWindow] = []
        
        self.active_window_titles: List[str] = []
        self.vision_accumulator: int = 0
        self._vision_in_progress: bool = False
        
        # Central Game Loop
        self.clock = QElapsedTimer()
        self.timer = QTimer()
        self.timer.timeout.connect(self._global_tick)
        
        self.timer.start(16) 
        self.clock.start()

    def _on_vision_ready(self, titles: List[str]) -> None:
        self.active_window_titles = titles
        self._vision_in_progress = False

    def _global_tick(self) -> None:
        """The heartbeat of the entire application."""
        dt = self.clock.restart()
        
        # Trigger non-blocking OS polling every 3 seconds
        self.vision_accumulator += dt
        if self.vision_accumulator >= 3000:
            self.vision_accumulator = 0
            if not self._vision_in_progress:
                self._vision_in_progress = True
                worker = VisionWorker()
                worker.signals.finished.connect(self._on_vision_ready)
                QThreadPool.globalInstance().start(worker)

        # Pre-compute centers and positions once for all pets
        # This replaces redundant C++ geometry/center evaluations in the collision loop
        centers: dict[PetWindow, QPoint] = {
            pet: pet.geometry().center() for pet in self.active_pets
        }
        
        # Update all active pets
        for pet in list(self.active_pets):
            pet.update_systems(dt, centers)

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
        if pet.mod_manager is None: return
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
            gc.collect()
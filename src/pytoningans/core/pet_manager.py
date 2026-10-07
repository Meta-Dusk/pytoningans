import ctypes, gc
from ctypes import wintypes
from typing import List, cast, Optional

from PySide6.QtCore import QRectF, QTimer, QElapsedTimer, QRunnable, QThreadPool, QObject, Signal
from PySide6.QtGui import QPixmapCache, QGuiApplication, QScreen

from pytoningans.core.world import WorldOverlay
from pytoningans.core.pet.window import PetWindow
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.api import IPet
from pytoningans.core.pet.animation import AnimationSystem
from pytoningans.core.structure import TravelPortal

HTTRANSPARENT = -1
HTCLIENT = 1

def fetch_visible_windows_worker() -> list[str]:
    """Background worker function querying visible window titles safely."""
    user32 = ctypes.windll.user32
    
    # Explicitly define C-types for compiled environments
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL

    titles: list[str] = []

    def foreach_window(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if buff.value:
                    titles.append(buff.value)
        return True

    # Keep a strong reference to the callback during execution to prevent GC crashes
    callback = WNDENUMPROC(foreach_window)
    user32.EnumWindows(callback, 0)
    
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
    """The central nervous system managing active worlds and global loops."""
    def __init__(self, mod_manager: ModManager) -> None:
        self.mod_manager: ModManager = mod_manager
        
        self.active_worlds: list[WorldOverlay] = []
        self.active_pets: list[PetWindow] = []
        
        self.active_window_titles: list[str] = []
        self.vision_accumulator: int = 0
        self._vision_in_progress: bool = False
        self._vision_worker: Optional[VisionWorker] = None
        
        self.clock = QElapsedTimer()
        self.timer = QTimer()
        self.timer.timeout.connect(self._global_tick)
        
        self._init_worlds()
        
        self.timer.start(16)
        self.clock.start()

    def _init_worlds(self) -> None:
        """Sets up a WorldOverlay for every connected monitor and links them with portals."""
        screens: List[QScreen] = QGuiApplication.screens()
        
        # Generate an overlay for every monitor
        for screen in screens:
            world = WorldOverlay(screen, self)
            world.showFullScreen()
            self.active_worlds.append(world)
            
        # Link adjacent monitors with two-way Travel Portals
        for i in range(len(self.active_worlds) - 1):
            world_a: WorldOverlay = self.active_worlds[i]
            world_b: WorldOverlay = self.active_worlds[i + 1]
            
            wa_rect: QRectF = world_a.scene.sceneRect()
            wb_rect: QRectF = world_b.scene.sceneRect()
            
            # Floor level approximation (120 is portal height)
            ground_y_a: float = wa_rect.bottom() - 120
            ground_y_b: float = wb_rect.bottom() - 120
            
            # Portal A -> B (Placed on the right edge of Monitor A)
            portal_a = TravelPortal(wa_rect.right() - 80, ground_y_a, world_a, world_b)
            portal_a.exit_x = 100.0  # Exit on the left side of B
            portal_a.exit_y = ground_y_b
            
            world_a.scene.addItem(portal_a)
            world_a.active_structures.append(portal_a)
            
            # Portal B -> A (Placed on the left edge of Monitor B)
            portal_b = TravelPortal(20, ground_y_b, world_b, world_a)
            portal_b.exit_x = wa_rect.right() - 160.0  # Exit on the right side of A (in front of portal)
            portal_b.exit_y = ground_y_a
            
            world_b.scene.addItem(portal_b)
            world_b.active_structures.append(portal_b)

    def _on_vision_ready(self, titles: list[str]) -> None:
        self.active_window_titles = titles
        self._vision_in_progress = False

    def _global_tick(self) -> None:
        """The heartbeat of the entire application across all worlds."""
        dt: int = self.clock.restart()
        
        self.vision_accumulator += dt
        if self.vision_accumulator >= 3000:
            self.vision_accumulator = 0
            if not self._vision_in_progress:
                self._vision_in_progress = True
                self._vision_worker = VisionWorker()
                self._vision_worker.signals.finished.connect(self._on_vision_ready)
                QThreadPool.globalInstance().start(self._vision_worker)

        for world in self.active_worlds:
            world.update_systems(dt)

    def spawn_pet(self, x: int, y: int, mod_folder: str) -> None:
        pet_mod = ModManager(self.mod_manager.mods_dir)
        pet_mod.load_mod(mod_folder)
        
        # Default to spawning in the primary world for now
        target_world: Optional[WorldOverlay] = self.active_worlds[0] if self.active_worlds else None
        if not target_world: return
        
        # Pass the world instance to the PetWindow
        pet: PetWindow = PetWindow(x, y, pet_mod, self, target_world)
        
        # Mount the pet into the QGraphicsScene
        target_world.scene.addItem(pet)
        
        target_world.active_pets.append(pet)
        self.active_pets.append(pet)
        self._on_spawn(pet)

    def _on_spawn(self, pet: PetWindow) -> None:
        """Modding API hook."""
        pet_api: IPet = cast(IPet, pet)
        if pet.mod_manager is None: return
        if pet.mod_manager.custom_behavior:
            pet.mod_manager.custom_behavior.on_spawn(pet_api)
    
    def remove_pet(self, pet: PetWindow) -> None:
        """Unregisters the pet from memory and the scene when closed."""
        if pet in self.active_pets:
            self.active_pets.remove(pet)
            
        for world in self.active_worlds:
            if pet in world.active_pets:
                world.active_pets.remove(pet)
                world.scene.removeItem(pet)
                break
        
        # Free up memory when the screen is completely empty
        if not self.active_pets:
            AnimationSystem.clear_shared_cache()
            ModManager.clear_shared_cache()
            QPixmapCache.clear()
            gc.collect()
import ctypes, gc
from ctypes import wintypes
from typing import List, cast, Optional

from PySide6.QtCore import QRectF, QTimer, QElapsedTimer, QRunnable, QThreadPool, QObject, Signal
from PySide6.QtGui import QPixmapCache, QGuiApplication, QScreen

from pytoningans.core.world import WorldOverlay
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.api import IEntity, IStructure, BaseStructureBehavior, BaseEntityBehavior
from pytoningans.core.entity.base import BaseEntity, Entity, BaseStructure
from pytoningans.core.entity.animation import AnimationSystem
from pytoningans.core.structure import TravelPortal
from pytoningans.core.constants import EntityType

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


class EntityManager:
    """The central nervous system managing active worlds and global loops."""
    def __init__(self, mod_manager: ModManager) -> None:
        self.mod_manager: ModManager = mod_manager
        
        self.active_worlds: list[WorldOverlay] = []
        self.active_entities: list[Entity] = []
        self.active_structures: list[BaseStructure] = []
        
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
        """Sets up a `WorldOverlay` for every connected monitor and links them with portals."""
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
            
            portal_a = TravelPortal(wa_rect.right() - 80, ground_y_a, world_a, world_b)
            portal_a.exit_offset_x = 80.0  # Tells portal_b to spit out to the right
            
            world_a.scene.addItem(portal_a)
            world_a.active_structures.append(portal_a)
            self.active_structures.append(portal_a)
            
            portal_b = TravelPortal(20, ground_y_b, world_b, world_a)
            portal_b.exit_offset_x = -80.0 # Tells portal_a to spit out to the left
            
            world_b.scene.addItem(portal_b)
            world_b.active_structures.append(portal_b)
            self.active_structures.append(portal_b)
            
            # Form the two-way dynamic link
            portal_a.linked_portal = portal_b
            portal_b.linked_portal = portal_a

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

    def spawn_entity(self, x: float, y: float, mod_folder: str) -> None:
        """Dynamically spawns a living Pet or a static Structure based on mod config."""
        entity_mod = ModManager(self.mod_manager.mods_dir)
        entity_mod.load_mod(mod_folder)
        
        target_world = self.active_worlds[0] if self.active_worlds else None
        if not target_world: return
        
        # Route instantiation based on the declared entity type
        if entity_mod.entity_type == EntityType.STRUCTURE.value:
            entity = BaseStructure(x, y, entity_mod, target_world)
            target_world.scene.addItem(entity)
            target_world.active_structures.append(entity)
            self.active_structures.append(entity)
        else:
            entity = Entity(x, y, entity_mod, target_world, self)
            target_world.scene.addItem(entity)
            target_world.active_entities.append(entity)
            self.active_entities.append(entity)
            
        self._on_spawn(entity)

    def _on_spawn(self, entity: BaseEntity) -> None:
        if entity.mod_manager is None: return
        
        behavior: Optional[BaseEntityBehavior | BaseStructureBehavior] = entity.mod_manager.custom_behavior
        if behavior is None: return
        
        if isinstance(entity, Entity) and isinstance(behavior, BaseEntityBehavior):
            entity_api: IEntity = cast(IEntity, entity)
            behavior.on_spawn(entity_api)
            
        elif isinstance(entity, BaseStructure) and isinstance(behavior, BaseStructureBehavior):
            struct_api: IStructure = cast(IStructure, entity)
            behavior.on_spawn(struct_api)
    
    def remove_entity(self, entity: BaseEntity) -> None:
        # Remove from global tracking safely
        if isinstance(entity, Entity) and entity in self.active_entities:
            self.active_entities.remove(entity)
        elif isinstance(entity, BaseStructure) and entity in self.active_structures:
            self.active_structures.remove(entity)
            
        # Remove from the specific world it inhabits
        for world in self.active_worlds:
            if entity in world.active_entities:
                world.active_entities.remove(cast(Entity, entity))
                world.scene.removeItem(entity)
                break
            elif entity in world.active_structures:
                world.active_structures.remove(cast(BaseStructure, entity))
                world.scene.removeItem(entity)
                break
        
        # Memory cleanup only if NO entities exist at all
        if not self.active_entities and not self.active_structures:
            AnimationSystem.clear_shared_cache()
            ModManager.clear_shared_cache()
            QPixmapCache.clear()
            gc.collect()
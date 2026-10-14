import ctypes, gc, random
from ctypes import wintypes
from typing import cast, Optional

from PySide6.QtCore import QTimer, QElapsedTimer, QRunnable, QThreadPool, QObject, Signal
from PySide6.QtGui import QPixmapCache, QGuiApplication, QScreen

from pytoningans.core.entity.base_structure import BaseStructure
from pytoningans.core.entity.base_item import BaseItem
from pytoningans.core.entity.living_entity import Entity
from pytoningans.core.world import WorldOverlay
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.api import (
    IEntity, IStructure, IItem, BaseStructureBehavior, BaseEntityBehavior,
    BaseItemBehavior, BaseBehavior
)
from pytoningans.core.entity.base_entity import BaseEntity
from pytoningans.core.entity.animation import AnimationSystem
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
        self.active_items: list[BaseItem] = []
        
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
        screens: list[QScreen] = QGuiApplication.screens()
        
        # Generate an overlay for every monitor
        for screen in screens:
            world = WorldOverlay(screen, self)
            world.showFullScreen()
            self.active_worlds.append(world)
            
        # Link adjacent monitors with two-way Travel Portals
        # for i in range(len(self.active_worlds) - 1):
        #     world_a: WorldOverlay = self.active_worlds[i]
        #     world_b: WorldOverlay = self.active_worlds[i + 1]
            
        #     wa_rect: QRectF = world_a.scene.sceneRect()
        #     wb_rect: QRectF = world_b.scene.sceneRect()
            
        #     # Floor level approximation (120 is portal height)
        #     ground_y_a: float = wa_rect.bottom() - 120
        #     ground_y_b: float = wb_rect.bottom() - 120
            
        #     portal_a = TravelPortal(wa_rect.right() - 80, ground_y_a, world_a, world_b)
        #     portal_a.exit_offset_x = 80.0  # Tells portal_b to spit out to the right
            
        #     world_a.scene.addItem(portal_a)
        #     world_a.active_structures.append(portal_a)
        #     self.active_structures.append(portal_a)
            
        #     portal_b = TravelPortal(20, ground_y_b, world_b, world_a)
        #     portal_b.exit_offset_x = -80.0 # Tells portal_a to spit out to the left
            
        #     world_b.scene.addItem(portal_b)
        #     world_b.active_structures.append(portal_b)
        #     self.active_structures.append(portal_b)
            
        #     # Form the two-way dynamic link
        #     portal_a.linked_portal = portal_b
        #     portal_b.linked_portal = portal_a

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

    def spawn_entity(
        self, x: float, y: float, mod_folder: str, 
        target_world: Optional[WorldOverlay] = None,
        instance_name: Optional[str] = None
    ) -> Optional[BaseEntity]:
        """Dynamically spawns a living Entity or a static Structure based on mod config."""
        mod_manager = ModManager(self.mod_manager.mods_dir)
        mod_manager.load_mod(mod_folder)
        
        # Fallback to the first world if no specific world is provided
        world: Optional[WorldOverlay] = (
            target_world or (self.active_worlds[0] if self.active_worlds else None)
        )
        if world is None: return None
        
        # Determine instance name
        chosen_name: Optional[str] = instance_name
        if chosen_name is None:
            mod_display_name: str = mod_manager.current_mod_name or mod_folder
            if mod_manager.instance_names:
                all_active: list[BaseEntity] = (
                    cast(list[BaseEntity], self.active_entities) +
                    cast(list[BaseEntity], self.active_structures) +
                    cast(list[BaseEntity], self.active_items)
                )
                used_names: set[str] = {
                    e.instance_name for e in all_active
                    if e.instance_name is not None
                }
                avail: list[str] = [n for n in mod_manager.instance_names if n not in used_names]
                if avail:
                    chosen_name = random.choice(avail)
                else:
                    chosen_name = random.choice(mod_manager.instance_names)
            else:
                existing_count: int = sum(
                    1 for e in (
                        cast(list[BaseEntity], self.active_entities) +
                        cast(list[BaseEntity], self.active_structures) +
                        cast(list[BaseEntity], self.active_items)
                    )
                    if e.mod_manager and e.mod_manager.current_mod_folder == mod_folder
                )
                if existing_count > 0:
                    chosen_name = f"{mod_display_name} #{existing_count + 1}"
                else:
                    chosen_name = mod_display_name

        # Route instantiation based on the declared entity type
        entity: BaseStructure | BaseItem | Entity
        if mod_manager.entity_type == EntityType.STRUCTURE.value:
            entity = BaseStructure(x, y, mod_manager, world)
            if chosen_name:
                entity.set_instance_name(chosen_name)
            world.scene.addItem(entity)
            world.active_structures.append(entity)
            self.active_structures.append(entity)
        elif mod_manager.entity_type == EntityType.ITEM.value:
            entity = BaseItem(x, y, mod_manager, world)
            if chosen_name:
                entity.set_instance_name(chosen_name)
            world.scene.addItem(entity)
            world.active_items.append(entity)
            self.active_items.append(entity)
        else:
            entity = Entity(x, y, mod_manager, world, self)
            if chosen_name:
                entity.set_instance_name(chosen_name)
            world.scene.addItem(entity)
            world.active_entities.append(entity)
            self.active_entities.append(entity)
            
        self._on_spawn(entity)
        return entity

    def _on_spawn(self, entity: BaseEntity) -> None:
        behavior: Optional[BaseBehavior] = entity.get_behavior
        if behavior is None: return
        
        try:
            if isinstance(entity, Entity) and isinstance(behavior, BaseEntityBehavior):
                behavior.on_spawn(cast(IEntity, entity))
                
            elif isinstance(entity, BaseStructure) and isinstance(behavior, BaseStructureBehavior):
                behavior.on_spawn(cast(IStructure, entity))

            elif isinstance(entity, BaseItem) and isinstance(behavior, BaseItemBehavior):
                behavior.on_spawn(cast(IItem, entity))
        except Exception as e:
            mod_folder: str = "?" if self.mod_manager is None else self.mod_manager.current_mod_folder
            print(
                "Custom Behavior on_spawn Error "
                f"({mod_folder}): {e}"
            )
    
    def remove_entity(self, entity: BaseEntity) -> None:
        mod_folder: Optional[str] = (
            entity.mod_manager.current_mod_folder if entity.mod_manager else None
        )

        # Remove from global tracking safely
        if isinstance(entity, Entity) and entity in self.active_entities:
            self.active_entities.remove(entity)
        elif isinstance(entity, BaseStructure) and entity in self.active_structures:
            self.active_structures.remove(entity)
        elif isinstance(entity, BaseItem) and entity in self.active_items:
            self.active_items.remove(entity)
            
        # Remove from the specific world it inhabits
        for world in self.active_worlds:
            if entity in world.active_entities:
                world.active_entities.remove(cast(Entity, entity))
                if entity.scene():
                    world.scene.removeItem(entity)
                break
            elif entity in world.active_structures:
                world.active_structures.remove(cast(BaseStructure, entity))
                if entity.scene():
                    world.scene.removeItem(entity)
                break
            elif entity in world.active_items:
                world.active_items.remove(cast(BaseItem, entity))
                if entity.scene():
                    world.scene.removeItem(entity)
                break
        
        # If no other remaining active entity or structure uses this mod, prune its sprite sheets & frame cache
        if mod_folder is not None and mod_folder:
            all_remaining: list[BaseEntity] = (
                cast(list[BaseEntity], self.active_entities) +
                cast(list[BaseEntity], self.active_structures) +
                cast(list[BaseEntity], self.active_items)
            )
            has_other: bool = any(
                entity.mod_manager and
                entity.mod_manager.current_mod_folder == mod_folder
                for entity in all_remaining
            )
            if not has_other:
                ModManager.clear_mod_cache(mod_folder)

        # Full memory cleanup if NO entities exist at all
        if not self.active_entities and not self.active_structures and not self.active_items:
            AnimationSystem.clear_shared_cache()
            ModManager.clear_shared_cache()
            QPixmapCache.clear()
            gc.collect()

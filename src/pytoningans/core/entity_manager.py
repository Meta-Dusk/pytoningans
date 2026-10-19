import gc, random
from typing import cast, Optional

from PySide6.QtCore import QTimer, QElapsedTimer, QThreadPool, QRect
from PySide6.QtGui import QPixmapCache, QGuiApplication, QScreen

from pytoningans.core.vision_worker import VisionWorker
from pytoningans.core.window_tracker import WindowTracker
from pytoningans.core.settings import SettingsManager

from pytoningans.core.entity.base_structure import BaseStructure
from pytoningans.core.entity.base_item import BaseItem
from pytoningans.core.entity.living_entity import Entity
from pytoningans.core.entity.base_entity import BaseEntity
from pytoningans.core.entity.animation import AnimationSystem

from pytoningans.core.world import WorldOverlay
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.spawning import SpawningSystem
from pytoningans.core.api import (
    IEntity, IStructure, IItem, BaseStructureBehavior, BaseEntityBehavior,
    BaseItemBehavior, BaseBehavior
)
from pytoningans.core.constants import EntityType

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
        
        self.window_tracker: WindowTracker = WindowTracker()
        self.window_track_accumulator: int = 0
        
        self.spawning_system: SpawningSystem = SpawningSystem(self)
        
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

    def _has_window_triggers(self) -> bool:
        """Returns True if any active entity mod defines window triggers."""
        return any(
            bool(e.mod_manager.window_triggers)
            for e in self.active_entities if e.mod_manager is not None
        )

    def _on_vision_ready(self, titles: list[str]) -> None:
        self.active_window_titles = titles
        self._vision_in_progress = False
        self._vision_worker = None

    def _global_tick(self) -> None:
        """The heartbeat of the entire application across all worlds."""
        dt: int = self.clock.restart()
        
        self.vision_accumulator += dt
        if self.vision_accumulator >= 3000:
            self.vision_accumulator = 0
            if not self._vision_in_progress and self._has_window_triggers():
                self._vision_in_progress = True
                self._vision_worker = VisionWorker()
                self._vision_worker.signals.finished.connect(self._on_vision_ready)
                QThreadPool.globalInstance().start(self._vision_worker)

        # Track visible interactive desktop windows for physics collisions
        self.window_track_accumulator += dt
        if self.window_track_accumulator >= 150:
            self.window_track_accumulator = 0
            if SettingsManager.get().settings.enable_window_physics:
                self.window_tracker.update()
                for world in self.active_worlds:
                    screen_geom: QRect = world.geometry()
                    world.active_windows = self.window_tracker.get_local_windows_for_screen(screen_geom)
                    world.active_window_rects = [lr for _, lr in world.active_windows]
            else:
                for world in self.active_worlds:
                    if world.active_window_rects:
                        world.active_window_rects.clear()
                    if world.active_windows:
                        world.active_windows.clear()

        for world in self.active_worlds:
            world.update_systems(dt)

    def spawn_entity(
        self, x: float, y: float, mod_folder: str, 
        target_world: Optional[WorldOverlay] = None,
        instance_name: Optional[str] = None,
        fade_in: Optional[bool] = None,
    ) -> Optional[BaseEntity]:
        """Dynamically spawns a living Entity or a static Structure based on mod config."""
        mod_manager = ModManager(self.mod_manager.mods_dir)
        mod_manager.load_mod(mod_folder)
        if fade_in is not None:
            mod_manager.fade_in_on_spawn = fade_in
        
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
        if mod_manager.entity_type == EntityType.STRUCTURE:
            entity = BaseStructure(x, y, mod_manager, world)
            if chosen_name:
                entity.set_instance_name(chosen_name)
            world.scene.addItem(entity)
            world.active_structures.append(entity)
            self.active_structures.append(entity)
        elif mod_manager.entity_type == EntityType.ITEM:
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
        if entity.mod_manager is not None and entity.mod_manager.pack is not None:
            entity.mod_manager.pack.on_entity_spawned(entity)

        behavior: Optional[BaseBehavior] = entity.behavior
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
        
        # If no other remaining active entity or structure uses this mod,
        # prune its sprite sheets and frame cache
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

from __future__ import annotations

import json, sys
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPixmap

from pytoningans.core.api import BaseBehavior
from pytoningans.core.config_schema import (
    CURRENT_CONFIG_VERSION,
    BehaviorConfig,
    DialogueConfig,
    ModConfig,
)
from pytoningans.core.constants import (
    AnimationMeta,
    AttackType,
    BehaviorType,
    DeathAnimation,
    EntityType,
)
from .behavior_loader import compile_behavior_mod
from .cache import (
    CacheKey,
    clear_mod_cache,
    clear_shared_cache,
    shared_frame_cache,
    shared_sheets,
)
from .config_io import (
    ensure_config_file,
    ensure_fallback_animations,
    parse_animations,
    save_config_file,
    sync_static_physics,
)
from .discovery import IGNORED_MOD_FOLDERS, get_available_mods_with_type
from .physics import get_frame_physics
from .sprites import bake_sprite_sheet, get_frame, resolve_dimensions


class ModManager:
    """Core mod management system responsible for mod configuration, behaviors, and sprites."""

    _shared_frame_cache: dict[CacheKey, QPixmap] = shared_frame_cache
    """Class-level cache: (mod_name, x, y, width, height) -> sliced QPixmap."""

    _shared_sheets: dict[str, QPixmap] = shared_sheets
    """Class-level cache for full sprite sheets."""

    IGNORED_MOD_FOLDERS: set[str] = IGNORED_MOD_FOLDERS

    @classmethod
    def clear_shared_cache(cls) -> None:
        """Flushes the extracted master frames from memory."""
        clear_shared_cache()

    @classmethod
    def clear_mod_cache(cls, mod_folder: str) -> None:
        """Flushes cached sprite sheets and sliced frames for a specific mod folder."""
        clear_mod_cache(mod_folder)

    def __init__(self, mods_dir: str | Path = "assets/mods") -> None:
        self.mods_dir: Path = Path(mods_dir)
        self.current_mod_name: str = ""
        self.current_mod_folder: str = ""
        self.global_columns: int = 1
        self.global_rows: int = 1
        self.is_static: bool = False
        self._static_physics_cache: Optional[tuple[QPoint, QRect]] = None

        self.config_version: int = CURRENT_CONFIG_VERSION
        self.can_fly: bool = False
        self.can_climb_walls: bool = False
        self.can_move_windows: bool = False
        self.window_move_mode: str = "attack"
        self.max_health: int = 100
        self.attack_damage: int = 10
        self.attack_range: int = 50
        self.jump_height: int = 150
        self.behavior_type: BehaviorType = BehaviorType.NEUTRAL
        self.attack_type: AttackType = AttackType.SINGLE
        self.max_targets: int = 1

        self.animations: dict[str, AnimationMeta] = {}
        self._global_sheet: Optional[QPixmap] = None
        self.config: Optional[ModConfig] = None
        self.custom_behavior: Optional[BaseBehavior] = None

        self.plain_dialogue: list[str] = []
        self.death_dialogue: list[str] = []
        self.window_triggers: list[dict[str, Any]] = []

        self.death_animation: DeathAnimation = DeathAnimation.SPRITE
        self.auto_close_on_death: bool = False
        self.instance_names: list[str] = []
        self.tags: list[str] = []

        # Inject the mods folder into Python's runtime path
        abs_mods_dir: str = str(self.mods_dir.resolve())
        if abs_mods_dir not in sys.path:
            sys.path.insert(0, abs_mods_dir)

    @property
    def current_mod_path(self) -> Path:
        """Returns the full Path to the currently loaded mod's directory."""
        return self.mods_dir / self.current_mod_folder

    @property
    def entity_type(self) -> str:
        """Returns the entity type, defaulting to 'entity' for backward compatibility."""
        return self.config.entity_type if self.config else EntityType.ENTITY.value

    def get_available_mods_with_type(self) -> dict[str, tuple[str, str]]:
        """Returns a dict mapping folder_name -> (display_name, entity_type)."""
        return get_available_mods_with_type(self.mods_dir, self.IGNORED_MOD_FOLDERS)

    def load_mod(self, mod_folder_name: str) -> bool:
        """Loads a mod folder by name, parsing configuration and loading sprite sheet."""
        if mod_folder_name.lower() in self.IGNORED_MOD_FOLDERS:
            return False

        self.current_mod_folder = mod_folder_name
        mod_path: Path = self.mods_dir / mod_folder_name
        config_path: Path = mod_path / "config.json"
        sprite_path: Path = mod_path / "sprite_sheet.png"

        if not sprite_path.exists():
            return False

        # AUTO-SCAFFOLD USING SCHEMA
        ensure_config_file(config_path, mod_folder_name)

        # Unconditionally load into memory
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        raw_entity_type = data.get("entity_type", EntityType.ENTITY.value)
        entity_type_str: str = (
            raw_entity_type.value
            if hasattr(raw_entity_type, "value")
            else str(raw_entity_type)
        )

        behavior_data: dict[str, Any] = data.get("behavior", {})
        raw_tags: list[Any] = data.get("tags", behavior_data.get("tags", []))
        self.tags = [str(t).lower().strip() for t in raw_tags if str(t).strip()]

        self._static_physics_cache = None
        self.is_static = data.get("is_static", False)
        if not self.is_static and entity_type_str in (EntityType.ITEM.value, EntityType.STRUCTURE.value):
            if data.get("columns", 1) == 1 and data.get("rows", 1) == 1:
                self.is_static = True

        # Instantiate the config to store the entity type
        self.config = ModConfig(
            name=data.get("name", mod_folder_name),
            entity_type=entity_type_str,
            is_static=self.is_static,
            tags=self.tags,
            version=data.get("version", CURRENT_CONFIG_VERSION),
            columns=data.get("columns", 1),
            rows=data.get("rows", 1),
        )

        # Extract into flat variables
        self.current_mod_name = data.get("name", mod_folder_name)
        self.global_columns = data.get("columns", 1)
        self.global_rows = data.get("rows", 1)
        self.config_version = data.get("version", 1)

        self.can_fly = behavior_data.get("can_fly", False)
        self.can_climb_walls = behavior_data.get("can_climb_walls", False)
        self.can_move_windows = behavior_data.get("can_move_windows", False)
        self.window_move_mode = behavior_data.get("window_move_mode", "attack")

        self.max_health = behavior_data.get("max_health", 100)
        self.attack_damage = behavior_data.get("attack_damage", 10)
        self.attack_range = behavior_data.get("attack_range", 50)
        self.jump_height = behavior_data.get("jump_height", 15)

        raw_behavior_type = behavior_data.get("type", "neutral")
        try:
            self.behavior_type = BehaviorType(raw_behavior_type)
        except ValueError:
            self.behavior_type = BehaviorType.NEUTRAL

        raw_attack_type = behavior_data.get("attack_type", "single")
        try:
            self.attack_type = AttackType(raw_attack_type)
        except ValueError:
            self.attack_type = AttackType.SINGLE

        self.max_targets = behavior_data.get("max_targets", 1)

        raw_death_anim = behavior_data.get("death_animation", "sprite")
        try:
            self.death_animation = DeathAnimation(raw_death_anim)
        except ValueError:
            self.death_animation = DeathAnimation.SPRITE

        self.auto_close_on_death = behavior_data.get("auto_close_on_death", False)
        self.instance_names = list(behavior_data.get("instance_names", []))

        anim_data: dict[str, Any] = data.get("animations", {})
        self.animations = parse_animations(anim_data, self.entity_type)
        ensure_fallback_animations(self.animations, self.entity_type, self.global_columns)

        # For static entities, ensure baseline physics and overrides match idle across all states
        if self.is_static:
            sync_static_physics(self.animations)

        dialogue_data = data.get("dialogue", {})
        self.plain_dialogue = dialogue_data.get("plain_dialogue", ["..."])
        self.death_dialogue = dialogue_data.get(
            "death_dialogue", ["Ugh...", "I'll be back...", "Farewell..."]
        )
        self.window_triggers = dialogue_data.get("window_triggers", [])

        self.custom_behavior = None
        self._compile_behavior_mod(mod_folder_name, mod_path)

        if mod_folder_name not in shared_sheets:
            with open(sprite_path, "rb") as f:
                sheet = QPixmap()
                sheet.loadFromData(f.read())

            if not sheet.isNull():
                shared_sheets[mod_folder_name] = sheet

        self._global_sheet = shared_sheets.get(mod_folder_name)
        if self._global_sheet is None:
            return False

        self._resolve_dimensions()
        return True

    def _compile_behavior_mod(self, mod_folder_name: str, mod_path: Path) -> None:
        self.custom_behavior = compile_behavior_mod(
            mod_folder_name, mod_path, self.entity_type
        )

    def save_mod_config(self, mod_folder_name: str, name: str) -> None:
        """Saves current settings into config.json in the mod's directory."""
        mod_path: Path = self.mods_dir / mod_folder_name
        config_path: Path = mod_path / "config.json"

        if self.is_static:
            sync_static_physics(self.animations)
        self._static_physics_cache = None

        config = ModConfig(
            name=name,
            entity_type=self.entity_type,
            is_static=self.is_static,
            tags=self.tags,
            version=CURRENT_CONFIG_VERSION,
            columns=self.global_columns,
            rows=self.global_rows,
            behavior=BehaviorConfig(
                type=BehaviorType(self.behavior_type).value,
                can_fly=self.can_fly,
                can_climb_walls=self.can_climb_walls,
                can_move_windows=self.can_move_windows,
                window_move_mode=self.window_move_mode,
                max_health=self.max_health,
                attack_damage=self.attack_damage,
                attack_range=self.attack_range,
                jump_height=self.jump_height,
                attack_type=self.attack_type,
                max_targets=self.max_targets,
                death_animation=self.death_animation,
                auto_close_on_death=self.auto_close_on_death,
                instance_names=self.instance_names,
            ),
            animations={str(state): meta for state, meta in self.animations.items()},
            dialogue=DialogueConfig(
                plain_dialogue=self.plain_dialogue,
                death_dialogue=self.death_dialogue,
                window_triggers=self.window_triggers,
            ),
        )

        self.config = config
        save_config_file(config_path, config)

    def get_frame(self, state: str, tick_index: int) -> Optional[QPixmap]:
        """Crops and returns the specific animation frame from the sprite sheet with caching."""
        return get_frame(
            self._global_sheet,
            self.current_mod_name,
            self.animations,
            state,
            tick_index,
        )

    def bake_sprite_sheet(self) -> bool:
        """Permanently bakes all crop settings into a new optimized sprite sheet file."""
        success, new_sheet = bake_sprite_sheet(
            self.mods_dir,
            self.current_mod_folder,
            self._global_sheet,
            self.global_columns,
            self.global_rows,
            self.animations,
            lambda: self.save_mod_config(self.current_mod_folder, self.current_mod_name),
        )
        if success and new_sheet:
            self._global_sheet = new_sheet
            return True
        return False

    def _resolve_dimensions(self) -> None:
        """Pre-computes tile and frame extraction dimensions."""
        resolve_dimensions(
            self._global_sheet,
            self.global_columns,
            self.global_rows,
            self.animations,
        )

    def get_frame_physics(self, state: str, tick_index: int) -> tuple[QPoint, QRect]:
        """Returns the (Anchor Point, Hitbox Rect) for the current frame."""
        if self.is_static:
            if self._static_physics_cache is not None:
                return self._static_physics_cache
            result = get_frame_physics(
                self.animations,
                state,
                tick_index,
                self.is_static,
                self.entity_type,
            )
            self._static_physics_cache = result
            return result

        return get_frame_physics(
            self.animations,
            state,
            tick_index,
            self.is_static,
            self.entity_type,
        )


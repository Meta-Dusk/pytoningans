import json, sys, inspect
import importlib.util
from pathlib import Path

from typing import Optional, Any

from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import QRect, Qt, QPoint

from pytoningans.core.constants import (
    EntityState, AnimationMeta, BehaviorType, AttackType, DeathAnimation,
    EntityType, StructureState
)
from pytoningans.core.api import BaseEntityBehavior, BaseStructureBehavior, BaseBehavior
from pytoningans.core.config_schema import (
    ModConfig, BehaviorConfig, DialogueConfig, CURRENT_CONFIG_VERSION
)

type CacheKey = tuple[str, int, int, int, int]

class ModManager:
    _shared_frame_cache: dict[CacheKey, QPixmap] = {}
    """Class-level cache: (mod_folder_name, state, frame_index) -> QPixmap"""
    
    _shared_sheets: dict[str, QPixmap] = {}
    """Class-level cache for full sprite sheets."""

    @classmethod
    def clear_shared_cache(cls) -> None:
        """Flushes the extracted master frames from memory."""
        cls._shared_frame_cache.clear()
        cls._shared_sheets.clear()
        
    def __init__(self, mods_dir: str | Path = "assets/mods") -> None:
        self.mods_dir: Path = Path(mods_dir)
        self.current_mod_name: str = ""
        self.current_mod_folder: str = ""
        self.global_columns: int = 1
        self.global_rows: int = 1
        
        self.config_version: int = CURRENT_CONFIG_VERSION
        self.can_fly: bool = False
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
        self.window_triggers: list[dict[str, Any]] = []
        
        self.death_animation: DeathAnimation = DeathAnimation.SPRITE
        self.auto_close_on_death: bool = False
        
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
        """Returns the entity type, defaulting to 'pet' for backward compatibility."""
        return self.config.entity_type if self.config else EntityType.PET.value
    
    def get_available_mods_with_type(self) -> dict[str, tuple[str, str]]:
        """Returns a dict mapping folder_name -> (display_name, entity_type)."""
        valid_mods: dict[str, tuple[str, str]] = {}
        if not self.mods_dir.exists():
            return valid_mods
            
        for item in self.mods_dir.iterdir():
            if not item.is_dir() or item.name.startswith(('_', '.')): 
                continue
            folder_name: str = item.name
            display_name: str = folder_name
            entity_type: str = EntityType.PET.value
            
            config_path: Path = item / "config.json"
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        display_name = data.get("name", folder_name)
                        entity_type = data.get("entity_type", EntityType.PET.value)
                except Exception:
                    pass
                    
            valid_mods[folder_name] = (display_name, entity_type)
                
        return valid_mods

    def load_mod(self, mod_folder_name: str) -> bool:
        self.current_mod_folder = mod_folder_name
        mod_path: Path = self.mods_dir / mod_folder_name
        config_path: Path = mod_path / "config.json"
        sprite_path: Path = mod_path / "sprite_sheet.png"

        if not sprite_path.exists():
            return False

        # AUTO-SCAFFOLD USING SCHEMA
        if not config_path.exists():
            new_config = ModConfig(name=mod_folder_name)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(new_config.to_dict(), f, indent=4)

        # Unconditionally load into memory
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        
        raw_entity_type = data.get("entity_type", EntityType.PET.value)
        entity_type_str: str = (
            raw_entity_type.value if hasattr(raw_entity_type, "value") else str(raw_entity_type)
        )
        
        # Instantiate the config to store the entity type
        self.config = ModConfig(
            name=data.get("name", mod_folder_name),
            entity_type=entity_type_str,
            version=data.get("version", CURRENT_CONFIG_VERSION),
            columns=data.get("columns", 1),
            rows=data.get("rows", 1)
        )
        
        # Extract into flat variables    
        self.current_mod_name = data.get("name", mod_folder_name)
        self.global_columns = data.get("columns", 1)
        self.global_rows = data.get("rows", 1)
        self.config_version = data.get("version", 1)
        
        behavior_data: dict[str, Any] = data.get("behavior", {})
        self.can_fly = behavior_data.get("can_fly", False)
        
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
        
        self.animations.clear()
        anim_data: dict[str, Any] = data.get("animations", {})
        
        # Load all existing animations from config.json first
        for state_key, raw_meta in anim_data.items():
            meta_dict: dict[str, Any] = dict(raw_meta)
            if "frames" in meta_dict:
                meta_dict["start_frame"] = 0
                meta_dict["end_frame"] = max(0, meta_dict.pop("frames") - 1)
            # Remove any unwanted legacy fields before initializing AnimationMeta
            clean_keys: set[str] = {f.name for f in AnimationMeta.__dataclass_fields__.values()}
            filtered: dict[str, Any] = {k: v for k, v in meta_dict.items() if k in clean_keys}
            self.animations[str(state_key)] = AnimationMeta(**filtered)
            
        # Ensure standard enum states exist as fallbacks
        state_enum = StructureState if self.entity_type == EntityType.STRUCTURE.value else EntityState
        cols: int = max(1, self.global_columns)
        for state in state_enum:
            key_str: str = str(state.value)
            if key_str not in self.animations:
                self.animations[key_str] = AnimationMeta(
                    row=0,
                    start_frame=0,
                    end_frame=max(0, cols - 1),
                    loop=True
                )
        
        dialogue_data = data.get("dialogue", {})
        self.plain_dialogue = dialogue_data.get("plain_dialogue", ["..."])
        self.window_triggers = dialogue_data.get("window_triggers", [])
        
        self.custom_behavior = None
        self._compile_behavior_mod(mod_folder_name, mod_path)

        if mod_folder_name not in ModManager._shared_sheets:
            with open(sprite_path, "rb") as f:
                sheet = QPixmap()
                sheet.loadFromData(f.read())
            
            if not sheet.isNull():
                ModManager._shared_sheets[mod_folder_name] = sheet
            
        self._global_sheet = ModManager._shared_sheets.get(mod_folder_name)
        if self._global_sheet is None:
            return False
            
        self._resolve_dimensions()
        return True

    def _compile_behavior_mod(self, mod_folder_name: str, mod_path: Path) -> None:
        behavior_path: Path = mod_path / "behavior.py"
        if not behavior_path.exists(): return
        try:
            spec = importlib.util.spec_from_file_location("mod_behavior", str(behavior_path))
            if spec is None or spec.loader is None: return
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Dynamically determine the expected parent class
            expected_base = (
                BaseStructureBehavior 
                if self.entity_type == EntityType.STRUCTURE.value 
                else BaseEntityBehavior
            )
            
            # Search the module for any class inheriting the expected base
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, expected_base) and obj is not expected_base:
                    self.custom_behavior = obj()
                    break
        except Exception as e:
            print(f"Failed to load behavior.py for {mod_folder_name}: {e}")

    def save_mod_config(self, mod_folder_name: str, name: str) -> None:
        mod_path: Path = self.mods_dir / mod_folder_name
        config_path: Path = mod_path / "config.json"
        
        config = ModConfig(
            name=name,
            entity_type=self.entity_type,
            version=CURRENT_CONFIG_VERSION,
            columns=self.global_columns,
            rows=self.global_rows,
            behavior=BehaviorConfig(
                type=BehaviorType(self.behavior_type).value,
                can_fly=self.can_fly,
                max_health=self.max_health,
                attack_damage=self.attack_damage,
                attack_range=self.attack_range,
                jump_height=self.jump_height,
                attack_type=self.attack_type,
                max_targets=self.max_targets,
                death_animation=self.death_animation,
                auto_close_on_death=self.auto_close_on_death,
            ),
            animations={str(state): meta for state, meta in self.animations.items()},
            dialogue=DialogueConfig(
                plain_dialogue=self.plain_dialogue,
                window_triggers=self.window_triggers
            )
        )
        
        self.config = config
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=4)

    def get_frame(self, state: str, tick_index: int) -> Optional[QPixmap]:
        if not self._global_sheet: return None
        anim_meta: Optional[AnimationMeta] = self.animations.get(state)
        if not anim_meta: return None

        total_play_frames: int = max(1, (anim_meta.end_frame - anim_meta.start_frame) + 1)
        
        mapped_index: int = 0
        if anim_meta.loop:
            mapped_index = tick_index % total_play_frames
        else:
            mapped_index = min(tick_index, total_play_frames - 1)
            
        if anim_meta.reverse:
            mapped_index = (total_play_frames - 1) - mapped_index
            
        actual_sheet_index: int = anim_meta.start_frame + mapped_index

        final_w: int = anim_meta.computed_w
        final_h: int = anim_meta.computed_h

        x_pos: int = (actual_sheet_index * final_w) + anim_meta.offset_x
        y_pos: int = (anim_meta.row * anim_meta.base_h) + anim_meta.offset_y 
        
        crop_rect = QRect(x_pos, y_pos, final_w, final_h)
        safe_rect = crop_rect.intersected(self._global_sheet.rect())
        
        if safe_rect.isEmpty(): return None

        # Cache using the Mod Name + X, Y, Width, Height + State + Frame
        cache_key: CacheKey = (
            self.current_mod_name, 
            safe_rect.x(), safe_rect.y(), safe_rect.width(), safe_rect.height()
        )
        
        if cache_key in ModManager._shared_frame_cache:
            return ModManager._shared_frame_cache[cache_key]
        
        frame: QPixmap = self._global_sheet.copy(safe_rect)
        ModManager._shared_frame_cache[cache_key] = frame
        
        return frame
    
    def bake_sprite_sheet(self) -> bool:
        """Permanently bakes all crop settings into a new optimized sprite sheet file."""
        if not self._global_sheet: return False

        cols: int = max(1, self.global_columns)
        rows: int = max(1, self.global_rows)
        base_w: int = self._global_sheet.width() // cols
        base_h: int = self._global_sheet.height() // rows

        new_cell_w, new_cell_h = 1, 1
        for meta in self.animations.values():
            w = meta.override_width if meta.override_width > 0 else base_w
            h = meta.override_height if meta.override_height > 0 else base_h
            new_cell_w = max(new_cell_w, w)
            new_cell_h = max(new_cell_h, h)

        new_sheet = QPixmap(new_cell_w * cols, new_cell_h * rows)
        new_sheet.fill(Qt.GlobalColor.transparent)
        painter = QPainter(new_sheet)

        painted_cells: set[tuple[int, int]] = set()

        for _, meta in self.animations.items():
            w: int = meta.override_width if meta.override_width > 0 else base_w
            h: int = meta.override_height if meta.override_height > 0 else base_h

            for sheet_idx in range(meta.start_frame, meta.end_frame + 1):
                cell_key: tuple[int, int] = (meta.row, sheet_idx)
                if cell_key in painted_cells: 
                    continue

                x_pos: int = (sheet_idx * w) + meta.offset_x
                y_pos: int = (meta.row * base_h) + meta.offset_y
                crop_rect: QRect = QRect(x_pos, y_pos, w, h).intersected(self._global_sheet.rect())

                if not crop_rect.isEmpty():
                    frame: QPixmap = self._global_sheet.copy(crop_rect)
                    dest_x: int = (sheet_idx * new_cell_w) + ((new_cell_w - frame.width()) // 2)
                    dest_y: int = (meta.row * new_cell_h) + ((new_cell_h - frame.height()) // 2)
                    painter.drawPixmap(dest_x, dest_y, frame)

                painted_cells.add(cell_key)

        painter.end()

        mod_path: Path = self.mods_dir / self.current_mod_folder
        sprite_path: Path = mod_path / "sprite_sheet.png"
        success: bool = new_sheet.save(str(sprite_path), "PNG")
        if not success: return False

        self._global_sheet = new_sheet
        self.clear_shared_cache()

        for meta in self.animations.values():
            meta.offset_x = 0
            meta.offset_y = 0
            meta.override_width = 0
            meta.override_height = 0

        self.save_mod_config(self.current_mod_folder, self.current_mod_name)
        return True
    
    def _resolve_dimensions(self) -> None:
        """Pre-computes tile and frame extraction dimensions."""
        if not self._global_sheet: return
        base_w: int = self._global_sheet.width() // max(1, self.global_columns)
        base_h: int = self._global_sheet.height() // max(1, self.global_rows)
        
        for meta in self.animations.values():
            meta.base_h = base_h
            meta.computed_w = meta.override_width if meta.override_width > 0 else base_w
            meta.computed_h = meta.override_height if meta.override_height > 0 else base_h
    
    def get_frame_physics(self, state: str, tick_index: int) -> tuple[QPoint, QRect]:
        """Returns the (Anchor Point, Hitbox Rect) for the current frame."""
        anim_meta: Optional[AnimationMeta] = self.animations.get(state)
        
        # Fallback defaults if state doesn't exist
        if anim_meta is None:
            return QPoint(0, 0), QRect(0, 0, 50, 50)
            
        total_play_frames: int = max(1, (anim_meta.end_frame - anim_meta.start_frame) + 1)
        
        # Calculate exactly which relative frame index we are playing
        mapped_index: int = tick_index % total_play_frames if anim_meta.loop else min(tick_index, total_play_frames - 1)
        if anim_meta.reverse:
            mapped_index = (total_play_frames - 1) - mapped_index
            
        # Start with the state's baseline physics
        ax, ay = anim_meta.anchor_x, anim_meta.anchor_y
        hx, hy = anim_meta.hitbox_x, anim_meta.hitbox_y
        hw, hh = anim_meta.hitbox_w, anim_meta.hitbox_h
        
        # Apply per-frame overrides if the user edited this specific frame
        frame_key: str = str(mapped_index)
        if frame_key in anim_meta.frame_overrides:
            override = anim_meta.frame_overrides[frame_key]
            ax = override.get("anchor_x", ax)
            ay = override.get("anchor_y", ay)
            hx = override.get("hitbox_x", hx)
            hy = override.get("hitbox_y", hy)
            hw = override.get("hitbox_w", hw)
            hh = override.get("hitbox_h", hh)
            
        # If hitbox width/height are 0 (unconfigured), default to the full image cell
        if hw == 0 or hh == 0:
            hw = anim_meta.computed_w
            hh = anim_meta.computed_h
            
        return QPoint(ax, ay), QRect(hx, hy, hw, hh)
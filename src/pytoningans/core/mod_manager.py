import json, sys, shutil
import importlib.util
from pathlib import Path

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import asdict

from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import QRect, Qt

from pytoningans.core.constants import PetState, AnimationMeta, BehaviorType
from pytoningans.core.api import BasePetBehavior
from pytoningans.utils.paths import get_asset_path

CURRENT_CONFIG_VERSION = 6

type CacheKey = Tuple[str, PetState, int]

class ModManager:
    _shared_frame_cache: Dict[CacheKey, QPixmap] = {}
    """Class-level cache: (mod_folder_name, state, frame_index) -> QPixmap"""

    @classmethod
    def clear_shared_cache(cls) -> None:
        """Flushes the extracted master frames from memory."""
        cls._shared_frame_cache.clear()
        
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
        
        self.animations: Dict[PetState, AnimationMeta] = {}
        self._global_sheet: Optional[QPixmap] = None
        self.custom_behavior: Optional[BasePetBehavior] = None
        
        self.plain_dialogue: List[str] = []
        self.window_triggers: List[Dict[str, Any]] = []
        
        self._scaffold_modding_api()
        
        # Inject the mods folder into Python's runtime path
        abs_mods_dir: str = str(self.mods_dir.resolve())
        if abs_mods_dir not in sys.path:
            sys.path.insert(0, abs_mods_dir)
    
    @property
    def current_mod_path(self) -> Path:
        """Returns the full Path to the currently loaded mod's directory."""
        return self.mods_dir / self.current_mod_folder
    
    def _scaffold_modding_api(self) -> None:
        """Copies the api_template.py file directly to the external mods directory."""
        self.mods_dir.mkdir(parents=True, exist_ok=True)
        
        source_api_path: Path = get_asset_path("assets/mods/api_template.py")
        target_api_path: Path = self.mods_dir / "api.py"
        
        if source_api_path.exists():
            shutil.copyfile(source_api_path, target_api_path)
        else:
            print(f"Warning: Could not find source API template at {source_api_path}")
    
    def get_available_mods(self) -> List[str]:
        """Returns a list of valid folder names in the mods directory."""
        valid_mods: List[str] = []
        if not self.mods_dir.exists():
            return valid_mods
            
        for item in self.mods_dir.iterdir():
            if item.is_dir() and not item.name.startswith(('_', '.')):
                valid_mods.append(item.name)
                
        return valid_mods

    def load_mod(self, mod_folder_name: str) -> bool:
        self.current_mod_folder = mod_folder_name
        mod_path: Path = self.mods_dir / mod_folder_name
        config_path: Path = mod_path / "config.json"
        sprite_path: Path = mod_path / "sprite_sheet.png"

        if not sprite_path.exists():
            return False

        # AUTO-SCAFFOLD
        if not config_path.exists():
            self.current_mod_name = mod_folder_name
            self.global_columns = 4
            self.global_rows = len(PetState)
            self.can_fly = False
            self.config_version = CURRENT_CONFIG_VERSION
            
            self.can_fly = False
            self.max_health = 100
            self.attack_damage = 10
            self.attack_range = 50
            self.jump_height = 15
            
            self.animations = {
                state: AnimationMeta(row=i, start_frame=0, end_frame=3)
                for i, state in enumerate(PetState)
            }
            
            self.plain_dialogue = ["Just hanging out.", "Lovely weather.", "Need a break?"]
            self.window_triggers = [
                {
                    "title_matches": ["secret_diary.txt", "diary - notepad"], 
                    "text": "Are you writing about me?", 
                    "duration": 4000, 
                    "chance": 1.0
                },
                {
                    "title_matches": ["visual studio code", "vscode", "code.exe"], 
                    "text": "Writing bugs or features today?", 
                    "duration": 4000, 
                    "chance": 0.1
                }
            ]
            self.save_mod_config(mod_folder_name, self.current_mod_name)
        else:
            with open(config_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
                
            self.current_mod_name = data.get("name", mod_folder_name)
            self.global_columns = data.get("columns", 1)
            self.global_rows = data.get("rows", 1)
            self.config_version = data.get("version", 1)
            
            behavior_data: Dict[str, Any] = data.get("behavior", {})
            self.can_fly = behavior_data.get("can_fly", False)
            
            self.max_health = behavior_data.get("max_health", 100)
            self.attack_damage = behavior_data.get("attack_damage", 10)
            self.attack_range = behavior_data.get("attack_range", 50)
            self.jump_height = behavior_data.get("jump_height", 15)
            
            raw_type = behavior_data.get("type", "neutral")
            try:
                self.behavior_type = BehaviorType(raw_type)
            except ValueError:
                self.behavior_type = BehaviorType.NEUTRAL
            
            self.animations.clear()
            anim_data = data.get("animations", {})
            
            for state in PetState:
                if state.value in anim_data:
                    raw_meta = anim_data[state.value]
                    
                    if "frames" in raw_meta:
                        raw_meta["start_frame"] = 0
                        raw_meta["end_frame"] = max(0, raw_meta.pop("frames") - 1)
                        
                    self.animations[state] = AnimationMeta(**raw_meta)
                else:
                    self.animations[state] = AnimationMeta(row=0, start_frame=0, end_frame=0)
            
            dialogue_data = data.get("dialogue", {})
            self.plain_dialogue = dialogue_data.get("plain_dialogue", ["..."])
            self.window_triggers = dialogue_data.get("window_triggers", [])
        
        self.custom_behavior = None
        self._compile_behavior_mod(mod_folder_name, mod_path)

        with open(sprite_path, "rb") as f:
            sheet = QPixmap()
            sheet.loadFromData(f.read())
            
        if sheet.isNull(): return False
            
        self._global_sheet = sheet
        return True

    def _compile_behavior_mod(self, mod_folder_name: str, mod_path: Path) -> None:
        behavior_path: Path = mod_path / "behavior.py"
        if not behavior_path.exists(): return
        try:
            spec = importlib.util.spec_from_file_location("mod_behavior", str(behavior_path))
            if spec is None or spec.loader is None: return
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "Behavior"):
                self.custom_behavior = module.Behavior()
        except Exception as e:
            print(f"Failed to load behavior.py for {mod_folder_name}: {e}")

    def save_mod_config(self, mod_folder_name: str, name: str) -> None:
        mod_path: Path = self.mods_dir / mod_folder_name
        config_path: Path = mod_path / "config.json"
        
        data: Dict[str, Any] = {
            "version": CURRENT_CONFIG_VERSION,
            "name": name,
            "columns": self.global_columns,
            "rows": self.global_rows,
            "behavior": {
                "type": BehaviorType(self.behavior_type).value,
                "can_fly": self.can_fly,
                "max_health": self.max_health,
                "attack_damage": self.attack_damage,
                "attack_range": self.attack_range,
                "jump_height": self.jump_height
            },
            "animations": {
                state.value: asdict(meta) for state, meta in self.animations.items()
            },
            "dialogue": {
                "plain_dialogue": self.plain_dialogue,
                "window_triggers": self.window_triggers
            }
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_frame(self, state: PetState, tick_index: int) -> Optional[QPixmap]:
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
        
        cache_key: CacheKey = (self.current_mod_name, state, actual_sheet_index)
        if cache_key in ModManager._shared_frame_cache:
            return ModManager._shared_frame_cache[cache_key]

        base_w: int = self._global_sheet.width() // max(1, self.global_columns)
        base_h: int = self._global_sheet.height() // max(1, self.global_rows)
        
        final_w: int = anim_meta.override_width if anim_meta.override_width > 0 else base_w
        final_h: int = anim_meta.override_height if anim_meta.override_height > 0 else base_h

        x_pos: int = (actual_sheet_index * final_w) + anim_meta.offset_x
        y_pos: int = (anim_meta.row * base_h) + anim_meta.offset_y 
        
        crop_rect = QRect(x_pos, y_pos, final_w, final_h)
        safe_rect = crop_rect.intersected(self._global_sheet.rect())
        
        if safe_rect.isEmpty(): return None
        
        frame = self._global_sheet.copy(safe_rect)
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

        painted_cells = set()

        for _, meta in self.animations.items():
            w: int = meta.override_width if meta.override_width > 0 else base_w
            h: int = meta.override_height if meta.override_height > 0 else base_h

            for sheet_idx in range(meta.start_frame, meta.end_frame + 1):
                cell_key: Tuple[int, int] = (meta.row, sheet_idx)
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
import json, os, shutil, sys
import importlib.util

from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

from PySide6.QtGui import QPixmap
from PySide6.QtCore import QRect

from pytoningans.core.constants import PetState, AnimationMeta
from pytoningans.core.api import BasePetBehavior

CURRENT_CONFIG_VERSION = 5

class ModManager:
    _shared_frame_cache: Dict[Tuple[str, PetState, int], QPixmap] = {}
    """Class-level cache: (mod_folder_name, state, frame_index) -> QPixmap"""

    @classmethod
    def clear_shared_cache(cls) -> None:
        """Flushes the extracted master frames from memory."""
        cls._shared_frame_cache.clear()
        
    def __init__(self, mods_dir: str = "assets/mods") -> None:
        self.mods_dir: str = mods_dir
        self.current_mod_name: str = ""
        self.global_columns: int = 1
        self.global_rows: int = 1
        self.can_fly: bool = False
        self.config_version: int = CURRENT_CONFIG_VERSION
        
        self.max_health: int = 100
        self.attack_damage: int = 10
        self.attack_range: int = 50
        self.jump_height: int = 150
        
        self.animations: Dict[PetState, AnimationMeta] = {}
        self._global_sheet: Optional[QPixmap] = None
        self.custom_behavior: Optional[BasePetBehavior] = None
        
        self._scaffold_modding_api()
        
        # Inject the mods folder into Python's runtime path
        abs_mods_dir = os.path.abspath(self.mods_dir)
        if abs_mods_dir not in sys.path:
            sys.path.insert(0, abs_mods_dir)
    
    def _scaffold_modding_api(self) -> None:
        """Copies the internal api.py file directly to the external mods directory."""
        os.makedirs(self.mods_dir, exist_ok=True)
        
        core_dir = os.path.dirname(os.path.abspath(__file__))
        source_api_path = os.path.abspath(os.path.join(core_dir, "..", "core", "api.py"))
        
        target_api_path = os.path.join(self.mods_dir, "api.py")
        
        # Copy the file, overwriting any existing one to ensure modders have the latest API
        if os.path.exists(source_api_path):
            shutil.copyfile(source_api_path, target_api_path)
        else:
            print(f"Warning: Could not find source API file at {source_api_path}")
    
    def get_available_mods(self) -> List[str]:
        """Returns a list of valid folder names in the mods directory."""
        valid_mods = []
        if not os.path.exists(self.mods_dir):
            return valid_mods
            
        for item in os.listdir(self.mods_dir):
            item_path = os.path.join(self.mods_dir, item)
            
            # Ignore files, and ignore folders starting with '_' or '.'
            if os.path.isdir(item_path) and not item.startswith(('_', '.')):
                valid_mods.append(item)
                
        return valid_mods

    def load_mod(self, mod_folder_name: str) -> bool:
        mod_path = os.path.join(self.mods_dir, mod_folder_name)
        config_path = os.path.join(mod_path, "config.json")
        sprite_path = os.path.join(mod_path, "sprite_sheet.png")

        if not os.path.exists(sprite_path):
            return False

        # AUTO-SCAFFOLD
        if not os.path.exists(config_path):
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
            self.save_mod_config(mod_folder_name, self.current_mod_name)
        else:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            self.current_mod_name = data.get("name", mod_folder_name)
            self.global_columns = data.get("columns", 1)
            self.global_rows = data.get("rows", 1)
            self.config_version = data.get("version", 1)
            
            behavior_data = data.get("behavior", {})
            self.can_fly = behavior_data.get("can_fly", False)
            
            self.max_health = behavior_data.get("max_health", 100)
            self.attack_damage = behavior_data.get("attack_damage", 10)
            self.attack_range = behavior_data.get("attack_range", 50)
            self.jump_height = behavior_data.get("jump_height", 15)
            
            self.animations.clear()
            anim_data = data.get("animations", {})
            
            for state in PetState:
                if state.value in anim_data:
                    raw_meta = anim_data[state.value]
                    
                    # Migration: Convert V2 'frames' to V3 'start_frame' & 'end_frame'
                    if "frames" in raw_meta:
                        raw_meta["start_frame"] = 0
                        raw_meta["end_frame"] = max(0, raw_meta.pop("frames") - 1)
                        
                    self.animations[state] = AnimationMeta(**raw_meta)
                else:
                    self.animations[state] = AnimationMeta(row=0, start_frame=0, end_frame=0)
        
        # Reset any previously loaded script
        self.custom_behavior = None
        
        # Check for a custom script in the target mod folder
        behavior_path = os.path.join(mod_path, "behavior.py")
        if os.path.exists(behavior_path):
            try:
                # Dynamically compile and load the Python file
                spec = importlib.util.spec_from_file_location("mod_behavior", behavior_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, "Behavior"):
                        self.custom_behavior = module.Behavior()
                    else:
                        print(
                            f"Warning: {mod_folder_name}/behavior.py "
                            "is missing the 'Behavior' class, using defaults."
                        )
            except Exception as e:
                print(f"Failed to load behavior.py for {mod_folder_name}: {e}")

        sheet: QPixmap = QPixmap(sprite_path)
        if sheet.isNull():
            return False
            
        self._global_sheet = sheet
        return True

    def save_mod_config(self, mod_folder_name: str, name: str) -> None:
        mod_path = os.path.join(self.mods_dir, mod_folder_name)
        config_path = os.path.join(mod_path, "config.json")
        
        data = {
            "version": CURRENT_CONFIG_VERSION,
            "name": name,
            "columns": self.global_columns,
            "rows": self.global_rows,
            "behavior": {
                "can_fly": self.can_fly,
                "max_health": self.max_health,
                "attack_damage": self.attack_damage,
                "attack_range": self.attack_range,
                "jump_height": self.jump_height
            },
            # Because self.animations is strictly Enums, .value works safely
            "animations": {
                state.value: asdict(meta) for state, meta in self.animations.items()
            }
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_frame(self, state: PetState, tick_index: int) -> Optional[QPixmap]:
        if not self._global_sheet: return None
        anim_meta = self.animations.get(state)
        if not anim_meta: return None

        # Determine the length of the slice
        total_play_frames = max(1, (anim_meta.end_frame - anim_meta.start_frame) + 1)
        
        # Handle Looping vs Clamping
        if anim_meta.loop:
            mapped_index = tick_index % total_play_frames
        else:
            # If not looping, hold on the final frame indefinitely (e.g. death state)
            mapped_index = min(tick_index, total_play_frames - 1)
            
        # Handle Reversing
        if anim_meta.reverse:
            mapped_index = (total_play_frames - 1) - mapped_index
            
        # Offset by the starting frame to find the actual grid column
        actual_sheet_index = anim_meta.start_frame + mapped_index
        
        cache_key = (self.current_mod_name, state, actual_sheet_index)
        if cache_key in ModManager._shared_frame_cache:
            return ModManager._shared_frame_cache[cache_key]

        base_w = self._global_sheet.width() // max(1, self.global_columns)
        base_h = self._global_sheet.height() // max(1, self.global_rows)
        
        final_w = anim_meta.override_width if anim_meta.override_width > 0 else base_w
        final_h = anim_meta.override_height if anim_meta.override_height > 0 else base_h

        # Extract using the actual spatial sheet index
        x_pos = (actual_sheet_index * final_w) + anim_meta.offset_x
        y_pos = (anim_meta.row * base_h) + anim_meta.offset_y 
        
        crop_rect = QRect(x_pos, y_pos, final_w, final_h)
        frame = self._global_sheet.copy(crop_rect)
        
        # Save to the shared class-level cache
        ModManager._shared_frame_cache[cache_key] = frame
        
        return frame
import json, os

from typing import Dict, List, Optional
from dataclasses import asdict

from PySide6.QtGui import QPixmap
from PySide6.QtCore import QRect

from pytoningans.core.constants import PetState, AnimationMeta

class ModManager:
    def __init__(self, mods_dir: str = "assets/mods") -> None:
        self.mods_dir: str = mods_dir
        self._global_sheet: Optional[QPixmap] = None
        self._frame_cache: Dict[str, QPixmap] = {}
        
        self.current_mod_name: str = ""
        self.global_columns: int = 1
        self.global_rows: int = 1
        self.animations: Dict[PetState, AnimationMeta] = {}

    def get_available_mods(self) -> List[str]:
        """Returns a list of folder names in the mods directory."""
        if not os.path.exists(self.mods_dir):
            os.makedirs(self.mods_dir)
        return [f.name for f in os.scandir(self.mods_dir) if f.is_dir()]

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
            self.animations = {
                state: AnimationMeta(row=i, frames=4)
                for i, state in enumerate(PetState)
            }
            self.save_mod_config(mod_folder_name, self.current_mod_name)
        else:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            self.current_mod_name = data.get("name", mod_folder_name)
            self.global_columns = data.get("columns", 1)
            self.global_rows = data.get("rows", 1)
            
            behavior_data = data.get("behavior", {})
            self.can_fly = behavior_data.get("can_fly", False)
            
            self.animations = {}
            for state_str, meta_dict in data.get("animations", {}).items():
                try:
                    self.animations[PetState(state_str)] = AnimationMeta(**meta_dict)
                except ValueError:
                    pass

        sheet: QPixmap = QPixmap(sprite_path)
        if sheet.isNull():
            return False
            
        self._global_sheet = sheet
        self._frame_cache.clear()
        return True

    def save_mod_config(self, mod_folder_name: str, name: str) -> None:
        mod_path = os.path.join(self.mods_dir, mod_folder_name)
        config_path = os.path.join(mod_path, "config.json")
        
        data = {
            "name": name,
            "columns": self.global_columns,
            "rows": self.global_rows,
            "behavior": {
                "can_fly": self.can_fly
            },
            "animations": {
                state.value: asdict(meta) for state, meta in self.animations.items()
            }
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_frame(self, state: PetState, frame_index: int) -> Optional[QPixmap]:
        if not self._global_sheet:
            return None
            
        anim_meta = self.animations.get(state)
        if not anim_meta:
            return None

        # Calculate the looped safe index FIRST
        safe_index: int = frame_index % anim_meta.frames
        
        # Use the safe index to build the cache key
        cache_key: str = f"{state.value}_{safe_index}"
        
        if cache_key in self._frame_cache:
            return self._frame_cache[cache_key]

        # CALCULATE DYNAMIC GRID
        base_w: int = self._global_sheet.width() // max(1, self.global_columns)
        base_h: int = self._global_sheet.height() // max(1, self.global_rows)
        
        # USE OVERRIDES IF > 0, OTHERWISE USE GRID
        final_w: int = anim_meta.override_width if anim_meta.override_width > 0 else base_w
        final_h: int = anim_meta.override_height if anim_meta.override_height > 0 else base_h

        x_pos: int = (safe_index * final_w) + anim_meta.offset_x
        y_pos: int = (anim_meta.row * base_h) + anim_meta.offset_y 
        
        crop_rect: QRect = QRect(x_pos, y_pos, final_w, final_h)
        frame: QPixmap = self._global_sheet.copy(crop_rect)
        self._frame_cache[cache_key] = frame
        
        return frame
import shutil
from pathlib import Path

from typing import Tuple, Any, Optional
from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap

from pytoningans.core.mod_manager import ModManager
from pytoningans.core.constants import EntityState, AnimationMeta

class ModEditorController:
    """Handles data bridging between the UI and the ModManager."""
    def __init__(self, mod_manager: ModManager) -> None:
        self.manager: ModManager = mod_manager

    def get_mod_list(self) -> dict[str, str]:
        return self.manager.get_available_mods()

    def load_mod(self, folder: str) -> bool:
        return self.manager.load_mod(folder)

    def save_mod(self, folder: str) -> None:
        self.manager.save_mod_config(folder, self.manager.current_mod_name)

    def get_global_grid(self) -> Tuple[int, int]:
        return self.manager.global_columns, self.manager.global_rows

    def update_global_grid(self, cols: int, rows: int) -> None:
        self.manager.global_columns = cols
        self.manager.global_rows = rows
        self.manager._resolve_dimensions() # Recalculate base tile sizes
        self.manager.clear_shared_cache()  # Flush old grid cuts

    def get_meta(self, state: str) -> AnimationMeta:
        return self.manager.animations.get(state, AnimationMeta(row=0, start_frame=0, end_frame=1))

    def update_meta(self, state: str, meta: AnimationMeta) -> None:
        self.manager.animations[state] = meta
        self.manager._resolve_dimensions()
        self.manager.clear_shared_cache()

    def get_frame(self, state: str, frame_index: int) -> Optional[QPixmap]:
        return self.manager.get_frame(state, frame_index)
        
    def has_mapped_row(self, state: str) -> Tuple[bool, int]:
        meta: Optional[AnimationMeta] = self.manager.animations.get(state)
        return (True, meta.row) if meta else (False, 0)
    
    def get_sheet_info(self) -> Tuple[int, int, int, int]:
        """Returns (sheet_width, sheet_height, base_tile_width, base_tile_height)."""
        sheet: Optional[QPixmap] = self.manager._global_sheet
        if sheet is None: return 0, 0, 0, 0
            
        sw, sh = sheet.width(), sheet.height()
        cols: int = max(1, self.manager.global_columns)
        rows: int = max(1, self.manager.global_rows)
        return sw, sh, sw // cols, sh // rows
    
    def get_behavior_stats(self) -> dict[str, Any]:
        return {
            "type": self.manager.behavior_type,
            "can_fly": self.manager.can_fly,
            "max_health": self.manager.max_health,
            "attack_damage": self.manager.attack_damage,
            "attack_range": self.manager.attack_range,
            "jump_height": self.manager.jump_height,
            "attack_type": self.manager.attack_type,
        }

    def update_behavior_stats(self, stats: dict[str, Any]) -> None:
        self.manager.behavior_type = stats.get("type", self.manager.behavior_type)
        self.manager.can_fly = stats.get("can_fly", self.manager.can_fly)
        self.manager.max_health = stats.get("max_health", self.manager.max_health)
        self.manager.attack_damage = stats.get("attack_damage", self.manager.attack_damage)
        self.manager.attack_range = stats.get("attack_range", self.manager.attack_range)
        self.manager.jump_height = stats.get("jump_height", self.manager.jump_height)
        self.manager.attack_type = stats.get("attack_type", self.manager.attack_type)
    
    def get_raw_preview(self, state: str, frame_index: int) -> Tuple[Optional[QPixmap], QRect]:
        """Returns the uncropped base tile and the QRect representing the custom crop area."""
        sheet: Optional[QPixmap] = self.manager._global_sheet
        if not sheet: return None, QRect()
        
        meta: Optional[AnimationMeta] = self.manager.animations.get(state)
        if not meta: return None, QRect()
        
        # Determine actual frame index
        total_frames: int = max(1, (meta.end_frame - meta.start_frame) + 1)
        mapped: int = frame_index % total_frames if meta.loop else min(frame_index, total_frames - 1)
        if meta.reverse:
            mapped = (total_frames - 1) - mapped
            
        actual_sheet_index: int = meta.start_frame + mapped
        
        # Extract the raw grid tile (No offsets applied yet)
        cols: int = max(1, self.manager.global_columns)
        rows: int = max(1, self.manager.global_rows)
        base_w: int = sheet.width() // cols
        base_h: int = sheet.height() // rows
        
        # Pad the extracted background so you don't lose the ability to expand the crop box
        final_w: int = meta.override_width if meta.override_width > 0 else base_w
        final_h: int = meta.override_height if meta.override_height > 0 else base_h
        
        origin_x: int = actual_sheet_index * final_w
        origin_y: int = meta.row * base_h
        
        display_w: int = max(base_w, final_w * 2)
        display_h: int = max(base_h, final_h * 2)
        
        raw_rect = QRect(origin_x, origin_y, display_w, display_h)
        raw_tile = sheet.copy(raw_rect)
        
        crop_rect: QRect = QRect(meta.offset_x, meta.offset_y, final_w, final_h)
        
        return raw_tile, crop_rect
    
    def bake_sprite_sheet(self) -> bool:
        return self.manager.bake_sprite_sheet()
    
    def apply_crop_to_all(self, source_state: str) -> None:
        """Copies the crop offsets and dimensions of the source state to all other states."""
        source_meta: Optional[AnimationMeta] = self.manager.animations.get(source_state)
        if source_meta is None: return
        
        for state, meta in self.manager.animations.items():
            if state != source_state:
                meta.override_width = source_meta.override_width
                meta.override_height = source_meta.override_height
                meta.offset_x = source_meta.offset_x
                meta.offset_y = source_meta.offset_y
        
        self.manager._resolve_dimensions()
        self.manager.clear_shared_cache()
    
    def get_mod_name(self) -> str:
        return self.manager.current_mod_name

    def update_mod_name(self, name: str) -> None:
        self.manager.current_mod_name = name
    
    def get_config_version(self) -> int:
        return self.manager.config_version
    
    def replace_sprite_sheet(self, mod_folder: str, new_image_path: str) -> None:
        target_path: Path = self.manager.mods_dir / mod_folder / "sprite_sheet.png"
        shutil.copy(new_image_path, target_path)
        self.manager.clear_shared_cache()
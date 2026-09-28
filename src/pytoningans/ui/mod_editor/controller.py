from typing import Tuple, Any

from pytoningans.core.mod_manager import ModManager
from pytoningans.core.constants import PetState, AnimationMeta

class ModEditorController:
    """Handles data bridging between the UI and the ModManager."""
    def __init__(self, mod_manager: ModManager) -> None:
        self.manager: ModManager = mod_manager

    def get_mod_list(self) -> list[str]:
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

    def get_meta(self, state: PetState) -> AnimationMeta:
        return self.manager.animations.get(state, AnimationMeta(row=0, start_frame=0, end_frame=1))

    def update_meta(self, state: PetState, meta: AnimationMeta) -> None:
        self.manager.animations[state] = meta
        self.manager.clear_shared_cache()

    def get_frame(self, state: PetState, frame_index: int):
        return self.manager.get_frame(state, frame_index)
        
    def has_mapped_row(self, state: PetState) -> Tuple[bool, int]:
        meta = self.manager.animations.get(state)
        return (True, meta.row) if meta else (False, 0)
    
    def get_sheet_info(self) -> Tuple[int, int, int, int]:
        """Returns (sheet_width, sheet_height, base_tile_width, base_tile_height)."""
        sheet = self.manager._global_sheet
        if not sheet:
            return 0, 0, 0, 0
            
        sw, sh = sheet.width(), sheet.height()
        cols = max(1, self.manager.global_columns)
        rows = max(1, self.manager.global_rows)
        return sw, sh, sw // cols, sh // rows
    
    def get_behavior(self) -> bool:
        return self.manager.can_fly

    def update_behavior(self, can_fly: bool) -> None:
        self.manager.can_fly = can_fly
    
    def get_behavior_stats(self) -> dict[str, Any]:
        return {
            "type": self.manager.behavior_type,
            "can_fly": self.manager.can_fly,
            "max_health": self.manager.max_health,
            "attack_damage": self.manager.attack_damage,
            "attack_range": self.manager.attack_range,
            "jump_height": self.manager.jump_height
        }

    def update_behavior_stats(self, stats: dict[str, Any]) -> None:
        self.manager.behavior_type = stats.get("type", self.manager.behavior_type)
        self.manager.can_fly = stats.get("can_fly", self.manager.can_fly)
        self.manager.max_health = stats.get("max_health", self.manager.max_health)
        self.manager.attack_damage = stats.get("attack_damage", self.manager.attack_damage)
        self.manager.attack_range = stats.get("attack_range", self.manager.attack_range)
        self.manager.jump_height = stats.get("jump_height", self.manager.jump_height)
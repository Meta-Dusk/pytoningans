from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ..config_schema import ModConfig
from ..constants import (
    AnimationMeta, EntityState, EntityType, ItemState, StructureState,
)


def parse_animations(
    anim_data: dict[str, Any],
    entity_type: str,
) -> dict[str, AnimationMeta]:
    """Parses raw animation dictionaries from config.json into AnimationMeta instances."""
    animations: dict[str, AnimationMeta] = {}
    item_valid_keys: set[str] = {s.value for s in ItemState}
    clean_keys: set[str] = {f.name for f in AnimationMeta.__dataclass_fields__.values()}

    for state_key, raw_meta in anim_data.items():
        # For item entities, ignore legacy living entity animation states
        if entity_type == EntityType.ITEM and state_key not in item_valid_keys:
            continue
        meta_dict: dict[str, Any] = dict(raw_meta)
        if "frames" in meta_dict:
            meta_dict["start_frame"] = 0
            meta_dict["end_frame"] = max(0, meta_dict.pop("frames") - 1)
        # Remove any unwanted legacy fields before initializing AnimationMeta
        filtered: dict[str, Any] = {k: v for k, v in meta_dict.items() if k in clean_keys}
        animations[str(state_key)] = AnimationMeta(**filtered)

    return animations


def ensure_fallback_animations(
    animations: dict[str, AnimationMeta],
    entity_type: str,
    global_columns: int,
) -> None:
    """Ensures standard enum states exist as fallbacks for the entity type."""
    if entity_type == EntityType.STRUCTURE:
        state_enum = StructureState
    elif entity_type == EntityType.ITEM:
        state_enum = ItemState
    else:
        state_enum = EntityState

    cols: int = max(1, global_columns)
    for state in state_enum:
        key_str: str = state.value
        if key_str in animations: continue
        animations[key_str] = AnimationMeta(
            row=0,
            start_frame=0,
            end_frame=max(0, cols - 1),
            loop=True,
        )


def sync_static_physics(animations: dict[str, AnimationMeta]) -> None:
    """For static entities/items/structures, ensures baseline physics match across all states and clears overrides."""
    if not animations: return
    base_meta: Optional[AnimationMeta] = (
        animations.get(ItemState.IDLE)
        or animations.get("idle")
        or animations.get("default")
        or next(iter(animations.values()), None)
    )
    if base_meta is None:
        return

    for meta in animations.values():
        if meta is base_meta:
            continue
        meta.anchor_x = base_meta.anchor_x
        meta.anchor_y = base_meta.anchor_y
        meta.hitbox_x = base_meta.hitbox_x
        meta.hitbox_y = base_meta.hitbox_y
        meta.hitbox_w = base_meta.hitbox_w
        meta.hitbox_h = base_meta.hitbox_h
        meta.has_hold_point = base_meta.has_hold_point
        meta.hold_x = base_meta.hold_x
        meta.hold_y = base_meta.hold_y
        meta.frame_overrides.clear()


sync_static_item_physics = sync_static_physics


def ensure_config_file(config_path: Path, mod_folder_name: str) -> None:
    """Auto-scaffolds a default config.json using ModConfig if none exists."""
    if not config_path.exists():
        new_config = ModConfig(name=mod_folder_name)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(new_config.to_dict(), f, indent=4)


def save_config_file(config_path: Path, config: ModConfig) -> None:
    """Serializes a ModConfig instance to config.json with indentation."""
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=4)


from __future__ import annotations

import json
from pathlib import Path

from pytoningans.core.constants import EntityType

IGNORED_MOD_FOLDERS: set[str] = {"api", "__pycache__"}


def get_available_mods_with_type(
    mods_dir: Path, ignored_folders: set[str] = IGNORED_MOD_FOLDERS
) -> dict[str, tuple[str, str]]:
    """Scans mods_dir and returns a dict mapping folder_name -> (display_name, entity_type)."""
    valid_mods: dict[str, tuple[str, str]] = {}
    if not mods_dir.exists():
        return valid_mods

    for item in mods_dir.iterdir():
        if (
            not item.is_dir()
            or item.name.startswith(("_", "."))
            or item.name.lower() in ignored_folders
        ):
            continue

        # A valid mod must contain a sprite sheet or config
        if not (item / "sprite_sheet.png").exists() and not (item / "config.json").exists():
            continue

        folder_name: str = item.name
        display_name: str = folder_name
        entity_type: str = EntityType.ENTITY.value

        config_path: Path = item / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    display_name = data.get("name", folder_name)
                    entity_type = data.get("entity_type", EntityType.ENTITY.value)
            except Exception:
                pass

        valid_mods[folder_name] = (display_name, entity_type)

    return valid_mods


def is_mod_static(mod_path: Path) -> bool:
    """Checks whether the mod at mod_path is static (single-sprite / non-animated)."""
    config_path = mod_path / "config.json"
    if not config_path.exists():
        return False
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("is_static", False):
                return True
            if data.get("columns", 1) == 1 and data.get("rows", 1) == 1:
                etype = data.get("entity_type", EntityType.ENTITY.value)
                if etype in (EntityType.ITEM.value, EntityType.STRUCTURE.value):
                    return True
    except Exception:
        pass
    return False


def get_mod_type_display(entity_type: str, is_static: bool = False) -> str:
    """Returns a user-friendly label for the mod entity type and animated/static nature."""
    if entity_type == EntityType.ITEM.value:
        return "Static Item" if is_static else "Animated Item"
    elif entity_type == EntityType.STRUCTURE.value:
        return "Static Structure" if is_static else "Animated Structure"
    elif is_static:
        return "Static Entity"
    else:
        return "Living Entity"


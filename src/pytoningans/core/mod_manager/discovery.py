from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pytoningans.core.constants import EntityType
from .modpack import ModPack, ModPackRegistry, load_pack_manifest, ModPackConfig

IGNORED_MOD_FOLDERS: set[str] = {"api", "__pycache__"}


@dataclass(slots=True, kw_only=True)
class ModEntryInfo:
    """Rich metadata for a discovered mod or pack-contained sub-entity."""
    mod_id: str
    display_name: str
    entity_type: str
    is_static: bool
    folder_path: Path
    pack_id: Optional[str] = None
    pack_name: Optional[str] = None
    tags: list[str] = field(default_factory=list)


def _scan_sub_entities_in_pack(
    pack_dir: Path, pack_id: str, pack_name: str
) -> list[ModEntryInfo]:
    """Discovers all entity/item/structure definitions within a modpack folder."""
    results: list[ModEntryInfo] = []

    # Search category folders: entities/, items/, structures/
    category_dirs: list[tuple[Path, EntityType]] = [
        (pack_dir / "entities", EntityType.ENTITY),
        (pack_dir / "items", EntityType.ITEM),
        (pack_dir / "structures", EntityType.STRUCTURE),
    ]

    found_dirs: set[Path] = set()

    for cat_dir, default_type in category_dirs:
        if not cat_dir.is_dir():
            continue
        for sub_dir in cat_dir.iterdir():
            if not sub_dir.is_dir() or sub_dir.name.startswith(("_", ".")) or sub_dir.name == "__pycache__":
                continue
            if not (sub_dir / "sprite_sheet.png").exists() and not (sub_dir / "config.json").exists():
                continue

            found_dirs.add(sub_dir.resolve())
            relative_name: str = f"{cat_dir.name}/{sub_dir.name}"
            mod_id: str = f"{pack_id}:{relative_name}"
            display_name, entity_type, tags, is_static = _parse_mod_meta(sub_dir, default_type)

            results.append(
                ModEntryInfo(
                    mod_id=mod_id,
                    display_name=display_name,
                    entity_type=entity_type,
                    is_static=is_static,
                    folder_path=sub_dir,
                    pack_id=pack_id,
                    pack_name=pack_name,
                    tags=tags,
                )
            )

    # Also search direct subdirectories with config.json/sprite_sheet.png
    for sub_dir in pack_dir.iterdir():
        if (
            not sub_dir.is_dir()
            or sub_dir.name.startswith(("_", "."))
            or sub_dir.name in ("entities", "items", "structures", "__pycache__", "assets")
        ):
            continue
        if sub_dir.resolve() in found_dirs:
            continue
        if not (sub_dir / "sprite_sheet.png").exists() and not (sub_dir / "config.json").exists():
            continue

        mod_id: str = f"{pack_id}:{sub_dir.name}"
        display_name, entity_type, tags, is_static = _parse_mod_meta(sub_dir, EntityType.ENTITY)
        results.append(
            ModEntryInfo(
                mod_id=mod_id,
                display_name=display_name,
                entity_type=entity_type,
                is_static=is_static,
                folder_path=sub_dir,
                pack_id=pack_id,
                pack_name=pack_name,
                tags=tags,
            )
        )

    return results


def _parse_mod_meta(
    mod_dir: Path, default_type: str = EntityType.ENTITY
) -> tuple[str, str, list[str], bool]:
    """Extracts (display_name, entity_type, tags, is_static) from a mod directory."""
    display_name: str = mod_dir.name
    entity_type: str = default_type
    tags: list[str] = []
    is_static: bool = False

    config_path: Path = mod_dir / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
                display_name = data.get("name", mod_dir.name)
                entity_type = data.get("entity_type", default_type)
                behavior_data: dict[str, Any] = data.get("behavior", {})
                raw_tags: list[str] = data.get("tags", behavior_data.get("tags", []))
                tags = [t.lower().strip() for t in raw_tags if isinstance(t, str) and t.strip()]
                is_static = data.get("is_static", False)
                if not is_static and entity_type in (EntityType.ITEM, EntityType.STRUCTURE):
                    if data.get("columns", 1) == 1 and data.get("rows", 1) == 1:
                        is_static = True
        except Exception:
            pass

    return display_name, entity_type, tags, is_static


def get_available_mods_with_type(
    mods_dir: Path, ignored_folders: set[str] = IGNORED_MOD_FOLDERS
) -> dict[str, tuple[str, str]]:
    """
    Scans mods_dir and returns a dict mapping mod_id -> (display_name, entity_type).
    Discovers both Tier 1 Standalone Mods and Tier 2 Modpacks.
    """
    valid_mods: dict[str, tuple[str, str]] = {}
    if not mods_dir.exists():
        return valid_mods

    entries: list[ModEntryInfo] = get_detailed_mod_list(mods_dir, ignored_folders)
    for entry in entries:
        label: str
        if entry.pack_name:
            label = f"[{entry.pack_name}] {entry.display_name}"
        else:
            label = entry.display_name
        valid_mods[entry.mod_id] = (label, entry.entity_type)

    return valid_mods


def get_detailed_mod_list(
    mods_dir: Path, ignored_folders: set[str] = IGNORED_MOD_FOLDERS
) -> list[ModEntryInfo]:
    """Returns a full list of ModEntryInfo for all standalone mods and pack sub-entities."""
    results: list[ModEntryInfo] = []
    if not mods_dir.exists():
        return results

    for item in sorted(mods_dir.iterdir(), key=lambda p: p.name.lower()):
        if (
            not item.is_dir()
            or item.name.startswith(("_", "."))
            or item.name.lower() in ignored_folders
        ):
            continue

        # Case 1: Tier 2 Modpack (Contains pack.json)
        if (item / "pack.json").exists():
            pack_manifest = load_pack_manifest(item)
            pack_id: str = pack_manifest.id if pack_manifest else item.name
            pack_name: str = pack_manifest.name if pack_manifest else pack_id

            sub_entries = _scan_sub_entities_in_pack(item, pack_id, pack_name)
            results.extend(sub_entries)

            # Register sub-entities into ModPack registry cache
            pack_obj = ModPackRegistry.get_or_load(item)
            if pack_obj is not None:
                for sub in sub_entries:
                    pack_obj.entities[sub.mod_id] = (sub.display_name, sub.entity_type)

            continue

        # Case 2: Tier 1 Standalone Mod (Contains sprite_sheet.png or config.json)
        if (item / "sprite_sheet.png").exists() or (item / "config.json").exists():
            display_name, ent_type, tags, is_static = _parse_mod_meta(item, EntityType.ENTITY)
            results.append(
                ModEntryInfo(
                    mod_id=item.name,
                    display_name=display_name,
                    entity_type=ent_type,
                    is_static=is_static,
                    folder_path=item,
                    pack_id=None,
                    pack_name=None,
                    tags=tags,
                )
            )

    return results


def get_available_packs(
    mods_dir: Path, ignored_folders: set[str] = IGNORED_MOD_FOLDERS
) -> dict[str, ModPack]:
    """Returns a dict mapping pack_id -> ModPack for all modpacks found in mods_dir."""
    packs: dict[str, ModPack] = {}
    if not mods_dir.exists():
        return packs

    for item in mods_dir.iterdir():
        if (
            not item.is_dir()
            or item.name.startswith(("_", "."))
            or item.name.lower() in ignored_folders
        ):
            continue

        if (item / "pack.json").exists():
            pack = ModPackRegistry.get_or_load(item)
            if pack is not None:
                packs[pack.id] = pack

    return packs


def resolve_mod_path(
    mods_dir: Path, mod_id: str, debug: bool = False
) -> tuple[Optional[Path], Optional[str], Optional[str]]:
    """
    Resolves any mod_id (standalone folder name, 'pack:sub_id', or relative path)
    to (mod_dir_path, pack_id, sub_id).
    Returns (None, None, None) if not found.
    """
    if debug:
        print(
            "[resolve_mod_path] Attempting to resolve:\n"
            f" -> mods_dir: {mods_dir}\n"
            f" -> mod_id: {mod_id}"
        )
    
    if not mods_dir.exists():
        if debug:
            print(f"[resolve_mod_path] mods_dir doesn't exist!")
        return None, None, None

    # Handle namespaced modpack ID: "pack_id:sub_path"
    if ":" in mod_id:
        pack_id, sub_path = mod_id.split(":", 1)
        sub_path: str = sub_path.strip().replace("\\", "/")

        # Search for folder in mods_dir / pack_id
        pack_dir: Path = mods_dir / pack_id
        if not pack_dir.exists():
            # Search if any pack has matching manifest id
            for item in mods_dir.iterdir():
                if not item.is_dir() or not (item / "pack.json").exists():
                    continue
                manifest: Optional[ModPackConfig] = load_pack_manifest(item)
                
                if manifest is None or manifest.id != pack_id:
                    continue
                pack_dir = item
                break

        candidates: list[Path] = [
            pack_dir / sub_path,
            pack_dir / "entities" / sub_path,
            pack_dir / "items" / sub_path,
            pack_dir / "structures" / sub_path,
        ]
        for cand in candidates:
            if cand.is_dir() and (
                (cand / "config.json").exists() or (cand / "sprite_sheet.png").exists()
            ):
                if debug:
                    print(f"=> Returning: {cand}, {pack_id}, {sub_path}")
                return cand, pack_id, sub_path

        # If sub_path was e.g. "entities/hero", also try basename "hero"
        base_name: str = Path(sub_path).name
        candidates_base: list[Path] = [
            pack_dir / "entities" / base_name,
            pack_dir / "items" / base_name,
            pack_dir / "structures" / base_name,
            pack_dir / base_name,
        ]
        for cand in candidates_base:
            if cand.is_dir() and (
                (cand / "config.json").exists() or (cand / "sprite_sheet.png").exists()
            ):
                if debug:
                    print(f"=> Returning: {cand}, {pack_id}, {sub_path}")
                return cand, pack_id, sub_path
        
        if debug:
            print(f"=> Returning: None, {pack_id}, {sub_path}")
        return None, pack_id, sub_path

    # Handle direct standalone mod
    direct_path: Path = mods_dir / mod_id
    if direct_path.is_dir() and (
        (direct_path / "config.json").exists() or (direct_path / "sprite_sheet.png").exists()
    ):
        if debug:
            print(f"=> Returning: {direct_path}, None, None")
        return direct_path, None, None
    
    # Check if modpack
    if direct_path.is_dir() and (
        (direct_path / "pack.json").exists() or (direct_path / "pack.py").exists()
    ):
        if debug:
            print(f"=> Returning: {direct_path}, None, None")
        return direct_path, None, None

    # Fallback: check if mod_id matches a sub-entity inside any modpack
    for item in mods_dir.iterdir():
        if not item.is_dir() or not (item / "pack.json").exists(): continue
        cand_pack: Path = item
        manifest: Optional[ModPackConfig] = load_pack_manifest(cand_pack)
        pack_id: str = manifest.id if manifest else cand_pack.name
        for cand in [
            cand_pack / "entities" / mod_id,
            cand_pack / "items" / mod_id,
            cand_pack / "structures" / mod_id,
            cand_pack / mod_id,
        ]:
            if cand.is_dir() and (
                (cand / "config.json").exists() or (cand / "sprite_sheet.png").exists()
            ):
                if debug:
                    print(f"=> Returning: {cand}, {pack_id}, {mod_id}")
                return cand, pack_id, mod_id
            
    if debug:
        print(f"=> Failed...")
    return None, None, None


def is_mod_static(mod_path: Path) -> bool:
    """Checks whether the mod at mod_path is static (single-sprite / non-animated)."""
    config_path: Path = mod_path / "config.json"
    if not config_path.exists():
        return False
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            if data.get("is_static", False):
                return True
            if data.get("columns", 1) == 1 and data.get("rows", 1) == 1:
                entity_type: str = data.get("entity_type", EntityType.ENTITY)
                if entity_type in (EntityType.ITEM, EntityType.STRUCTURE):
                    return True
    except Exception:
        pass
    return False


def get_mod_type_display(entity_type: str, is_static: bool = False) -> str:
    """Returns a user-friendly label for the mod entity type and animated/static nature."""
    if entity_type == EntityType.ITEM:
        return "Static Item" if is_static else "Animated Item"
    elif entity_type == EntityType.STRUCTURE:
        return "Static Structure" if is_static else "Animated Structure"
    elif is_static:
        return "Static Entity"
    else:
        return "Living Entity"

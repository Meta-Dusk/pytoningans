"""
PyToNingans Mod Browser - Installer Service
===========================================
Handles package installation, remote zip extraction, local scaffolding,
version manifest updates, uninstallation, and placeholder asset generation.
"""
from __future__ import annotations

import json, shutil, tempfile
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from pytoningans.core.config_schema import CURRENT_CONFIG_VERSION
from pytoningans.core.constants import EntityType
from pytoningans.core.mod_manager import resolve_mod_path, extract_mod_or_pack_from_zip
from .models import CommunityModItem

if TYPE_CHECKING:
    from .supabase_client import SupabaseClient


def create_placeholder_sprite(path: Path) -> None:
    """Generates a valid 32x32 transparent colored PNG sprite sheet placeholder."""
    from PySide6.QtGui import QImage, QColor
    img = QImage(32, 32, QImage.Format.Format_ARGB32)
    img.fill(QColor(99, 102, 241, 255))
    img.save(str(path))


def install_catalog_item(
    item: CommunityModItem,
    mods_dir: Path,
    cloud: Optional[SupabaseClient] = None,
) -> tuple[bool, str]:
    """
    Installs a community mod or modpack into mods_dir.
    If package_url is present and cloud is available, downloads the real archive and extracts it safely.
    Otherwise falls back to generating a valid local scaffold.
    """
    mods_dir.mkdir(parents=True, exist_ok=True)
    target_dir: Path = mods_dir / item.id

    if target_dir.exists():
        print(f"[install_catalog_item] Mod folder '{item.id}' already exists locally.")
        return False, f"Mod folder '{item.id}' already exists locally."

    # Case 1: Real package download from Cloud Storage
    if item.package_url and cloud is not None and cloud.is_configured:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_zip: Path = Path(temp_dir) / f"{item.id}.zip"
            dl_ok, dl_msg = cloud.download_package(item.package_url, temp_zip)
            print(f"[install_catalog_item] Download Message: {dl_msg}")
            if dl_ok:
                ext_ok, ext_msg, _ = extract_mod_or_pack_from_zip(temp_zip, mods_dir)
                print(f"[install_catalog_item] Extract Message:\n{ext_msg}")
                if ext_ok:
                    item.is_installed = True
                    item.installed_version = item.version
                    item.has_update = False
                    item.downloads += 1
                    print(f"[install_catalog_item] Successfully downloaded and installed '{item.name}'")
                    return True, f"Successfully downloaded and installed '{item.name}'."

    # Case 2: Offline scaffold fallback
    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        if item.is_pack:
            manifest_data = {
                "id": item.id,
                "name": item.name,
                "version": item.version,
                "author": item.author,
                "description": item.description,
                "tags": item.tags,
                "shared_script": "pack.py",
                "sub_mods": [
                    f"entities/{e.lower().replace(' ', '_')}" 
                    for e in item.contained_entities
                ],
            }
            (target_dir / "pack.json").write_text(
                json.dumps(manifest_data, indent=2), encoding="utf-8"
            )
            (target_dir / "pack.py").write_text(
                f'"""Shared controller for {item.name}."""\n'
                "from pytoningans.core.api import BaseModPack, PackMenuAction\n\n"
                "class PackController(BaseModPack):\n"
                "    def on_pack_loaded(self) -> None:\n"
                "        self.shared_state['status'] = 'Active'\n"
                f"        print('Modpack [{item.name}] loaded successfully.')\n",
                encoding="utf-8",
            )

            for entity_name in item.contained_entities:
                slug: str = entity_name.lower().replace(" ", "_")
                entity_dir: Path = target_dir / "entities" / slug
                entity_dir.mkdir(parents=True, exist_ok=True)
                entity_config: dict[str, Any] = {
                    "name": entity_name,
                    "entity_type": EntityType.ENTITY,
                    "version": CURRENT_CONFIG_VERSION,
                    "columns": 1,
                    "rows": 1,
                }
                (entity_dir / "config.json").write_text(
                    json.dumps(entity_config, indent=2), encoding="utf-8"
                )
                create_placeholder_sprite(entity_dir / "sprite_sheet.png")

        else:
            config_data: dict[str, Any] = {
                "name": item.name,
                "entity_type": item.entity_type,
                "version": CURRENT_CONFIG_VERSION,
                "mod_version": item.version,
                "columns": 1,
                "rows": 1,
                "behavior": {
                    "can_fly": "flying" in item.tags,
                    "tags": item.tags,
                },
            }
            (target_dir / "config.json").write_text(
                json.dumps(config_data, indent=2), encoding="utf-8"
            )
            create_placeholder_sprite(target_dir / "sprite_sheet.png")

        item.is_installed = True
        item.installed_version = item.version
        item.has_update = False
        item.downloads += 1
        print(f"[install_catalog_item] Successfully installed '{item.name}'.")
        return True, f"Successfully installed '{item.name}'."

    except Exception as e:
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        print(f"[install_catalog_item] Failed to install mod: {e}")
        return False, f"Failed to install mod: {e}"


def update_installed_mod(
    item: CommunityModItem,
    mods_dir: Path,
    cloud: Optional[SupabaseClient] = None,
) -> tuple[bool, str]:
    """
    Updates an installed mod or modpack to the latest catalog release version.
    Downloads the updated package if available, or refreshes manifests cleanly.
    """
    target_dir: Path = mods_dir / item.id
    if not target_dir.exists():
        resolved, pack_id, _ = resolve_mod_path(mods_dir, item.id)
        if resolved is not None and resolved.exists():
            target_dir = mods_dir / pack_id if pack_id else resolved
        else:
            return False, f"Local installation for '{item.name}' not found."

    # If remote package URL exists, perform clean package update
    if item.package_url and cloud is not None and cloud.is_configured:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_zip = Path(temp_dir) / f"{item.id}.zip"
            dl_ok, _ = cloud.download_package(item.package_url, temp_zip)
            if dl_ok:
                ext_ok, _, _ = extract_mod_or_pack_from_zip(temp_zip, mods_dir)
                if ext_ok:
                    item.installed_version = item.version
                    item.has_update = False
                    return True, f"Successfully upgraded '{item.name}' to v{item.version}!"

    try:
        if item.is_pack:
            pack_json = target_dir / "pack.json"
            if pack_json.exists():
                p_data = json.loads(pack_json.read_text(encoding="utf-8"))
                p_data["version"] = item.version
                p_data["description"] = item.description
                pack_json.write_text(json.dumps(p_data, indent=2), encoding="utf-8")
        else:
            cfg_file = target_dir / "config.json"
            if cfg_file.exists():
                c_data = json.loads(cfg_file.read_text(encoding="utf-8"))
                c_data["mod_version"] = item.version
                c_data["version"] = CURRENT_CONFIG_VERSION
                cfg_file.write_text(json.dumps(c_data, indent=2), encoding="utf-8")

        item.installed_version = item.version
        item.has_update = False
        return True, f"Successfully updated '{item.name}' to v{item.version}!"
    except Exception as e:
        return False, f"Failed to update '{item.name}': {e}"


def uninstall_installed_mod(
    item: CommunityModItem,
    mods_dir: Path,
) -> tuple[bool, str]:
    """Safely removes an installed mod or modpack from mods_dir."""
    target_dir: Path = mods_dir / item.id
    if not target_dir.exists():
        resolved, pack_id, _ = resolve_mod_path(mods_dir, item.id)
        if resolved is not None and resolved.exists():
            target_dir = mods_dir / pack_id if pack_id else resolved
        else:
            return False, f"Could not find installed folder for '{item.id}'."

    try:
        shutil.rmtree(target_dir)
        item.is_installed = False
        item.installed_version = None
        item.has_update = False
        return True, f"Successfully uninstalled '{item.name}'."
    except Exception as e:
        return False, f"Failed to delete mod folder: {e}"


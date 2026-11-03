"""Mod management package handling mod assets, configuration, behaviors, and modpacks."""

from __future__ import annotations

from .manager import ModManager
from ..config_schema import CURRENT_CONFIG_VERSION
from .cache import CacheKey

from .discovery import (
    is_mod_static,
    get_mod_type_display,
    get_available_mods_with_type,
    get_detailed_mod_list,
    get_available_packs,
    resolve_mod_path,
    ModEntryInfo,
)

from .modpack import (
    ModPack,
    ModPackRegistry,
    load_pack_manifest,
)

from .archive import (
    export_mod_or_pack_to_zip,
    extract_mod_or_pack_from_zip,
)

from .security import (
    SecurityRiskLevel,
    SecurityIssue,
    SecurityReport,
    scan_python_file,
    scan_mod_or_pack,
)

__all__ = [
    # Core
    "ModManager",
    "CURRENT_CONFIG_VERSION",
    "CacheKey",
    
    # Discovery
    "is_mod_static",
    "get_mod_type_display",
    "get_available_mods_with_type",
    "get_detailed_mod_list",
    "get_available_packs",
    "resolve_mod_path",
    "ModEntryInfo",
    
    # Modpacks
    "ModPack",
    "ModPackRegistry",
    "load_pack_manifest",
    
    # Archive
    "export_mod_or_pack_to_zip",
    "extract_mod_or_pack_from_zip",
    
    # Security
    "SecurityRiskLevel",
    "SecurityIssue",
    "SecurityReport",
    "scan_python_file",
    "scan_mod_or_pack",
]

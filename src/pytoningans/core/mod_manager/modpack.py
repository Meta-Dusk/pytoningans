"""
PyToNingans Modpack Architecture (Tier 2 Content Packs)
=======================================================
Provides discovery, manifest parsing, runtime shared state, and dynamic loading
for bundled packs containing multiple entities, items, and structures.
"""
from __future__ import annotations

import json, importlib.util, inspect, sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, cast

from pytoningans.core.config_schema import ModPackConfig
from pytoningans.core.api import BaseModPack, PackMenuAction,IEntity

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity


class ModPack:
    """Runtime instance of a loaded content pack."""

    def __init__(self, manifest: ModPackConfig, folder_path: Path) -> None:
        self.manifest: ModPackConfig = manifest
        self.folder_path: Path = folder_path
        self.controller: Optional[BaseModPack] = None
        self.shared_state: dict[str, Any] = {}
        
        self.entities: dict[str, tuple[str, str]] = {}
        """Mapping of sub_id -> (display_name, entity_type)"""

    @property
    def id(self) -> str:
        return self.manifest.id

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    @property
    def author(self) -> str:
        return self.manifest.author

    @property
    def description(self) -> str:
        return self.manifest.description

    def on_entity_spawned(self, entity: BaseEntity) -> None:
        """Notifies the pack controller when one of its child entities is spawned."""
        if self.controller is None: return
        try:
            self.controller.on_entity_spawned(cast(Any, entity))
        except Exception as e:
            print(f"Error in {self.id} on_entity_spawned: {e}")

    def get_context_menu_actions(self, entity: BaseEntity) -> list[PackMenuAction]:
        """
        Collects custom context menu actions defined by the pack controller for this entity.
        """
        if self.controller is not None:
            try:
                return self.controller.get_context_menu_actions(cast(IEntity, entity))
            except Exception as e:
                print(f"Error in {self.id} get_context_menu_actions: {e}")
        return []


def load_pack_manifest(pack_dir: Path) -> Optional[ModPackConfig]:
    """Reads and parses pack.json from pack_dir. Returns None if invalid or missing."""
    manifest_path: Path = pack_dir / "pack.json"
    if not manifest_path.exists():
        return None

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        pack_id: str = data.get("id", pack_dir.name).strip() or pack_dir.name
        pack_name: str = data.get("name", pack_id).strip() or pack_id
        version: str = str(data.get("version", "1.0.0"))
        author: str = data.get("author", "")
        description: str = data.get("description", "")
        shared_script: str = data.get("shared_script", "pack.py")
        tags: list[str] = [
            t.lower().strip() for t in data.get("tags", [])
            if isinstance(t, str) and t.strip()
        ]

        return ModPackConfig(
            id=pack_id,
            name=pack_name,
            version=version,
            author=author,
            description=description,
            shared_script=shared_script,
            tags=tags,
        )
    except Exception as e:
        print(f"Failed to read pack.json at {pack_dir}: {e}")
        return None


def compile_pack_controller(
    manifest: ModPackConfig, pack_dir: Path
) -> Optional[BaseModPack]:
    """
    Dynamically loads and instantiates the BaseModPack
    subclass from the pack's shared script.
    """
    script_name: str = manifest.shared_script or "pack.py"
    script_path: Path = pack_dir / script_name
    if not script_path.exists():
        return None

    try:
        # Guarantee 'import api' resolves to core API
        import pytoningans.core.api as core_api
        import pytoningans.core.api.types as api_types
        import pytoningans.core.api.components as api_components
        import pytoningans.core.api.protocols as api_protocols
        import pytoningans.core.api.behaviors as api_behaviors
        import pytoningans.core.api.modpack as api_modpack

        sys.modules["api"] = core_api
        sys.modules["api.types"] = api_types
        sys.modules["api.components"] = api_components
        sys.modules["api.protocols"] = api_protocols
        sys.modules["api.behaviors"] = api_behaviors
        sys.modules["api.modpack"] = api_modpack

        spec = importlib.util.spec_from_file_location(
            f"modpack_controller_{manifest.id}", str(script_path)
        )
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        target_base_name: str = "BaseModPack"
        for _, obj in inspect.getmembers(module, inspect.isclass):
            mro_names: list[str] = [base.__name__ for base in inspect.getmro(obj)]
            if target_base_name in mro_names and obj.__name__ != target_base_name:
                pack_cls = cast(type[BaseModPack], obj)
                instance: BaseModPack
                try:
                    instance = pack_cls(pack_info=manifest)
                except TypeError:
                    instance = pack_cls()
                instance.pack_info = manifest
                instance.on_pack_loaded()
                return instance

    except Exception as e:
        print(f"Failed to load pack script {script_name} for pack '{manifest.id}': {e}")

    return None


class ModPackRegistry:
    """Global registry maintaining shared ModPack runtime instances in memory."""

    _active_packs: dict[str, ModPack] = {}

    @classmethod
    def get_or_load(cls, pack_dir: Path) -> Optional[ModPack]:
        """Returns the cached ModPack instance or loads it from disk."""
        manifest: Optional[ModPackConfig] = load_pack_manifest(pack_dir)
        if manifest is None:
            return None

        if manifest.id in cls._active_packs:
            return cls._active_packs[manifest.id]

        pack = ModPack(manifest=manifest, folder_path=pack_dir)
        controller: Optional[BaseModPack] = compile_pack_controller(manifest, pack_dir)
        if controller is not None:
            pack.controller = controller
            pack.shared_state = controller.shared_state

        cls._active_packs[manifest.id] = pack
        return pack

    @classmethod
    def get_pack(cls, pack_id: str) -> Optional[ModPack]:
        """Retrieves a cached ModPack by id if loaded."""
        return cls._active_packs.get(pack_id)

    @classmethod
    def clear(cls) -> None:
        """Clears all cached active modpack runtime instances."""
        cls._active_packs.clear()


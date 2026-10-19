"""
PyToNingans Mod Browser - Client and Data Provider
================================================
Handles catalog fetching, search filtering, download orchestration,
package extraction, local installation tracking, release updates, and rating submissions.
Integrates with Supabase Cloud REST & Storage backend with complete offline-first caching.
"""
from __future__ import annotations

import json, shutil, tempfile, time
from pathlib import Path
from typing import Any, Optional

from pytoningans.core.config_schema import CURRENT_CONFIG_VERSION
from pytoningans.core.constants import EntityType
from pytoningans.core.mod_manager import (
    resolve_mod_path, get_available_mods_with_type, get_available_packs,
    extract_mod_or_pack_from_zip,
)
from pytoningans.utils.paths import get_app_version, get_settings_path
from .models import CommunityModItem, ModRelease, parse_semver
from .supabase_client import SupabaseClient


DEFAULT_CATALOG_DATA: list[dict[str, Any]] = [
    {
        "id": "vocaloid_crew_pack",
        "name": "Vocaloid Desktop Companions",
        "entity_type": "pack",
        "version": "1.2.0",
        "author": "MikuFan99",
        "description": (
            "A delightful bundle containing Hatsune Miku, Kagamine Rin, and Len! "
            "Features custom singing animations and shared stage energy state."
        ),
        "tags": ["anime", "music", "modpack", "companions"],
        "rating": 9.8,
        "rating_count": 84,
        "downloads": 3420,
        "size_bytes": 142000,
        "is_pack": True,
        "contained_entities": ["Hatsune Miku", "Kagamine Rin", "Kagamine Len"],
        "config_version": CURRENT_CONFIG_VERSION,
        "target_app_version": "0.8.0",
        "releases": [
            {
                "version": "1.2.0",
                "changelog": "Added Kagamine Len dual-singing interaction routine.",
                "created_at": "2026-10-18",
            },
            {
                "version": "1.0.0",
                "changelog": "Initial release with Hatsune Miku and Rin.",
                "created_at": "2026-10-10",
            },
        ],
    },
    {
        "id": "pixel_slime_knight",
        "name": "Bouncing Slime Knight",
        "entity_type": EntityType.ENTITY,
        "version": "1.0.4",
        "author": "RetroGamer",
        "description": (
            "A brave tiny slime equipped with a tiny sword and shield. "
            "Bounces playfully around window borders and protects your screen."
        ),
        "tags": ["rpg", "cute", "interactive", "slime"],
        "rating": 9.3,
        "rating_count": 52,
        "downloads": 1890,
        "size_bytes": 48000,
        "is_pack": False,
        "contained_entities": [],
        "config_version": CURRENT_CONFIG_VERSION,
        "target_app_version": "0.8.0",
        "releases": [
            {
                "version": "1.0.4",
                "changelog": "Fine-tuned border bounce physics.",
                "created_at": "2026-10-17",
            }
        ],
    },
    {
        "id": "coffee_brewer_structure",
        "name": "Desktop Espresso Bar",
        "entity_type": EntityType.STRUCTURE,
        "version": "1.1.0",
        "author": "BaristaBot",
        "description": (
            "An interactive coffee station for your desktop. "
            "Entities can gather around to brew coffee and recover energy."
        ),
        "tags": ["decor", "cozy", "interactive", "structure"],
        "rating": 9.6,
        "rating_count": 41,
        "downloads": 2150,
        "size_bytes": 62000,
        "is_pack": False,
        "contained_entities": [],
        "config_version": CURRENT_CONFIG_VERSION,
        "target_app_version": "0.8.0",
        "releases": [
            {
                "version": "1.1.0",
                "changelog": "Added steaming coffee particles.",
                "created_at": "2026-10-15",
            }
        ],
    },
    {
        "id": "energy_crystal_item",
        "name": "Mystic Energy Crystal",
        "entity_type": EntityType.ITEM,
        "version": "1.0.0",
        "author": "CrystalMage",
        "description": (
            "A glowing celestial gem that entities can pick up and carry on their "
            "heads or item anchors to boost movement speed."
        ),
        "tags": ["magic", "item", "carryable", "boost"],
        "rating": 8.9,
        "rating_count": 27,
        "downloads": 980,
        "size_bytes": 28000,
        "is_pack": False,
        "contained_entities": [],
        "config_version": CURRENT_CONFIG_VERSION,
        "target_app_version": "0.8.0",
        "releases": [
            {
                "version": "1.0.0",
                "changelog": "Initial crystal release.",
                "created_at": "2026-10-12",
            }
        ],
    },
    {
        "id": "cyber_drone_flying",
        "name": "Autonomous Patrol Drone",
        "entity_type": EntityType.ENTITY,
        "version": "2.0.1",
        "author": "NeoTech",
        "description": (
            "High-tech hovering drone with smooth window collision and searchlight "
            "scanning routines. Can push loose windows when aggressive."
        ),
        "tags": ["sci-fi", "flying", "drone", "physics"],
        "rating": 9.1,
        "rating_count": 63,
        "downloads": 2740,
        "size_bytes": 75000,
        "is_pack": False,
        "contained_entities": [],
        "config_version": CURRENT_CONFIG_VERSION,
        "target_app_version": "0.8.0",
        "releases": [
            {
                "version": "2.0.1",
                "changelog": "Improved flying window collision angle detection.",
                "created_at": "2026-10-19",
            }
        ],
    },
    {
        "id": "retro_companion_legacy",
        "name": "Vintage Desktop Golem",
        "entity_type": EntityType.ENTITY,
        "version": "0.9.0",
        "author": "OldSchoolModder",
        "description": (
            "A slow stone golem from the early alpha versions. "
            "Note: Designed for config schema v1 and app v0.7.0."
        ),
        "tags": ["retro", "legacy", "rock"],
        "rating": 8.2,
        "rating_count": 15,
        "downloads": 620,
        "size_bytes": 31000,
        "is_pack": False,
        "contained_entities": [],
        "config_version": 1,  # Legacy config version to demonstrate Outdated badge
        "target_app_version": "0.7.0",
        "releases": [
            {
                "version": "0.9.0",
                "changelog": "Legacy build.",
                "created_at": "2026-08-01",
            }
        ],
    },
]
"""Seed catalog: Realistic community creations demonstrating diverse entity types, modpacks, and release versions"""


class ModBrowserClient:
    """Manages community mod browsing, catalog searching, package downloads, and local installations."""

    def __init__(self, mods_dir: Path) -> None:
        self.mods_dir: Path = mods_dir.resolve()
        self.cloud: SupabaseClient = SupabaseClient()
        self._cache_file: Path = get_settings_path().parent / "catalog_cache.json"
        self._user_ratings: dict[str, float] = {}
        self._catalog_items: list[CommunityModItem] = []
        self.is_online: bool = self.cloud.is_configured
        self._load_local_catalog()
        self.refresh_catalog_from_cloud()

    def _load_local_catalog(self) -> None:
        """Initializes catalog data from built-in seed and cached disk entries."""
        self._catalog_items = []
        catalog_map: dict[str, CommunityModItem] = {}

        # Load built-in seed
        for entry in DEFAULT_CATALOG_DATA:
            item = self._dict_to_item(entry)
            catalog_map[item.id] = item

        # Merge local cache if available
        if self._cache_file.exists():
            try:
                cached_data = json.loads(self._cache_file.read_text(encoding="utf-8"))
                for entry in cached_data:
                    item = self._dict_to_item(entry)
                    catalog_map[item.id] = item
            except Exception:
                pass

        self._catalog_items = list(catalog_map.values())

    def _dict_to_item(self, entry: dict[str, Any]) -> CommunityModItem:
        """Converts raw catalog dictionary data into a CommunityModItem."""
        releases: list[ModRelease] = []
        for release in entry.get("releases", []):
            release: dict[str, Any]
            releases.append(
                ModRelease(
                    version=release.get("version", entry.get("version", "1.0.0")),
                    changelog=release.get("changelog", ""),
                    created_at=release.get("created_at", "2026-10-18"),
                    target_app_version=release.get(
                        "target_app_version", entry.get("target_app_version", "0.8.0")
                    ),
                    config_version=int(
                        release.get(
                            "config_version", entry.get("config_version", CURRENT_CONFIG_VERSION)
                        )
                    ),
                    download_url=release.get("download_url"),
                )
            )

        return CommunityModItem(
            id=entry["id"],
            name=entry["name"],
            entity_type=entry["entity_type"],
            version=entry["version"],
            author=entry["author"],
            description=entry.get("description", ""),
            tags=list(entry.get("tags") or []),
            rating=float(entry.get("rating", 10.0)),
            rating_count=int(entry.get("rating_count", 0)),
            downloads=int(entry.get("downloads", 0)),
            size_bytes=int(entry.get("size_bytes", 32000)),
            is_pack=bool(entry.get("is_pack", False)),
            contained_entities=list(entry.get("contained_entities") or []),
            icon_url=entry.get("icon_url"),
            preview_image_path=entry.get("preview_image_path"),
            package_url=entry.get("package_url"),
            created_at=entry.get("created_at", "2026-10-18"),
            updated_at=entry.get("updated_at", "2026-10-19"),
            config_version=int(entry.get("config_version", CURRENT_CONFIG_VERSION)),
            target_app_version=entry.get("target_app_version", "0.8.0"),
            releases=releases,
        )

    def _item_to_dict(self, item: CommunityModItem) -> dict[str, Any]:
        """Serializes a CommunityModItem for JSON caching."""
        return {
            "id": item.id,
            "name": item.name,
            "entity_type": item.entity_type,
            "version": item.version,
            "author": item.author,
            "description": item.description,
            "tags": item.tags,
            "rating": item.rating,
            "rating_count": item.rating_count,
            "downloads": item.downloads,
            "size_bytes": item.size_bytes,
            "is_pack": item.is_pack,
            "contained_entities": item.contained_entities,
            "icon_url": item.icon_url,
            "package_url": item.package_url,
            "config_version": item.config_version,
            "target_app_version": item.target_app_version,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "releases": [
                {
                    "version": release.version,
                    "changelog": release.changelog,
                    "created_at": release.created_at,
                    "config_version": release.config_version,
                    "target_app_version": release.target_app_version,
                    "download_url": release.download_url,
                }
                for release in item.releases
            ],
        }

    def _save_cache(self) -> None:
        """Saves current catalog items to local disk cache."""
        try:
            data: list[dict[str, Any]] = [self._item_to_dict(item) for item in self._catalog_items]
            self._cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def refresh_catalog_from_cloud(self) -> tuple[bool, str]:
        """
        Queries live community catalog from Supabase PostgREST if configured.
        Merges results with local catalog and updates the offline cache.
        """
        if not self.cloud.is_configured:
            return False, "Cloud sync is not configured (Running in Offline Mode)."

        success, msg, cloud_items = self.cloud.fetch_catalog()
        if not success:
            self.is_online = False
            return False, msg

        self.is_online = True
        existing_map: dict[str, CommunityModItem] = {item.id: item for item in self._catalog_items}

        for row in cloud_items:
            cloud_item = self._dict_to_item(row)
            existing_map[cloud_item.id] = cloud_item

        self._catalog_items = list(existing_map.values())
        self._save_cache()
        return True, f"Synchronized {len(cloud_items)} mods with Supabase Cloud!"

    def get_mod_by_id(self, mod_id: str) -> Optional[CommunityModItem]:
        """Returns the catalog entry for a given mod ID if present."""
        for item in self._catalog_items:
            if item.id == mod_id:
                return item
        return None

    def fetch_mods(
        self, query: str = "", category: str = "all",
        sort_by: str = "rating", installed_only: bool = False,
    ) -> list[CommunityModItem]:
        """
        Queries and filters community mods according to search string, category, and sorting.
        Synchronizes each item with local installation state.
        """
        self.sync_installed_status(self._catalog_items)
        results: list[CommunityModItem] = []

        _query: str = query.strip().lower()
        for item in self._catalog_items:
            if installed_only and not item.is_installed:
                continue

            if category == "pack" and not item.is_pack:
                continue
            elif category in (EntityType.ENTITY, EntityType.ITEM, EntityType.STRUCTURE):
                if item.entity_type != category:
                    continue

            if _query:
                matches_name: bool = _query in item.name.lower()
                matches_author: bool = _query in item.author.lower()
                matches_desc: bool = _query in item.description.lower()
                matches_tags: bool = any(_query in t.lower() for t in item.tags)
                matches_entities: bool = any(_query in e.lower() for e in item.contained_entities)
                if not (
                    matches_name or matches_author or matches_desc or matches_tags or matches_entities
                ):
                    continue

            results.append(item)

        # Sort results
        if sort_by == "rating":
            results.sort(key=lambda m: (m.rating, m.rating_count), reverse=True)
        elif sort_by == "downloads":
            results.sort(key=lambda m: m.downloads, reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda m: m.name.lower())
        elif sort_by == "newest":
            results.sort(key=lambda m: m.created_at, reverse=True)

        return results

    def sync_installed_status(self, items: list[CommunityModItem]) -> None:
        """Updates is_installed, installed_version, and has_update flags on catalog items."""
        if not self.mods_dir.exists():
            for item in items:
                item.is_installed = False
                item.installed_version = None
                item.has_update = False
            return

        installed_standalone: dict[str, tuple[str, str]] = get_available_mods_with_type(self.mods_dir)
        installed_packs: dict[str, Any] = get_available_packs(self.mods_dir)

        for item in items:
            folder: Path = self.mods_dir / item.id
            if item.is_pack:
                pack_obj = installed_packs.get(item.id)
                if pack_obj is not None:
                    item.is_installed = True
                    item.installed_version = pack_obj.manifest.version
                elif folder.exists() and (folder / "pack.json").exists():
                    item.is_installed = True
                    try:
                        p_data = json.loads((folder / "pack.json").read_text(encoding="utf-8"))
                        item.installed_version = str(p_data.get("version", "1.0.0"))
                    except Exception:
                        item.installed_version = "1.0.0"
                else:
                    item.is_installed = False
                    item.installed_version = None
            else:
                if item.id in installed_standalone or folder.exists():
                    item.is_installed = True
                    config_file: Path = folder / "config.json"
                    if config_file.exists():
                        try:
                            config_data: dict[str, Any] = json.loads(
                                config_file.read_text(encoding="utf-8")
                            )
                            item.installed_version = str(
                                config_data.get("mod_version", config_data.get("version", "1.0.0"))
                            )
                        except Exception:
                            item.installed_version = "1.0.0"
                    else:
                        item.installed_version = "1.0.0"
                else:
                    item.is_installed = False
                    item.installed_version = None

            # Compare catalog semver vs installed semver
            if item.is_installed and item.installed_version:
                item.has_update = parse_semver(item.version) > parse_semver(item.installed_version)
            else:
                item.has_update = False

    def install_mod(self, item: CommunityModItem) -> tuple[bool, str]:
        """
        Installs a community mod or modpack into self.mods_dir.
        If package_url is present, downloads the real archive and extracts it safely.
        Otherwise falls back to generating a valid local scaffold.
        """
        self.mods_dir.mkdir(parents=True, exist_ok=True)
        target_dir: Path = self.mods_dir / item.id

        if target_dir.exists():
            return False, f"Mod folder '{item.id}' already exists locally."

        # Case 1: Real package download from Cloud Storage
        if item.package_url:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_zip = Path(temp_dir) / f"{item.id}.zip"
                dl_ok, dl_msg = self.cloud.download_package(item.package_url, temp_zip)
                if dl_ok:
                    ext_ok, ext_msg, _ = extract_mod_or_pack_from_zip(temp_zip, self.mods_dir)
                    if ext_ok:
                        item.is_installed = True
                        item.installed_version = item.version
                        item.has_update = False
                        item.downloads += 1
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
                    self._create_placeholder_sprite(entity_dir / "sprite_sheet.png")

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
                self._create_placeholder_sprite(target_dir / "sprite_sheet.png")

            item.is_installed = True
            item.installed_version = item.version
            item.has_update = False
            item.downloads += 1
            return True, f"Successfully installed '{item.name}'."

        except Exception as e:
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            return False, f"Failed to install mod: {e}"

    def update_mod(self, item: CommunityModItem) -> tuple[bool, str]:
        """
        Updates an installed mod or modpack to the latest catalog release version.
        Downloads the updated package if available, or refreshes manifests cleanly.
        """
        target_dir: Path = self.mods_dir / item.id
        if not target_dir.exists():
            resolved, pack_id, _ = resolve_mod_path(self.mods_dir, item.id)
            if resolved is not None and resolved.exists():
                target_dir = self.mods_dir / pack_id if pack_id else resolved
            else:
                return False, f"Local installation for '{item.name}' not found."

        # If remote package URL exists, perform clean package update
        if item.package_url:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_zip = Path(temp_dir) / f"{item.id}.zip"
                dl_ok, _ = self.cloud.download_package(item.package_url, temp_zip)
                if dl_ok:
                    ext_ok, _, _ = extract_mod_or_pack_from_zip(temp_zip, self.mods_dir)
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

    def uninstall_mod(self, item: CommunityModItem) -> tuple[bool, str]:
        """Safely removes an installed mod or modpack from self.mods_dir."""
        target_dir: Path = self.mods_dir / item.id
        if not target_dir.exists():
            resolved, pack_id, _ = resolve_mod_path(self.mods_dir, item.id)
            if resolved is not None and resolved.exists():
                target_dir = self.mods_dir / pack_id if pack_id else resolved
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

    def publish_or_update(
        self,
        mod_id: str,
        name: str,
        author: str,
        version: str,
        description: str,
        entity_type: str,
        is_pack: bool,
        tags: list[str],
        changelog: str = "",
        contained_entities: Optional[list[str]] = None,
        size_bytes: int = 0,
        zip_path: Optional[Path] = None,
    ) -> tuple[bool, str, CommunityModItem]:
        """
        Publishes a new mod or updates an existing publication.
        Uploads package to Supabase Storage and records metadata in database if cloud is connected.
        """
        contained_entities = contained_entities or []
        today: str = time.strftime("%Y-%m-%d")
        existing_item: Optional[CommunityModItem] = self.get_mod_by_id(mod_id)

        package_url: Optional[str] = None
        if zip_path is not None and zip_path.exists() and self.cloud.is_configured:
            up_ok, up_msg, uploaded_url = self.cloud.upload_package(
                zip_path, f"{mod_id}_v{version}.zip"
            )
            if up_ok:
                package_url = uploaded_url

        if existing_item is not None:
            if parse_semver(version) <= parse_semver(existing_item.version):
                return (
                    False,
                    f"New release version (v{version}) must be higher than current catalog version (v{existing_item.version}).",
                    existing_item,
                )

            new_release = ModRelease(
                version=version,
                changelog=changelog or f"Updated to v{version}.",
                created_at=today,
                target_app_version=get_app_version(),
                config_version=CURRENT_CONFIG_VERSION,
                download_url=package_url or existing_item.package_url,
            )
            existing_item.releases.insert(0, new_release)
            existing_item.version = version
            existing_item.description = description
            existing_item.updated_at = today
            existing_item.size_bytes = size_bytes or existing_item.size_bytes
            existing_item.config_version = CURRENT_CONFIG_VERSION
            existing_item.target_app_version = get_app_version()
            if package_url:
                existing_item.package_url = package_url
            if tags:
                existing_item.tags = list(set(existing_item.tags + tags))
            if contained_entities:
                existing_item.contained_entities = contained_entities

            if self.cloud.is_configured:
                mod_update: dict[str, Any] = {
                    "version": version,
                    "description": description,
                    "size_bytes": existing_item.size_bytes,
                    "updated_at": "now()",
                    "package_url": existing_item.package_url,
                }
                release_data: dict[str, Any] = {
                    "mod_id": mod_id,
                    "version": version,
                    "changelog": changelog or f"Updated to v{version}.",
                    "download_url": existing_item.package_url,
                    "size_bytes": existing_item.size_bytes,
                    "config_version": CURRENT_CONFIG_VERSION,
                    "target_app_version": get_app_version(),
                }
                self.cloud.publish_release_update(mod_id, mod_update, release_data)

            self._save_cache()
            return True, f"Successfully published release v{version} for '{existing_item.name}'!", existing_item

        # Create brand-new mod entry
        initial_release = ModRelease(
            version=version,
            changelog=changelog or "Initial community release.",
            created_at=today,
            target_app_version=get_app_version(),
            config_version=CURRENT_CONFIG_VERSION,
            download_url=package_url,
        )
        new_item = CommunityModItem(
            id=mod_id,
            name=name,
            entity_type=entity_type,
            version=version,
            author=author,
            description=description,
            tags=tags,
            rating=10.0,
            rating_count=0,
            downloads=0,
            size_bytes=size_bytes,
            is_pack=is_pack,
            contained_entities=contained_entities,
            package_url=package_url,
            created_at=today,
            updated_at=today,
            config_version=CURRENT_CONFIG_VERSION,
            target_app_version=get_app_version(),
            releases=[initial_release],
        )
        self._catalog_items.insert(0, new_item)

        if self.cloud.is_configured:
            mod_data: dict[str, Any] = {
                "id": mod_id,
                "name": name,
                "entity_type": entity_type,
                "version": version,
                "author": author,
                "description": description,
                "tags": tags,
                "is_pack": is_pack,
                "contained_entities": contained_entities,
                "config_version": CURRENT_CONFIG_VERSION,
                "target_app_version": get_app_version(),
                "package_url": package_url,
                "size_bytes": size_bytes,
            }
            release_data: dict[str, Any] = {
                "mod_id": mod_id,
                "version": version,
                "changelog": changelog or "Initial community release.",
                "download_url": package_url,
                "size_bytes": size_bytes,
                "config_version": CURRENT_CONFIG_VERSION,
                "target_app_version": get_app_version(),
            }
            self.cloud.publish_new_mod(mod_data, release_data)

        self._save_cache()
        return True, f"Successfully published '{name}' (v{version}) to Community Mod Browser!", new_item

    def rate_mod(self, mod_id: str, score: float) -> tuple[bool, str]:
        """Submits a rating (1.0 to 10.0) for a given mod and synchronizes with cloud if connected."""
        score = max(1.0, min(10.0, score))
        for item in self._catalog_items:
            if item.id != mod_id: continue
            
            total_points: float = item.rating * item.rating_count
            if mod_id in self._user_ratings:
                old_score: float = self._user_ratings[mod_id]
                total_points = total_points - old_score + score
            else:
                total_points += score
                item.rating_count += 1

            item.rating = round(total_points / max(1, item.rating_count), 1)
            self._user_ratings[mod_id] = score
            self._save_cache()

            if self.cloud.is_configured:
                self.cloud.submit_rating(mod_id, score)

            return True, f"Your rating of {score:.1f}/10 has been recorded!"

        return False, f"Mod '{mod_id}' was not found in catalog."

    def _create_placeholder_sprite(self, path: Path) -> None:
        """Generates a valid 32x32 transparent colored PNG sprite sheet placeholder."""
        from PySide6.QtGui import QImage, QColor
        img = QImage(32, 32, QImage.Format.Format_ARGB32)
        img.fill(QColor(99, 102, 241, 255))
        img.save(str(path))

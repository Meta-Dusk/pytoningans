"""
PyToNingans Mod Browser - Client and Data Provider
================================================
Handles catalog fetching, search filtering, download orchestration,
package caching, release updates, and rating submissions.
Integrates with Supabase Cloud REST and Storage backend with complete offline-first caching.
Delegates disk installation, scaffolding, and uninstallation to installer_service.
"""
from __future__ import annotations

import json, time
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from pytoningans.core.config_schema import CURRENT_CONFIG_VERSION
from pytoningans.core.constants import EntityType
from pytoningans.core.mod_manager import (
    get_available_mods_with_type, get_available_packs,
)
from pytoningans.utils.paths import get_app_version, get_settings_path
from .catalog_seed import DEFAULT_CATALOG_DATA
from .installer_service import (
    install_catalog_item, update_installed_mod, uninstall_installed_mod,
    create_placeholder_sprite,
)
from .models import CommunityModItem, ModRelease, parse_semver
from .supabase_client import SupabaseClient
from .auth import AuthManager

if TYPE_CHECKING:
    from pytoningans.core.mod_manager.modpack import ModPack
    from pytoningans.ui.mod_browser.auth import UserProfile

__all__ = ["ModBrowserClient", "DEFAULT_CATALOG_DATA"]


class ModBrowserClient:
    """Manages community mod browsing, catalog searching, package downloads, and local installations."""

    def __init__(self, mods_dir: Path) -> None:
        self.mods_dir: Path = mods_dir.resolve()
        self.cloud: SupabaseClient = SupabaseClient()
        self._cache_file: Path = get_settings_path().parent / "catalog_cache.json"
        self._user_ratings: dict[str, float] = {}
        self.is_online: bool = False
        self._load_local_catalog()

    def go_offline(self) -> None:
        """Switches client to offline mode and restores local catalog items."""
        self.is_online = False
        self._load_local_catalog()

    def _load_local_catalog(self) -> None:
        """Initializes catalog data from cached disk entries."""
        self._catalog_items = []
        catalog_map: dict[str, CommunityModItem] = {}

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

    def load_seed_catalog(self) -> int:
        """
        Debug feature: Injects demo/seed catalog items for offline testing.
        Returns the number of new seed items added.
        """
        existing_ids: set[str] = {item.id for item in self._catalog_items}
        added_count: int = 0
        for entry in DEFAULT_CATALOG_DATA:
            item: CommunityModItem = self._dict_to_item(entry)
            if item.id not in existing_ids:
                self._catalog_items.append(item)
                existing_ids.add(item.id)
                added_count += 1

        self._save_cache()
        return added_count

    def clear_catalog_cache(self) -> None:
        """
        Debug feature: Resets catalog cache to clean empty state.
        """
        self._catalog_items.clear()
        if self._cache_file.exists():
            try:
                self._cache_file.unlink()
            except Exception:
                pass

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
            author_id=entry.get("author_id"),
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
            author_badges=list(entry.get("author_badges") or []),
            github_username=entry.get("github_username"),
        )

    def _item_to_dict(self, item: CommunityModItem) -> dict[str, Any]:
        """Serializes a CommunityModItem for JSON caching."""
        return {
            "id": item.id,
            "name": item.name,
            "entity_type": item.entity_type,
            "version": item.version,
            "author": item.author,
            "author_id": item.author_id,
            "author_badges": item.author_badges,
            "github_username": item.github_username,
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

    def get_local_mod_items(self) -> list[CommunityModItem]:
        """
        Scans self.mods_dir for local standalone mods and modpacks that are not in the community catalog cache.
        Returns CommunityModItem instances with is_local_only=True so creators can inspect,
        track local changes, and publish online whenever they choose.
        """
        if not self.mods_dir.exists():
            return []

        catalog_ids: set[str] = {item.id for item in self._catalog_items}
        local_items: list[CommunityModItem] = []

        # Local Modpacks
        installed_packs: dict[str, ModPack] = get_available_packs(self.mods_dir)
        for pack_id, pack in installed_packs.items():
            if pack_id in catalog_ids:
                continue
            folder: Path = self.mods_dir / pack_id
            contained: list[str] = []
            if folder.exists():
                for sub_category in ("entities", "items", "structures"):
                    sub_category_dir: Path = folder / sub_category
                    if not sub_category_dir.is_dir(): continue
                    for child in sub_category_dir.iterdir():
                        if not child.is_dir() or child.name.startswith(("_", ".")): continue
                        config: Path = child / "config.json"
                        if config.exists():
                            try:
                                config_info: dict[str, Any] = json.loads(
                                    config.read_text(encoding="utf-8")
                                )
                                contained.append(config_info.get("name", child.name))
                            except Exception:
                                contained.append(child.name)
                        else:
                            contained.append(child.name)
            size: int = 0
            if folder.exists():
                try:
                    size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
                except Exception:
                    size = 32000

            author_val: str = pack.manifest.author or "LocalCreator"
            current_user: Optional[UserProfile] = AuthManager.get().current_user
            pack_author_id: Optional[str] = (
                current_user.id if current_user is not None and
                current_user.username == author_val else None
            )
            pack_badges: list[str] = (
                list(current_user.badges) if current_user is not None and
                current_user.username == author_val else []
            )
            pack_gh: Optional[str] = (
                current_user.github_username if current_user is not None and
                current_user.username == author_val else None
            )

            local_items.append(
                CommunityModItem(
                    id=pack_id,
                    name=pack.name,
                    entity_type="pack",
                    version=pack.manifest.version or "1.0.0",
                    author=author_val,
                    author_id=pack_author_id,
                    author_badges=pack_badges,
                    github_username=pack_gh,
                    description=(
                        pack.manifest.description or
                        f"Locally authored modpack with {len(contained)} content items."
                    ),
                    tags=["local", "pack"] + getattr(pack.manifest, "tags", []),
                    rating=10.0,
                    rating_count=0,
                    downloads=0,
                    size_bytes=size,
                    is_pack=True,
                    contained_entities=contained,
                    is_installed=True,
                    installed_version=pack.manifest.version or "1.0.0",
                    is_local_only=True,
                )
            )

        # Local Standalone Mods
        installed_standalone: dict[str, tuple[str, str]] = get_available_mods_with_type(self.mods_dir)
        for mod_id, (name, entity_type) in installed_standalone.items():
            if ":" in mod_id or mod_id in catalog_ids:
                continue
            _folder: Path = self.mods_dir / mod_id
            if not _folder.is_dir():
                continue
            config_file: Path = _folder / "config.json"
            ver: str = "1.0.0"
            author: str = "LocalCreator"
            tags: list[str] = ["local"]
            if config_file.exists():
                try:
                    config_data = json.loads(config_file.read_text(encoding="utf-8"))
                    ver = str(config_data.get("version", config_data.get("mod_version", "1.0.0")))
                    author = str(config_data.get("author", author))
                    if "tags" in config_data and isinstance(config_data["tags"], list):
                        tags = list(set(tags + config_data["tags"]))
                except Exception:
                    pass

            size: int = 0
            try:
                size = sum(f.stat().st_size for f in _folder.rglob("*") if f.is_file())
            except Exception:
                size = 16000

            current_user: Optional[UserProfile] = AuthManager.get().current_user
            mod_author_id: Optional[str] = (
                current_user.id if current_user is not None and
                current_user.username == author else None
            )
            mod_badges: list[str] = (
                list(current_user.badges) if current_user is not None and
                current_user.username == author else []
            )
            mod_gh: Optional[str] = (
                current_user.github_username if current_user is not None and
                current_user.username == author else None
            )

            local_items.append(
                CommunityModItem(
                    id=mod_id,
                    name=name,
                    entity_type=entity_type,
                    version=ver,
                    author=author,
                    author_id=mod_author_id,
                    author_badges=mod_badges,
                    github_username=mod_gh,
                    description=f"Locally authored {entity_type} mod.",
                    tags=tags,
                    rating=10.0,
                    rating_count=0,
                    downloads=0,
                    size_bytes=size,
                    is_pack=False,
                    is_installed=True,
                    installed_version=ver,
                    is_local_only=True,
                )
            )

        return local_items

    def fetch_mods(
        self, query: str = "", category: str = "all",
        sort_by: str = "rating", installed_only: bool = False,
    ) -> list[CommunityModItem]:
        """
        Queries and filters community mods according to search string, category, and sorting.
        Synchronizes each item with local installation state and surfaces local creations.
        """
        self.sync_installed_status(self._catalog_items)
        local_pool: list[CommunityModItem] = self.get_local_mod_items()
        all_pool: list[CommunityModItem] = list(self._catalog_items) + local_pool

        results: list[CommunityModItem] = []

        _query: str = query.strip().lower()
        for item in all_pool:
            if installed_only and not item.is_installed:
                continue

            if category == "local":
                if not item.is_local_only:
                    continue
            elif category == "pack" and not item.is_pack:
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
        Delegates package extraction and local scaffolding to installer_service.
        """
        return install_catalog_item(item, self.mods_dir, self.cloud)

    def update_mod(self, item: CommunityModItem) -> tuple[bool, str]:
        """
        Updates an installed mod or modpack to the latest catalog release version.
        Delegates package extraction and manifest updating to installer_service.
        """
        return update_installed_mod(item, self.mods_dir, self.cloud)

    def uninstall_mod(self, item: CommunityModItem) -> tuple[bool, str]:
        """Safely removes an installed mod or modpack from self.mods_dir."""
        return uninstall_installed_mod(item, self.mods_dir)

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
            print(f"[publish_or_update] Upload Message:\n{up_msg}")
            if up_ok:
                package_url = uploaded_url

        if existing_item is not None:
            if parse_semver(version) <= parse_semver(existing_item.version):
                msg: str = (
                    f"New release version (v{version}) must be higher than current "
                    f"catalog version (v{existing_item.version})."
                )
                return False, msg, existing_item,

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
        current_user: Optional[UserProfile] = AuthManager.get().current_user
        author_id: Optional[str] = (
            current_user.id if current_user is not None and
            current_user.username == author else None
        )
        author_badges: list[str] = (
            list(current_user.badges) if current_user is not None and
            current_user.username == author else []
        )
        author_gh: Optional[str] = (
            current_user.github_username if current_user is not None and
            current_user.username == author else None
        )

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
            author_id=author_id,
            author_badges=author_badges,
            github_username=author_gh,
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
                "author_id": author_id,
                "author_badges": author_badges,
                "github_username": author_gh,
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
        create_placeholder_sprite(path)

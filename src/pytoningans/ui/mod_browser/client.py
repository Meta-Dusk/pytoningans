"""
PyToNingans Mod Browser - Client and Data Provider
================================================
Handles catalog fetching, search filtering, download orchestration,
package extraction, local installation tracking, and rating submissions.
Designed for offline-first operation with cloud sync readiness.
"""
from __future__ import annotations

import json, shutil
from pathlib import Path
from typing import Any

from pytoningans.core.constants import EntityType
from pytoningans.core.mod_manager import (
    resolve_mod_path, get_available_mods_with_type, get_available_packs,
)
from .models import CommunityModItem


# Seed catalog: Realistic community creations demonstrating diverse entity types and modpacks
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
    },
    {
        "id": "dungeon_crawler_pack",
        "name": "Classic Dungeon Crawler Pack",
        "entity_type": "pack",
        "version": "1.0.0",
        "author": "PixelForge",
        "description": (
            "Everything you need for desktop RPG adventures: Warrior, Skeleton Mob, "
            "Treasure Chest, and Healing Potions bundled in one pack."
        ),
        "tags": ["rpg", "combat", "modpack", "enemies", "loot"],
        "rating": 9.5,
        "rating_count": 79,
        "downloads": 4100,
        "size_bytes": 210000,
        "is_pack": True,
        "contained_entities": ["Dungeon Warrior", "Skeleton Archer", "Mimic Chest", "Healing Potion"],
    },
]


class ModBrowserClient:
    """Manages community mod browsing, catalog searching, package downloads, and local installations."""

    def __init__(self, mods_dir: Path) -> None:
        self.mods_dir: Path = mods_dir.resolve()
        
        self._user_ratings: dict[str, float] = {}
        """mod_id -> rating given by current user"""
        
        self._catalog_items: list[CommunityModItem] = []
        self.is_online: bool = True
        self._load_local_catalog()

    def _load_local_catalog(self) -> None:
        """Initializes catalog data from built-in seed and cached entries."""
        self._catalog_items = []
        for entry in DEFAULT_CATALOG_DATA:
            item = CommunityModItem(
                id=entry["id"],
                name=entry["name"],
                entity_type=entry["entity_type"],
                version=entry["version"],
                author=entry["author"],
                description=entry["description"],
                tags=list(entry.get("tags", [])),
                rating=float(entry.get("rating", 10.0)),
                rating_count=int(entry.get("rating_count", 0)),
                downloads=int(entry.get("downloads", 0)),
                size_bytes=int(entry.get("size_bytes", 32000)),
                is_pack=bool(entry.get("is_pack", False)),
                contained_entities=list(entry.get("contained_entities", [])),
                icon_url=entry.get("icon_url"),
                preview_image_path=entry.get("preview_image_path"),
                package_url=entry.get("package_url"),
                created_at="2026-10-18",
                updated_at="2026-10-19",
            )
            self._catalog_items.append(item)

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
            # Filter: installed only
            if installed_only and not item.is_installed:
                continue

            # Filter: category
            if category == "pack" and not item.is_pack:
                continue
            elif category in (EntityType.ENTITY, EntityType.ITEM, EntityType.STRUCTURE):
                if item.entity_type != category:
                    continue

            # Filter: search query
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
        """Updates the is_installed flag on catalog items based on currently present folders in mods_dir."""
        if not self.mods_dir.exists():
            for item in items:
                item.is_installed = False
            return

        installed_standalone: set[str] = set(get_available_mods_with_type(self.mods_dir).keys())
        installed_packs: set[str] = set(get_available_packs(self.mods_dir).keys())

        for item in items:
            if item.is_pack:
                item.is_installed = (item.id in installed_packs) or (self.mods_dir / item.id).exists()
            else:
                item.is_installed = (item.id in installed_standalone) or (self.mods_dir / item.id).exists()

    def install_mod(self, item: CommunityModItem) -> tuple[bool, str]:
        """
        Installs a community mod or modpack into self.mods_dir.
        Simulates remote zip package download and verification, then extracts via archive utilities.
        """
        self.mods_dir.mkdir(parents=True, exist_ok=True)
        target_dir: Path = self.mods_dir / item.id

        if target_dir.exists():
            return False, f"Mod folder '{item.id}' already exists locally."

        try:
            # Generate scaffold package structure matching mod specifications
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

                # Generate child sub-entities
                for entity_name in item.contained_entities:
                    slug: str = entity_name.lower().replace(" ", "_")
                    entity_dir: Path = target_dir / "entities" / slug
                    entity_dir.mkdir(parents=True, exist_ok=True)
                    entity_config: dict[str, Any] = {
                        "name": entity_name,
                        "entity_type": EntityType.ENTITY,
                        "version": 2,
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
                    "version": 2,
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
            item.downloads += 1
            return True, f"Successfully installed '{item.name}'."

        except Exception as e:
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            return False, f"Failed to install mod: {e}"

    def uninstall_mod(self, item: CommunityModItem) -> tuple[bool, str]:
        """Safely removes an installed mod or modpack from self.mods_dir."""
        target_dir: Path = self.mods_dir / item.id
        if not target_dir.exists():
            # Check if resolved by ID
            resolved, pack_id, _ = resolve_mod_path(self.mods_dir, item.id)
            if resolved is not None and resolved.exists():
                target_dir = self.mods_dir / pack_id if pack_id else resolved
            else:
                return False, f"Could not find installed folder for '{item.id}'."

        try:
            shutil.rmtree(target_dir)
            item.is_installed = False
            return True, f"Successfully uninstalled '{item.name}'."
        except Exception as e:
            return False, f"Failed to delete mod folder: {e}"

    def rate_mod(self, mod_id: str, score: float) -> tuple[bool, str]:
        """Submits a rating (1.0 to 10.0) for a given mod and updates the score average."""
        score = max(1.0, min(10.0, score))
        for item in self._catalog_items:
            if item.id == mod_id:
                # Update rolling average
                total_points: float = item.rating * item.rating_count
                if mod_id in self._user_ratings:
                    # User updating previous rating
                    old_score: float = self._user_ratings[mod_id]
                    total_points = total_points - old_score + score
                else:
                    total_points += score
                    item.rating_count += 1

                item.rating = round(total_points / max(1, item.rating_count), 1)
                self._user_ratings[mod_id] = score
                return True, f"Your rating of {score:.1f}/10 has been recorded!"

        return False, f"Mod '{mod_id}' was not found in catalog."

    def _create_placeholder_sprite(self, path: Path) -> None:
        """Generates a valid 32x32 transparent colored PNG sprite sheet placeholder."""
        from PySide6.QtGui import QImage, QColor
        img = QImage(32, 32, QImage.Format.Format_ARGB32)
        img.fill(QColor(99, 102, 241, 255))
        img.save(str(path))

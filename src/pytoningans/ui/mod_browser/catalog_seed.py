"""
PyToNingans Mod Browser - Seed Catalog Data
===========================================
Default offline-accessible community mod and modpack definitions.
Provides rich demonstration data showcasing diverse entity types,
modpacks, changelogs, and version metadata.
"""
from __future__ import annotations

from typing import Any

from pytoningans.core.config_schema import CURRENT_CONFIG_VERSION
from pytoningans.core.constants import EntityType

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


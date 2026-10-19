"""
PyToNingans Mod Browser - Data Models
=====================================
Defines metadata schemas for community mods, modpacks, reviews, and ratings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CommunityModItem:
    """Represents a community mod or modpack available in the Mod Browser."""
    id: str
    name: str
    entity_type: str  # "entity", "structure", "item", "pack"
    version: str
    author: str
    description: str
    tags: list[str] = field(default_factory=list)
    rating: float = 10.0  # Rating score from 1.0 to 10.0
    rating_count: int = 0
    downloads: int = 0
    size_bytes: int = 0
    is_pack: bool = False
    contained_entities: list[str] = field(default_factory=list)
    icon_url: Optional[str] = None
    preview_image_path: Optional[str] = None
    package_url: Optional[str] = None
    is_installed: bool = False
    installed_version: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    @property
    def formatted_size(self) -> str:
        """Returns human-readable size string (e.g. 1.2 MB)."""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        else:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"

    @property
    def formatted_rating(self) -> str:
        """Returns a formatted rating string (e.g. '★ 9.5/10 (42)')."""
        if self.rating_count == 0:
            return "★ New (No ratings)"
        return f"★ {self.rating:.1f}/10 ({self.rating_count})"


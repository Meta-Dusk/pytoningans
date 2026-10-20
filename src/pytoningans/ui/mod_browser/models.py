"""
PyToNingans Mod Browser - Data Models
=====================================
Defines metadata schemas for community mods, modpacks, reviews, ratings, and release versioning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pytoningans.core.config_schema import CURRENT_CONFIG_VERSION
from pytoningans.utils.paths import get_app_version


def parse_semver(ver: str) -> tuple[int, ...]:
    """
    Parses a semantic version string (e.g. '1.2.0' or 'v0.8.0-alpha')
    into an integer tuple for comparison.
    """
    try:
        clean: str = ver.strip().lstrip("v").split("-")[0]
        parts: list[int] = [int(p) for p in clean.split(".") if p.isdigit()]
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])
    except Exception:
        return (0, 0, 0)


@dataclass
class ModRelease:
    """Represents a specific release version / git-like tag of a mod or modpack."""
    version: str
    changelog: str
    created_at: str
    target_app_version: str = "0.8.0"
    config_version: int = CURRENT_CONFIG_VERSION
    download_url: Optional[str] = None
    package_hash: Optional[str] = None


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
    config_version: int = CURRENT_CONFIG_VERSION
    target_app_version: str = "0.8.0"
    releases: list[ModRelease] = field(default_factory=list)
    has_update: bool = False
    is_local_only: bool = False

    @property
    def semver(self) -> tuple[int, ...]:
        """Parsed semver tuple of the catalog version."""
        return parse_semver(self.version)

    @property
    def installed_semver(self) -> tuple[int, ...]:
        """Parsed semver tuple of the locally installed version."""
        return parse_semver(self.installed_version or "0.0.0")

    @property
    def is_outdated(self) -> bool:
        """
        Determines if this mod targets an outdated config schema or an older game version.
        """
        if self.config_version < CURRENT_CONFIG_VERSION:
            return True
        if parse_semver(self.target_app_version) < parse_semver(get_app_version()):
            return True
        return False

    @property
    def outdated_reasons(self) -> list[str]:
        """Returns explanations for why this mod is flagged as outdated."""
        reasons: list[str] = []
        if self.config_version < CURRENT_CONFIG_VERSION:
            reasons.append(
                f"Uses older config schema v{self.config_version} "
                f"(Current engine is v{CURRENT_CONFIG_VERSION})"
            )
        current_version: str = get_app_version()
        if parse_semver(self.target_app_version) < parse_semver(current_version):
            reasons.append(
                f"Built for game v{self.target_app_version} (Current is v{current_version})"
            )
        return reasons

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

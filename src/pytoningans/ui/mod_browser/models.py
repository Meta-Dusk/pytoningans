"""
PyToNingans Mod Browser - Data Models
=====================================
Defines metadata schemas for community mods, modpacks, reviews, ratings, and release versioning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any

from pytoningans.core.config_schema import CURRENT_CONFIG_VERSION
from pytoningans.core.constants import EntityType, VerificationStatus
from pytoningans.core.roles import get_github_for_creator, is_developer_account
from pytoningans.utils.paths import get_app_version, _DEFAULT_APP_VERSION
from pytoningans.utils.format import formatted_size


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


@dataclass(kw_only=True, slots=True, frozen=True)
class ModRelease:
    """
    Represents a specific release version / git-like tag of a mod or modpack.
    """
    version: str
    changelog: str
    created_at: str
    target_app_version: str = _DEFAULT_APP_VERSION
    config_version: int = CURRENT_CONFIG_VERSION
    download_url: Optional[str] = None
    package_hash: Optional[str] = None
    
    def to_dict_cloud(
        self, *, mod_id: str, size_bytes: int
    ) -> dict[str, Any]:
        """Serialize for JSON cloud payload."""
        return {
            "mod_id": mod_id,
            "version": self.version,
            "changelog": self.changelog,
            "download_url": self.download_url,
            "size_bytes": size_bytes,
            "config_version": self.config_version,
            "target_app_version": self.target_app_version,
            "created_at": self.created_at,
        }
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON Caching."""
        return {
            "version": self.version,
            "changelog": self.changelog,
            "created_at": self.created_at,
            "target_app_version": self.target_app_version,
            "config_version": self.config_version,
            "download_url": self.download_url,
            "package_hash": self.package_hash
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModRelease:
        return ModRelease(
            version=data.get("version", "1.0.0"),
            changelog=data.get("changelog", ""),
            created_at=data.get("created_at", "2026-10-18"),
            target_app_version=data.get("target_app_version", _DEFAULT_APP_VERSION),
            config_version=data.get("config_version", CURRENT_CONFIG_VERSION),
            download_url=data.get("download_url"),
            package_hash=data.get("package_hash")
        )


@dataclass(kw_only=True, slots=True)
class CommunityModItem:
    """Represents a community mod or modpack available in the Mod Browser."""
    id: str
    name: str
    entity_type: EntityType | str
    version: str
    author: str
    author_id: Optional[str] = None
    author_badges: list[str] = field(default_factory=list)
    github_username: Optional[str] = None
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
    target_app_version: str = _DEFAULT_APP_VERSION
    releases: list[ModRelease] = field(default_factory=list)
    has_update: bool = False
    is_local_only: bool = False
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None

    @property
    def is_developer(self) -> bool:
        """Determines if the author is recognized as an official core developer."""
        return is_developer_account(user_id=self.author_id or "", handle=self.author)

    @property
    def author_github(self) -> Optional[str]:
        """Returns GitHub handle for the author if linked or developer."""
        if self.github_username:
            return self.github_username.strip().lstrip("@")
        return get_github_for_creator(user_id=self.author_id or "", handle=self.author)

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
        return formatted_size(self.size_bytes)

    @property
    def formatted_rating(self) -> str:
        """Returns a formatted rating string (e.g. '★ 9.5/10.0 (42)')."""
        if self.rating_count == 0:
            return "★ New (No ratings)"
        return f"★ {self.rating:.1f}/10.0 ({self.rating_count})"
    
    def to_dict_cloud(self) -> dict[str, Any]:
        """Serialize for JSON cloud payload."""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "version": self.version,
            "author": self.author,
            "author_id": self.author_id,
            "author_badges": self.author_badges,
            "github_username": self.github_username,
            "description": self.description,
            "tags": self.tags,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "is_pack": self.is_pack,
            "contained_entities": self.contained_entities,
            "config_version": self.config_version,
            "target_app_version": self.target_app_version,
            "package_url": self.package_url,
            "icon_url": self.icon_url,
            "preview_image_path": self.preview_image_path,
            "downloads": self.downloads,
            "size_bytes": self.size_bytes,
            "verification_status": self.verification_status.value,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON caching."""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "version": self.version,
            "author": self.author,
            "author_id": self.author_id,
            "author_badges": self.author_badges,
            "github_username": self.github_username,
            "description": self.description,
            "tags": self.tags,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "downloads": self.downloads,
            "size_bytes": self.size_bytes,
            "is_pack": self.is_pack,
            "contained_entities": self.contained_entities,
            "icon_url": self.icon_url,
            "preview_image_path": self.preview_image_path,
            "package_url": self.package_url,
            "is_installed": self.is_installed,
            "installed_version": self.installed_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "config_version": self.config_version,
            "target_app_version": self.target_app_version,
            "releases": [
                {
                    "version": release.version,
                    "changelog": release.changelog,
                    "created_at": release.created_at,
                    "config_version": release.config_version,
                    "target_app_version": release.target_app_version,
                    "download_url": release.download_url,
                    "package_hash": release.package_hash
                }
                for release in self.releases
            ],
            "has_update": self.has_update,
            "is_local_only": self.is_local_only,
            "verification_status": self.verification_status.value,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommunityModItem:
        """Converts raw catalog dictionary data into a CommunityModItem."""
        releases: list[ModRelease] = []
        for release in data.get("releases", []):
            release: dict[str, Any]
            releases.append(ModRelease.from_dict(release))

        return CommunityModItem(
            id=data["id"],
            name=data["name"],
            entity_type=data["entity_type"],
            version=data["version"],
            author=data["author"],
            author_id=data.get("author_id"),
            author_badges=list(data.get("author_badges") or []),
            github_username=data.get("github_username"),
            description=data.get("description", ""),
            tags=list(data.get("tags") or []),
            rating=float(data.get("rating", 10.0)),
            rating_count=int(data.get("rating_count", 0)),
            downloads=int(data.get("downloads", 0)),
            size_bytes=int(data.get("size_bytes", 32000)),
            is_pack=bool(data.get("is_pack", False)),
            contained_entities=list(data.get("contained_entities") or []),
            icon_url=data.get("icon_url"),
            preview_image_path=data.get("preview_image_path"),
            package_url=data.get("package_url"),
            is_installed=data.get("is_installed", False),
            installed_version=data.get("installed_version"),
            created_at=data.get("created_at", "2026-10-18"),
            updated_at=data.get("updated_at", "2026-10-19"),
            config_version=int(data.get("config_version", CURRENT_CONFIG_VERSION)),
            target_app_version=data.get("target_app_version", _DEFAULT_APP_VERSION),
            releases=releases,
            verification_status=data.get("verification_status", VerificationStatus.PENDING.value),
            verified_by=data.get("verified_by"),
            verified_at=data.get("verified_at"),
        )

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from pytoningans.core.mod_manager import ModManager


class EntityTagMixin:
    """Encapsulates runtime tag management for entities."""

    tags: set[str]
    mod_manager: Optional[ModManager]

    def _init_tags(self) -> None:
        self.tags = (
            set(self.mod_manager.tags) if self.mod_manager is not None else set()
        )

    def has_tag(self, tag: str) -> bool:
        """Returns True if the entity has the specified tag (case-insensitive)."""
        return tag.lower().strip() in self.tags

    def has_all_tags(self, *tags: str) -> bool:
        """Returns True if the entity contains every specified tag."""
        return all(t.lower().strip() in self.tags for t in tags)

    def has_any_tag(self, *tags: str) -> bool:
        """Returns True if the entity contains at least one of the specified tags."""
        return any(t.lower().strip() in self.tags for t in tags)

    def add_tag(self, tag: str) -> None:
        """Dynamically adds a tag to the entity at runtime."""
        clean_tag: str = tag.lower().strip()
        if clean_tag:
            self.tags.add(clean_tag)

    def remove_tag(self, tag: str) -> None:
        """Removes a tag from the entity at runtime."""
        self.tags.discard(tag.lower().strip())


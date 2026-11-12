"""
PyToNingans Modding API - Modpack Base Classes and Protocols
==========================================================
Enables grouping entities, items, and structures into cohesive modpacks
with shared runtime state, inter-entity communication, and custom context menus.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional
from dataclasses import asdict, dataclass, field

if TYPE_CHECKING:
    from .protocol import IBaseEntity


@dataclass(slots=True, kw_only=True)
class PackMenuAction:
    """Action button added to an entity's desktop context menu by its parent modpack."""
    label: str
    callback: Callable[[], None]
    tooltip: str = ""


@dataclass(slots=True, kw_only=True)
class ModPackConfig:
    id: str
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    shared_script: str = "pack.py"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseModPack:
    """
    Base class for shared modpack logic in `pack.py`.
    Provides shared state, lifecycle hooks, and context menu actions for all child entities.
    """

    def __init__(self, pack_info: Optional[ModPackConfig] = None) -> None:
        self.pack_info: Optional[ModPackConfig] = pack_info
        self.shared_state: dict[str, Any] = {}

    def on_pack_loaded(self) -> None:
        """Called when the modpack manifest and controller are loaded into memory."""
        pass

    def on_entity_spawned(self, entity: IBaseEntity) -> None:
        """Called whenever any child entity belonging to this pack is spawned on screen."""
        pass

    def get_context_menu_actions(self, entity: IBaseEntity) -> list[PackMenuAction]:
        """
        Returns custom context menu action buttons to display when right-clicking
        an entity belonging to this pack.
        """
        return []

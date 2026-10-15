from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtWidgets import QVBoxLayout, QPushButton

from .living import build_living_actions
from .item import build_item_actions
from .structure import build_structure_actions

if TYPE_CHECKING:
    from ..window import EntityContextMenu


def populate_actions(menu: EntityContextMenu, layout: QVBoxLayout) -> None:
    """Dispatches action building to the appropriate sub-module based on the entity's type."""
    from pytoningans.core.entity.living_entity import Entity
    from pytoningans.core.entity.base_item import BaseItem
    from pytoningans.core.entity.base_structure import BaseStructure

    if isinstance(menu.entity, Entity):
        build_living_actions(menu, layout, menu.entity)
    elif isinstance(menu.entity, BaseItem):
        build_item_actions(menu, layout, menu.entity)
    elif isinstance(menu.entity, BaseStructure):
        build_structure_actions(menu, layout, menu.entity)
    else:
        if menu.entity is not None:
            close_btn = QPushButton("Close Object")
            close_btn.setObjectName("DangerBtn")
            close_btn.clicked.connect(lambda: menu.execute_and_close(menu.entity.destroy if menu.entity else None))
            layout.addWidget(close_btn)

    layout.addStretch()


__all__ = [
    "build_living_actions",
    "build_item_actions",
    "build_structure_actions",
    "populate_actions",
]


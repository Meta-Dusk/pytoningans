from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from PySide6.QtGui import QPixmap, QColor

from pytoningans.core.entity.base_entity import BaseStructure

if TYPE_CHECKING:
    from pytoningans.core.world import WorldOverlay
    from pytoningans.core.mod_manager import ModManager


class TravelPortal(BaseStructure):
    """Engine-level portal used for multi-monitor linking."""
    def __init__(
        self, x: float, y: float, 
        world: WorldOverlay, target_world: WorldOverlay,
        mod_manager: Optional[ModManager] = None
    ) -> None:
        super().__init__(x, y, mod_manager, world)
        self.teleport_comp = self.attach_teleportation(target_world)
        
        # Fallback colored box if no custom sprite sheet is present
        if not mod_manager or not mod_manager._global_sheet:
            pix = QPixmap(60, 120)
            pix.fill(QColor(138, 43, 226, 200))
            self.setPixmap(pix)

    @property
    def linked_portal(self) -> Optional[BaseStructure]:
        return self.teleport_comp.linked_portal

    @linked_portal.setter
    def linked_portal(self, portal: Optional[BaseStructure]) -> None:
        self.teleport_comp.linked_portal = portal

    @property
    def exit_offset_x(self) -> float:
        return self.teleport_comp.exit_offset_x

    @exit_offset_x.setter
    def exit_offset_x(self, val: float) -> None:
        self.teleport_comp.exit_offset_x = val

    @property
    def exit_offset_y(self) -> float:
        return self.teleport_comp.exit_offset_y

    @exit_offset_y.setter
    def exit_offset_y(self, val: float) -> None:
        self.teleport_comp.exit_offset_y = val

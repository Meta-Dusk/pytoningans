from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt, QPoint, QPointF
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QMainWindow, QGraphicsView, QGraphicsScene

from pytoningans.core.entity.indicators.damage_number import DamageNumberItem
from pytoningans.core.vision_worker import HTCLIENT, HTTRANSPARENT

if TYPE_CHECKING:
    from pytoningans.core.entity_manager import EntityManager
    from pytoningans.core.entity.base_entity import BaseEntity
    from pytoningans.core.entity.base_structure import BaseStructure
    from pytoningans.core.entity.base_item import BaseItem
    from pytoningans.core.entity.living_entity import Entity
    

class WorldOverlay(QMainWindow):
    """The transparent, fullscreen monitor overlay that acts as a **World**."""
    def __init__(self, screen: QScreen, manager: EntityManager) -> None:
        super().__init__()
        self.manager = manager
        self.target_screen = screen
        
        # The World now manages multiple entity types natively
        self.active_entities: list[Entity] = []
        self.active_structures: list[BaseStructure] = []
        self.active_items: list[BaseItem] = []
        self.active_damage_numbers: list[DamageNumberItem] = []
        
        flags: Qt.WindowType = (
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.scene = QGraphicsScene(self)
        
        screen_geom: QRect = self.target_screen.availableGeometry()
        self.scene.setSceneRect(0, 0, screen_geom.width(), screen_geom.height())
        
        self.view = QGraphicsView(self.scene, self)
        self.view.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.setCentralWidget(self.view)
        self.setGeometry(screen_geom)
        
    def nativeEvent(self, eventType, message):
        msg: wintypes.MSG = wintypes.MSG.from_address(message.__int__())
        if msg.message == 0x0084: # WM_NCHITTEST
            x: int = ctypes.c_short(msg.lParam & 0xFFFF).value
            y: int = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
            
            local_pos: QPoint = self.view.mapFromGlobal(QPoint(x, y))
            scene_pos: QPointF = self.view.mapToScene(local_pos)
            
            if self.scene.itemAt(scene_pos, self.view.transform()):
                return True, HTCLIENT
                
            return True, HTTRANSPARENT
            
        return super().nativeEvent(eventType, message)

    def spawn_damage_number(
        self, amount: int, scene_pos: QPointF, is_heal: bool = False
    ) -> None:
        indicator = DamageNumberItem(amount, scene_pos, is_heal)
        self.scene.addItem(indicator)
        self.active_damage_numbers.append(indicator)

    def update_systems(self, dt: int) -> None:
        # Tick static/interactive structures first
        for struct in list(self.active_structures):
            struct.update_systems(dt)
            
        # Tick mobile entities
        centers: dict[BaseEntity, QPointF] = {
            entity: entity.sceneBoundingRect().center() for entity in self.active_entities
        }
        for entity in list(self.active_entities):
            entity.update_systems(dt, centers)

        # Tick items
        for item in list(self.active_items):
            item.update_systems(dt)

        # Tick floating combat numbers
        for num in list(self.active_damage_numbers):
            if not num.tick(dt): continue
            if num.scene():
                self.scene.removeItem(num)
            if num in self.active_damage_numbers:
                self.active_damage_numbers.remove(num)
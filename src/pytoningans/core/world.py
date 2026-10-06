import ctypes

from ctypes import wintypes
from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt, QPoint, QPointF
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QMainWindow, QGraphicsView, QGraphicsScene

if TYPE_CHECKING:
    from pytoningans.core.pet_manager import PetManager
    from pytoningans.core.pet.window import PetWindow
    from pytoningans.core.structure import BaseStructure

HTTRANSPARENT = -1
HTCLIENT = 1

class WorldOverlay(QMainWindow):
    """The transparent, fullscreen monitor overlay that acts as a 'World'."""
    def __init__(self, screen: QScreen, manager: PetManager) -> None:
        super().__init__()
        self.manager = manager
        self.target_screen = screen
        
        # The World now manages multiple entity types natively
        self.active_pets: list[PetWindow] = []
        self.active_structures: list[BaseStructure] = []
        
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

    def update_systems(self, dt: int) -> None:
        # Tick static/interactive structures first
        for struct in list(self.active_structures):
            struct.update_systems(dt)
            
        # Tick mobile pets
        centers: dict[PetWindow, QPointF] = {
            pet: pet.sceneBoundingRect().center() for pet in self.active_pets
        }
        for pet in list(self.active_pets):
            pet.update_systems(dt, centers)
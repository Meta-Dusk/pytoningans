import sys, ctypes, signal
from ctypes import wintypes

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PySide6.QtCore import QPointF, QRect, Qt, QPoint, QTimer, QElapsedTimer
from PySide6.QtGui import QPixmap, QColor, QKeyEvent
from PySide6.QtWidgets import QGraphicsSceneMouseEvent

HTTRANSPARENT = -1
HTCLIENT = 1

class Entity(QGraphicsPixmapItem):
    """A minimal test entity representing a pet."""
    def __init__(self, x: int, y: int):
        super().__init__()
        self.setPos(x, y)
        self.vx = 3
        self.vy = 3
        
        self.red_pix = QPixmap(100, 100)
        self.red_pix.fill(QColor("red"))
        
        self.green_pix = QPixmap(100, 100)
        self.green_pix.fill(QColor("green"))
        
        self.setPixmap(self.red_pix)
        
    def update_systems(self, dt: int, bounds_width: int, bounds_height: int) -> None:
        new_x: float = self.x() + self.vx * (dt / 16.0)
        new_y: float = self.y() + self.vy * (dt / 16.0)
        
        if new_x <= 0 or new_x + 100 >= bounds_width:
            self.vx *= -1
            new_x = max(0, min(new_x, bounds_width - 100))
            
        if new_y <= 0 or new_y + 100 >= bounds_height:
            self.vy *= -1
            new_y = max(0, min(new_y, bounds_height - 100))
            
        self.setPos(new_x, new_y)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setPixmap(self.green_pix)
            event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setPixmap(self.red_pix)
            event.accept()


class WorldOverlay(QMainWindow):
    """The transparent, fullscreen monitor overlay."""
    def __init__(self):
        super().__init__()
        
        flags: Qt.WindowType = (
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.scene = QGraphicsScene(self)
        screen_geom: QRect = self.screen().availableGeometry()
        self.scene.setSceneRect(0, 0, screen_geom.width(), screen_geom.height())
        
        self.view = QGraphicsView(self.scene, self)
        self.view.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setCentralWidget(self.view)
        
        self.entities: list[Entity] = []

    def spawn_entity(self, x: int, y: int) -> None:
        ent = Entity(x, y)
        self.scene.addItem(ent)
        self.entities.append(ent)

    def update_systems(self, dt: int) -> None:
        bounds: QRect = self.screen().availableGeometry()
        for ent in self.entities:
            ent.update_systems(dt, bounds.width(), bounds.height())

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

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Allow closing the test window quickly via the Escape key."""
        if event.key() == Qt.Key.Key_Escape:
            QApplication.quit()


class GameManager:
    """The central nervous system replacing PetManager."""
    def __init__(self):
        self.active_worlds: list[WorldOverlay] = []
        
        self.clock = QElapsedTimer()
        self.timer = QTimer()
        self.timer.timeout.connect(self._global_tick)
        
        primary_world = WorldOverlay()
        primary_world.showFullScreen()
        
        primary_world.spawn_entity(100, 100)
        primary_world.spawn_entity(400, 300)
        primary_world.spawn_entity(800, 600)
        
        self.active_worlds.append(primary_world)
        
        self.timer.start(16)
        self.clock.start()

    def _global_tick(self) -> None:
        dt: int = self.clock.restart()
        for world in self.active_worlds:
            world.update_systems(dt)


if __name__ == "__main__":
    # Ensure Python catches Ctrl+C in the terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    manager = GameManager()
    sys.exit(app.exec())
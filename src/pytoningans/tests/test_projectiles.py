from __future__ import annotations

import sys, ctypes, signal, random
from ctypes import wintypes
from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import (
    QApplication, QGraphicsItem, QMainWindow, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem
)
from PySide6.QtCore import Qt, QPoint, QTimer, QElapsedTimer
from PySide6.QtGui import QPixmap, QColor

if TYPE_CHECKING:
    from PySide6.QtCore import QByteArray, QPointF, QRect
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QGraphicsSceneMouseEvent


HTTRANSPARENT = -1
HTCLIENT = 1


class Projectile(QGraphicsPixmapItem):
    """Lightweight projectile optimized for single-window overlay rendering."""
    def __init__(
        self, x: float, y: float, vx: float, vy: float,
        pixmap: QPixmap, lifetime: float = 8.0
    ) -> None:
        super().__init__()
        self.setPixmap(pixmap)
        self.setPos(x, y)
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.time_alive = 0.0
        self.is_dead = False
        
        # Flag used by WorldOverlay nativeEvent to bypass click-testing
        self.passthrough_mouse = True
        
        # Disable C++ Qt mouse event processing
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setAcceptHoverEvents(False)

    def update_systems(self, dt_sec: float, bounds_w: float, bounds_h: float) -> None:
        if self.is_dead:
            return

        self.time_alive += dt_sec
        if self.time_alive >= self.lifetime:
            self.is_dead = True
            return

        new_x: float = self.x() + self.vx * dt_sec
        new_y: float = self.y() + self.vy * dt_sec

        # Bounce off screen borders
        if new_x <= 0 or new_x + self.pixmap().width() >= bounds_w:
            self.vx *= -1
            new_x = max(0, min(new_x, bounds_w - self.pixmap().width()))
            
        if new_y <= 0 or new_y + self.pixmap().height() >= bounds_h:
            self.vy *= -1
            new_y = max(0, min(new_y, bounds_h - self.pixmap().height()))

        self.setPos(new_x, new_y)


class Entity(QGraphicsPixmapItem):
    """An interactive companion entity that captures mouse clicks."""
    def __init__(self, x: int, y: int) -> None:
        super().__init__()
        self.setPos(x, y)
        self.vx: float = 150.0
        self.vy: float = 150.0
        self.passthrough_mouse: bool = False
        
        self.red_pix = QPixmap(80, 80)
        self.red_pix.fill(QColor("red"))
        
        self.green_pix = QPixmap(80, 80)
        self.green_pix.fill(QColor("green"))
        
        self.setPixmap(self.red_pix)
        
    def update_systems(
        self, dt_sec: float, bounds_w: float, bounds_h: float
    ) -> None:
        new_x: float = self.x() + self.vx * dt_sec
        new_y: float = self.y() + self.vy * dt_sec
        
        if new_x <= 0 or new_x + 80 >= bounds_w:
            self.vx *= -1
            new_x = max(0, min(new_x, bounds_w - 80))
            
        if new_y <= 0 or new_y + 80 >= bounds_h:
            self.vy *= -1
            new_y = max(0, min(new_y, bounds_h - 80))
            
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
    """Transparent, fullscreen monitor overlay using native Win32 hit-testing."""
    def __init__(self):
        super().__init__()
        
        flags = (
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
        
        # Optimize rendering pipeline for transparent overlay
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setCentralWidget(self.view)
        
        self.entities: list[Entity] = []
        self.projectiles: list[Projectile] = []

        # Shared 12x12 projectile pixmap
        self.proj_pixmap = QPixmap(12, 12)
        self.proj_pixmap.fill(QColor("cyan"))

    def spawn_entity(self, x: int, y: int) -> None:
        entity = Entity(x, y)
        self.scene.addItem(entity)
        self.entities.append(entity)

    def spawn_projectiles(self, count: int) -> None:
        geom: QRect = self.screen().availableGeometry()
        for _ in range(count):
            x: float = random.uniform(100, geom.width() - 100)
            y: float = random.uniform(100, geom.height() - 100)
            vx: float = random.uniform(-400, 400)
            vy: float = random.uniform(-400, 400)
            
            proj = Projectile(x, y, vx, vy, self.proj_pixmap)
            self.scene.addItem(proj)
            self.projectiles.append(proj)

    def update_systems(self, dt_sec: float) -> None:
        bounds: QRect = self.screen().availableGeometry()
        
        for ent in self.entities:
            ent.update_systems(dt_sec, bounds.width(), bounds.height())

        # Update and purge dead projectiles
        alive_projectiles: list[Projectile] = []
        for proj in self.projectiles:
            proj.update_systems(dt_sec, bounds.width(), bounds.height())
            if proj.is_dead:
                self.scene.removeItem(proj)
            else:
                alive_projectiles.append(proj)
                
        self.projectiles = alive_projectiles

    def nativeEvent(
        self, eventType: QByteArray | bytes | bytearray | memoryview[int],
        message: int
    ) -> object:
        msg: wintypes.MSG = wintypes.MSG.from_address(message.__int__())
        if msg.message == 0x0084:  # WM_NCHITTEST
            x: int = ctypes.c_short(msg.lParam and 0xFFFF).value
            y: int = ctypes.c_short((msg.lParam >> 16) and 0xFFFF).value
            
            local_pos: QPoint = self.view.mapFromGlobal(QPoint(x, y))
            scene_pos: QPointF = self.view.mapToScene(local_pos)
            
            hit_item: Optional[QGraphicsItem] = self.scene.itemAt(scene_pos, self.view.transform())
            
            # Key Fix: Only return HTCLIENT if the item under mouse is NOT a passthrough projectile
            if hit_item and not getattr(hit_item, "passthrough_mouse", False):
                return True, HTCLIENT
                
            return True, HTTRANSPARENT
            
        return super().nativeEvent(eventType, message)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            QApplication.quit()


class GameManager:
    def __init__(self):
        self.active_worlds: list[WorldOverlay] = []
        
        self.clock = QElapsedTimer()
        self.timer = QTimer()
        self.timer.timeout.connect(self._global_tick)
        
        self.fps_timer = QElapsedTimer()
        self.fps_timer.start()
        self.frame_count = 0
        
        primary_world = WorldOverlay()
        primary_world.showFullScreen()
        
        # Initial entities and burst of projectiles
        primary_world.spawn_entity(200, 200)
        primary_world.spawn_entity(600, 400)
        primary_world.spawn_projectiles(300)
        
        self.active_worlds.append(primary_world)
        
        self.timer.start(16)
        self.clock.start()

    def _global_tick(self) -> None:
        dt_ms: int = self.clock.restart()
        dt_sec: float = dt_ms / 1000.0
        
        for world in self.active_worlds:
            world.update_systems(dt_sec)

        # FPS and Object Count Logging
        self.frame_count += 1
        if self.fps_timer.elapsed() >= 1000:
            fps: int = self.frame_count
            total_proj: int = sum(len(w.projectiles) for w in self.active_worlds)
            print(f"[Overlay Benchmark] FPS: {fps} | Active Projectiles: {total_proj}")
            self.frame_count = 0
            self.fps_timer.restart()


def sigint_handler(*args):
    """Gracefully shuts down Qt and returns control to the terminal."""
    print("\n[GameManager] Terminating process via Ctrl+C...")
    QApplication.quit()
    sys.exit(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Attach custom SIGINT handler
    signal.signal(signal.SIGINT, sigint_handler)

    # Heartbeat timer: forces the Python interpreter to periodically run 
    # and process incoming OS signals like SIGINT while Qt's event loop is running
    signal_timer = QTimer()
    signal_timer.start(100)
    signal_timer.timeout.connect(lambda: None)

    manager = GameManager()
    sys.exit(app.exec())
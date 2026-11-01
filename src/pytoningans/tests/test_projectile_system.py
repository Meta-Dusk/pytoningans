from __future__ import annotations

import sys, ctypes, signal, random
from ctypes import wintypes
from typing import cast, TYPE_CHECKING

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PySide6.QtCore import QPointF, QRect, Qt, QPoint, QTimer, QElapsedTimer
from PySide6.QtGui import QPixmap, QColor

# Core Projectile System Imports
from pytoningans.core.projectile import Projectile
from pytoningans.core.projectile import ProjectileManager
from pytoningans.core.entity.living_entity import Entity

if TYPE_CHECKING:
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QGraphicsSceneMouseEvent


HTTRANSPARENT = -1
HTCLIENT = 1


class InteractiveEntity(QGraphicsPixmapItem):
    """Minimal test entity to verify mouse interaction alongside projectiles."""
    def __init__(self, x: float, y: float):
        super().__init__()
        self.setPos(x, y)
        self.vx: float = 120.0
        self.vy: float = 120.0
        self.passthrough_mouse: bool = False

        self.red_pix = QPixmap(80, 80)
        self.red_pix.fill(QColor("red"))

        self.green_pix = QPixmap(80, 80)
        self.green_pix.fill(QColor("green"))

        self.setPixmap(self.red_pix)

    def update_systems(self, dt_sec: float, bounds_w: float, bounds_h: float) -> None:
        new_x: float = self.x() + self.vx * dt_sec
        new_y: float = self.y() + self.vy * dt_sec

        if new_x <= 0 or new_x + 80 >= bounds_w:
            self.vx *= -1
            new_x = max(0.0, min(new_x, bounds_w - 80))

        if new_y <= 0 or new_y + 80 >= bounds_h:
            self.vy *= -1
            new_y = max(0.0, min(new_y, bounds_h - 80))

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
    """Transparent overlay integrating ProjectileManager."""
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
        screen_geom = self.screen().availableGeometry()
        self.scene.setSceneRect(0, 0, screen_geom.width(), screen_geom.height())

        self.view = QGraphicsView(self.scene, self)
        self.view.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setCentralWidget(self.view)

        # Entities & Projectile Manager
        self.entities: list[InteractiveEntity] = []
        self.projectile_manager = ProjectileManager(self.scene)

        # Shared Projectile Textures
        self.proj_pixmap = QPixmap(10, 10)
        self.proj_pixmap.fill(QColor("yellow"))

    def spawn_entity(self, x: float, y: float) -> None:
        ent = InteractiveEntity(x, y)
        self.scene.addItem(ent)
        self.entities.append(ent)

    def burst_projectiles(self, count: int = 50) -> None:
        geom = self.screen().availableGeometry()
        center_x = geom.width() / 2
        center_y = geom.height() / 2

        for _ in range(count):
            vel_x = random.uniform(-500, 500)
            vel_y = random.uniform(-500, 500)
            self.projectile_manager.spawn(
                pixmap=self.proj_pixmap,
                pos=QPointF(center_x, center_y),
                velocity=QPointF(vel_x, vel_y),
                gravity=150.0,  # Light downward gravity arc
                lifetime=6.0,
                passthrough_mouse=True,
            )

    def update_systems(self, dt_sec: float) -> None:
        bounds: QRect = self.screen().availableGeometry()

        # Update Companion Entities
        for ent in self.entities:
            ent.update_systems(dt_sec, bounds.width(), bounds.height())

        # Update Projectiles via Manager
        self.projectile_manager.update(
            dt_sec=dt_sec,
            bounds_w=bounds.width(),
            bounds_h=bounds.height(),
            active_entities=cast(list[Entity], self.entities),
        )

    def nativeEvent(self, eventType, message):
        msg = wintypes.MSG.from_address(message.__int__())
        if msg.message == 0x0084:  # WM_NCHITTEST
            x = ctypes.c_short(msg.lParam & 0xFFFF).value
            y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value

            local_pos = self.view.mapFromGlobal(QPoint(x, y))
            scene_pos = self.view.mapToScene(local_pos)

            hit_item = self.scene.itemAt(scene_pos, self.view.transform())

            # Only intercept mouse if hit item is NOT a passthrough projectile
            if hit_item and not getattr(hit_item, "passthrough_mouse", False):
                return True, HTCLIENT

            return True, HTTRANSPARENT

        return super().nativeEvent(eventType, message)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space:
            self.burst_projectiles(50)
        elif event.key() == Qt.Key.Key_Escape:
            QApplication.quit()


class GameManager:
    """Central manager driving global timing and overlay instances."""
    def __init__(self):
        self.active_worlds: list[WorldOverlay] = []

        self.clock = QElapsedTimer()
        self.timer = QTimer()
        self.timer.timeout.connect(self._global_tick)

        self.fps_timer = QElapsedTimer()
        self.fps_timer.start()
        self.frame_count = 0

        # Launch Primary Overlay World
        primary_world = WorldOverlay()
        primary_world.showFullScreen()

        primary_world.spawn_entity(300, 300)
        primary_world.spawn_entity(700, 400)
        primary_world.burst_projectiles(100)  # Initial salvo

        self.active_worlds.append(primary_world)

        self.timer.start(16)
        self.clock.start()

    def _global_tick(self) -> None:
        dt_ms = self.clock.restart()
        dt_sec = dt_ms / 1000.0

        for world in self.active_worlds:
            world.update_systems(dt_sec)

        # Debug Statistics Logging
        self.frame_count += 1
        if self.fps_timer.elapsed() >= 1000:
            total_active = sum(
                len(w.projectile_manager.active_projectiles) for w in self.active_worlds
            )
            print(f"[GameManager] FPS: {self.frame_count} | Active Projectiles: {total_active}")
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
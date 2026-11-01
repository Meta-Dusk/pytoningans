from __future__ import annotations

import sys, ctypes, signal, random
from ctypes import wintypes
from typing import TYPE_CHECKING, cast, Optional

from PySide6.QtWidgets import (
    QApplication, QGraphicsItem, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem
)
from PySide6.QtCore import QPointF, Qt, QPoint, QTimer, QElapsedTimer
from PySide6.QtGui import QPixmap, QColor

from pytoningans.core.window_tracker import WindowTracker
from pytoningans.core.particle import Particle, ParticleManager, ParticlePresets
from pytoningans.core.entity.base_entity import BaseEntity

if TYPE_CHECKING:
    from PySide6.QtCore import QByteArray, QRect
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QGraphicsSceneMouseEvent


HTTRANSPARENT = -1
HTCLIENT = 1


class InteractiveEntity(QGraphicsPixmapItem):
    """Test companion entity that updates and accepts click interactions."""
    def __init__(self, x: float, y: float):
        super().__init__()
        self.setPos(x, y)
        self.vx: float = 140.0
        self.vy: float = 140.0
        self.passthrough_mouse: bool = False

        self.red_pix = QPixmap(64, 64)
        self.red_pix.fill(QColor("coral"))

        self.green_pix = QPixmap(64, 64)
        self.green_pix.fill(QColor("mediumseagreen"))

        self.setPixmap(self.red_pix)

    def update_systems(self, dt_sec: float, bounds_w: float, bounds_h: float) -> None:
        new_x: float = self.x() + self.vx * dt_sec
        new_y: float = self.y() + self.vy * dt_sec

        if new_x <= 0 or new_x + 64 >= bounds_w:
            self.vx *= -1
            new_x = max(0.0, min(new_x, bounds_w - 64))

        if new_y <= 0 or new_y + 64 >= bounds_h:
            self.vy *= -1
            new_y = max(0.0, min(new_y, bounds_h - 64))

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
    """Transparent overlay validating particle target tracking and window collisions."""
    def __init__(self, window_tracker: WindowTracker):
        super().__init__()

        flags = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.scene = QGraphicsScene(self)
        self.screen_geom = self.screen().availableGeometry()
        self.scene.setSceneRect(0, 0, self.screen_geom.width(), self.screen_geom.height())

        self.view = QGraphicsView(self.scene, self)
        self.view.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setCentralWidget(self.view)

        self.window_tracker: WindowTracker = window_tracker
        self.entities: list[InteractiveEntity] = []
        self.particle_manager = ParticleManager(self.scene)

        # Textures
        self.dot_pix = QPixmap(8, 8)
        self.dot_pix.fill(QColor("yellow"))

        self.spark_pix = QPixmap(6, 6)
        self.spark_pix.fill(QColor("orange"))

        self.dust_pix = QPixmap(10, 10)
        self.dust_pix.fill(QColor(200, 200, 250, 180))

        self.aura_pix = QPixmap(6, 6)
        self.aura_pix.fill(QColor("cyan"))

    def spawn_entity(self, x: float, y: float) -> None:
        entity = InteractiveEntity(x, y)
        self.scene.addItem(entity)
        self.entities.append(entity)

        # Attach footstep dust trail directly to moving target
        ParticlePresets.dust_trail(
            manager=self.particle_manager,
            pixmap=self.dust_pix,
            target=entity,
            offset=QPointF(32, 60),  # Positioned at foot level
            rate=16.0,
        )

        # Attach ambient aura centered around moving target
        ParticlePresets.ambient_aura(
            manager=self.particle_manager,
            pixmap=self.aura_pix,
            target=entity,
            offset=QPointF(32, 32),  # Positioned at sprite center
            radius=45.0,
            rate=10.0,
            local_space=True
        )

    def launch_window_projectiles(self, count: int = 20) -> None:
        """Launches projectiles that bounce off screen borders and explode on desktop windows."""
        screen_geom: QRect = self.screen_geom
        origin = QPointF(screen_geom.width() / 2, screen_geom.height() - 100)

        for _ in range(count):
            vx: float = random.uniform(-400, 400)
            vy: float = random.uniform(-600, -200)

            def on_hit_win(_: Particle, hit_pos: QPointF):
                ParticlePresets.spark_impact(
                    manager=self.particle_manager,
                    pixmap=self.spark_pix,
                    pos=hit_pos,
                    count=10,
                )

            self.particle_manager.spawn(
                pixmap=self.dot_pix,
                pos=origin,
                velocity=QPointF(vx, vy),
                gravity=180.0,
                lifetime=5.0,
                fade_out=False,
                bounce_bounds=True,
                passthrough_mouse=True,
                collide_windows=True,
                collide_entities=True,
                on_hit_window=on_hit_win,
            )

    def update_systems(self, dt_sec: float) -> None:
        bounds: QRect = self.screen_geom

        # Update Companion Entities
        for entity in self.entities:
            entity.update_systems(dt_sec, bounds.width(), bounds.height())

        # Update Particles & Emitters
        self.particle_manager.update(
            dt_sec=dt_sec,
            bounds_w=bounds.width(),
            bounds_h=bounds.height(),
            window_tracker=self.window_tracker,
            active_entities=cast(list[BaseEntity], self.entities),
        )

    def nativeEvent(
        self, eventType: QByteArray | bytes | bytearray | memoryview[int],
        message: int
    ) -> object:
        msg: wintypes.MSG = wintypes.MSG.from_address(message.__int__())
        if msg.message == 0x0084:  # WM_NCHITTEST
            x: int = ctypes.c_short(msg.lParam & 0xFFFF).value
            y: int = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value

            local_pos: QPoint = self.view.mapFromGlobal(QPoint(x, y))
            scene_pos: QPointF = self.view.mapToScene(local_pos)

            hit_item: Optional[QGraphicsItem] = self.scene.itemAt(scene_pos, self.view.transform())

            if hit_item and not getattr(hit_item, "passthrough_mouse", False):
                return True, HTCLIENT

            return True, HTTRANSPARENT

        return super().nativeEvent(eventType, message)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        match event.key():
            case Qt.Key.Key_Space:
                self.launch_window_projectiles(20)
            case Qt.Key.Key_E:
                # Explosion burst test at screen center
                center = QPointF(self.screen_geom.width() / 2, self.screen_geom.height() / 2)
                ParticlePresets.explode(
                    manager=self.particle_manager,
                    pixmap=self.spark_pix,
                    pos=center,
                    count=40,
                )
            case Qt.Key.Key_Escape:
                QApplication.quit()


class GameManager:
    def __init__(self):
        self.window_tracker = WindowTracker()
        self.active_worlds: list[WorldOverlay] = []

        self.clock = QElapsedTimer()
        self.timer = QTimer()
        self.timer.timeout.connect(self._global_tick)

        self.fps_timer = QElapsedTimer()
        self.fps_timer.start()
        self.frame_count = 0

        # Scan active desktop windows
        self.window_tracker.update()

        primary_world = WorldOverlay(self.window_tracker)
        primary_world.showFullScreen()
        primary_world.spawn_entity(250, 250)

        self.active_worlds.append(primary_world)

        self.timer.start(16)
        self.clock.start()

    def _global_tick(self) -> None:
        dt_ms: int = self.clock.restart()
        dt_sec: float = dt_ms / 1000.0

        # Periodically refresh window positions
        self.window_tracker.update()

        for world in self.active_worlds:
            world.update_systems(dt_sec)

        self.frame_count += 1
        if self.fps_timer.elapsed() >= 1000:
            total_particles: int = sum(
                len(w.particle_manager.active_particles) for w in self.active_worlds
            )
            total_emitters: int = sum(
                len(w.particle_manager.active_emitters) for w in self.active_worlds
            )
            print(
                f"[ParticleSystemTest] FPS: {self.frame_count} | "
                f"Active Particles: {total_particles} | Active Emitters: {total_emitters}"
            )
            self.frame_count = 0
            self.fps_timer.restart()


def sigint_handler(*args):
    print("\n[ParticleSystemTest] Exiting process cleanly...")
    QApplication.quit()
    sys.exit(0)


if __name__ == "__main__":
    print("=" * 30)
    print("Particle System Test")
    print("=" * 30)
    print(
        "Controls:\n"
        "\tSpace -> Spawn Window-Colliding Projectiles\n"
        "\tE -> Trigger a Radial Particle Explosion\n"
        "\tCtrl + C -> (In terminal) Force Terminate Application\n"
        "\tEscape -> Exit Application\n"
    )
    app = QApplication(sys.argv)
    signal.signal(signal.SIGINT, sigint_handler)

    signal_timer = QTimer()
    signal_timer.start(100)
    signal_timer.timeout.connect(lambda: None)

    manager = GameManager()
    sys.exit(app.exec())
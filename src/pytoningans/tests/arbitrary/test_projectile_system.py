from __future__ import annotations

import sys, ctypes, signal, random
from ctypes import wintypes
from typing import TYPE_CHECKING, Optional, Callable

from PySide6.QtWidgets import (
    QApplication, QGraphicsItem, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PySide6.QtCore import QPointF, Qt, QPoint, QTimer, QElapsedTimer
from PySide6.QtGui import QPixmap, QColor

if TYPE_CHECKING:
    from PySide6.QtCore import QRectF, QByteArray, QRect
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QGraphicsSceneMouseEvent, QGraphicsItem
    from pytoningans.core.window_tracker import WindowTracker


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


class Projectile(QGraphicsPixmapItem):
    """Lightweight graphics item representing a moving projectile or particle effect."""

    def __init__(
        self,
        pixmap: QPixmap,
        x: float,
        y: float,
        vx: float,
        vy: float,
        gravity: float = 0.0,
        lifetime: float = 5.0,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_window: Optional[Callable[[Projectile, QPointF], None]] = None,
        on_hit_entity: Optional[Callable[[Projectile, InteractiveEntity], None]] = None,
        on_expire: Optional[Callable[[Projectile], None]] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(pixmap, parent)
        self.setPos(x, y)
        
        self.vx: float = vx
        self.vy: float = vy
        self.gravity: float = gravity
        self.lifetime: float = lifetime
        self.time_alive: float = 0.0
        self.is_dead: bool = False

        # Collision & Mouse behavior toggles
        self.passthrough_mouse: bool = passthrough_mouse
        self.collide_windows: bool = collide_windows
        self.collide_entities: bool = collide_entities

        # Event Callbacks
        self.on_hit_window = on_hit_window
        self.on_hit_entity = on_hit_entity
        self.on_expire = on_expire

        # Optimize C++ layer mouse processing
        if self.passthrough_mouse:
            self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.setAcceptHoverEvents(False)

    def update_systems(
        self,
        dt_sec: float,
        bounds_w: float,
        bounds_h: float,
        window_tracker=None,
        active_entities: Optional[list[InteractiveEntity]] = None,
    ) -> None:
        if self.is_dead:
            return

        # Lifetime expiration
        self.time_alive += dt_sec
        if self.time_alive >= self.lifetime:
            if self.on_expire:
                self.on_expire(self)
            self.destroy()
            return

        # Velocity & Gravity
        if self.gravity != 0.0:
            self.vy += self.gravity * dt_sec

        new_x: float = self.x() + self.vx * dt_sec
        new_y: float = self.y() + self.vy * dt_sec

        # Screen border boundary check / bouncing
        pix_w: int = self.pixmap().width()
        pix_h: int = self.pixmap().height()

        if new_x <= 0 or new_x + pix_w >= bounds_w:
            self.vx *= -1
            new_x = max(0.0, min(new_x, bounds_w - pix_w))

        if new_y <= 0 or new_y + pix_h >= bounds_h:
            self.vy *= -1
            new_y = max(0.0, min(new_y, bounds_h - pix_h))

        self.setPos(new_x, new_y)

        # Optional Win32 Window Collisions (Stubbed for integration)
        if self.collide_windows and window_tracker is not None:
            impact_point = QPointF(new_x + pix_w / 2, new_y + pix_h / 2)
            if hasattr(window_tracker, "check_point_collision") and window_tracker.check_point_collision(impact_point):
                if self.on_hit_window:
                    self.on_hit_window(self, impact_point)
                self.destroy()
                return

        # Optional Entity Collisions
        if self.collide_entities and active_entities:
            hitbox: QRectF = self.sceneBoundingRect()
            for entity in active_entities:
                if entity.sceneBoundingRect().intersects(hitbox):
                    if self.on_hit_entity:
                        self.on_hit_entity(self, entity)
                    self.destroy()
                    return

    def destroy(self) -> None:
        self.is_dead = True
        if self.scene():
            self.scene().removeItem(self)

class ProjectileManager:
    """
    Manages active projectiles, handling creation, tick updates, and scene cleanup.
    """

    def __init__(self, scene: QGraphicsScene):
        self.scene: QGraphicsScene = scene
        self.active_projectiles: list[Projectile] = []

    def spawn(
        self,
        pixmap: QPixmap,
        pos: QPointF,
        velocity: QPointF,
        gravity: float = 0.0,
        lifetime: float = 5.0,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        **kwargs,
    ) -> Projectile:
        proj = Projectile(
            pixmap=pixmap,
            x=pos.x(),
            y=pos.y(),
            vx=velocity.x(),
            vy=velocity.y(),
            gravity=gravity,
            lifetime=lifetime,
            passthrough_mouse=passthrough_mouse,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            **kwargs,
        )
        self.scene.addItem(proj)
        self.active_projectiles.append(proj)
        return proj

    def update(
        self,
        dt_sec: float,
        bounds_w: float,
        bounds_h: float,
        window_tracker: Optional[WindowTracker] = None,
        active_entities: Optional[list[InteractiveEntity]] = None,
    ) -> None:
        surviving_projectiles: list[Projectile] = []

        for projectile in self.active_projectiles:
            projectile.update_systems(
                dt_sec,
                bounds_w,
                bounds_h,
                window_tracker=window_tracker,
                active_entities=active_entities,
            )
            if projectile.is_dead:
                # Ensures scene removal if destroy() wasn't directly called
                if projectile.scene():
                    self.scene.removeItem(projectile)
            else:
                surviving_projectiles.append(projectile)

        self.active_projectiles = surviving_projectiles

    def clear_all(self) -> None:
        for projectile in self.active_projectiles:
            if projectile.scene():
                self.scene.removeItem(projectile)
        self.active_projectiles.clear()


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
        screen_geom: QRect = self.screen().availableGeometry()
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
        self.projectile_pixmap = QPixmap(10, 10)
        self.projectile_pixmap.fill(QColor("yellow"))

    def spawn_entity(self, x: float, y: float) -> None:
        entity = InteractiveEntity(x, y)
        self.scene.addItem(entity)
        self.entities.append(entity)

    def burst_projectiles(self, count: int = 50) -> None:
        geometry: QRect = self.screen().availableGeometry()
        center_x: float = geometry.width() / 2
        center_y: float = geometry.height() / 2

        for _ in range(count):
            velocity_x: float = random.uniform(-500, 500)
            velocity_y: float = random.uniform(-500, 500)
            self.projectile_manager.spawn(
                pixmap=self.projectile_pixmap,
                pos=QPointF(center_x, center_y),
                velocity=QPointF(velocity_x, velocity_y),
                gravity=150.0,  # Light downward gravity arc
                lifetime=6.0,
                passthrough_mouse=True,
            )

    def update_systems(self, dt_sec: float) -> None:
        bounds: QRect = self.screen().availableGeometry()

        # Update Companion Entities
        for entity in self.entities:
            entity.update_systems(dt_sec, bounds.width(), bounds.height())

        # Update Projectiles via Manager
        self.projectile_manager.update(
            dt_sec=dt_sec,
            bounds_w=bounds.width(),
            bounds_h=bounds.height(),
            active_entities=self.entities,
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

            # Only intercept mouse if hit item is NOT a passthrough projectile
            if hit_item and not getattr(hit_item, "passthrough_mouse", False):
                return True, HTCLIENT

            return True, HTTRANSPARENT

        return super().nativeEvent(eventType, message)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        match event.key():
            case Qt.Key.Key_Space:
                self.burst_projectiles(50)
            case Qt.Key.Key_Escape:
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
        dt_ms: int = self.clock.restart()
        dt_sec: float = dt_ms / 1000.0

        for world in self.active_worlds:
            world.update_systems(dt_sec)

        # Debug Statistics Logging
        self.frame_count += 1
        if self.fps_timer.elapsed() >= 1000:
            total_active: int = sum(
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
    print("=" * 30)
    print("Projectile System Test")
    print("=" * 30)
    print(
        "Controls:\n"
        "\tSpace -> Spawn Projectiles (Burst)\n"
        "\tCtrl + C -> (In terminal) Force Terminate Application\n"
        "\tEscape -> Exit Application\n"
    )
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
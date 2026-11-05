from __future__ import annotations

import sys, ctypes, signal, random, math
from ctypes import wintypes
from typing import TYPE_CHECKING, cast, Optional

from PySide6.QtWidgets import (
    QApplication, QGraphicsItem, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem
)
from PySide6.QtCore import QPointF, Qt, QPoint, QTimer, QElapsedTimer
from PySide6.QtGui import QPixmap, QColor, QPainter

from pytoningans.core.window_tracker import WindowTracker
from pytoningans.core.particle import (
    ParticleManager, ParticlePresets, ParticleEmitterConfig, ParticleConfig
)
from pytoningans.core.particle import ProceduralGraphics as pg

if TYPE_CHECKING:
    from PySide6.QtCore import QByteArray, QRect
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QGraphicsSceneMouseEvent
    from pytoningans.core.entity import BaseEntity
    from pytoningans.core.particle import ParticleEmitter, Particle


HTTRANSPARENT = -1
HTCLIENT = 1


def generate_animated_orb_spritesheet(
    frame_width: int = 32, frame_height: int = 32, frame_count: int = 4
) -> QPixmap:
    """Generates a procedural glowing orb sprite sheet for AnimatedParticle testing."""
    sheet = QPixmap(frame_width * frame_count, frame_height)
    sheet.fill(Qt.GlobalColor.transparent)

    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    palette: list[QColor] = [
        QColor(0, 240, 255),
        QColor(255, 80, 220),
        QColor(255, 230, 0),
        QColor(80, 255, 120),
    ]

    for i in range(frame_count):
        cx: float = i * frame_width + frame_width / 2.0
        cy: float = frame_height / 2.0
        color: QColor = palette[i % len(palette)]

        # Outer ring
        painter.setPen(color)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), 12.0, 12.0)

        # Core dot with phase pulsing
        core_r = 4.0 + (i % 3) * 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

    painter.end()
    return sheet


class InteractiveEntity(QGraphicsPixmapItem):
    """Moving desktop entity that acts as the homing target and interaction anchor."""

    def __init__(self, x: float, y: float) -> None:
        super().__init__()
        self.setPos(x, y)
        self.vx: float = 160.0
        self.vy: float = 160.0
        self.passthrough_mouse: bool = False

        self.normal_pix: QPixmap = pg.create_glow_circle(
            32, QColor("cyan"), QColor(0, 180, 255, 0)
        )
        self.clicked_pix: QPixmap = pg.create_glow_circle(
            32, QColor("magenta"), QColor(255, 0, 180, 0)
        )

        self.setPixmap(self.normal_pix)

    def update_systems(self, dt_sec: float, bounds_w: float, bounds_h: float) -> None:
        new_x: float = self.x() + self.vx * dt_sec
        new_y: float = self.y() + self.vy * dt_sec

        w: int = self.pixmap().width()
        h: int = self.pixmap().height()

        if new_x <= 0 or new_x + w >= bounds_w:
            self.vx *= -1
            new_x = max(0.0, min(new_x, bounds_w - w))

        if new_y <= 0 or new_y + h >= bounds_h:
            self.vy *= -1
            new_y = max(0.0, min(new_y, bounds_h - h))

        self.setPos(new_x, new_y)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setPixmap(self.clicked_pix)
            event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setPixmap(self.normal_pix)
            event.accept()


class WorldOverlay(QMainWindow):
    """Transparent overlay validating Phase 1-3 advanced particle extensions."""

    def __init__(self, window_tracker: WindowTracker) -> None:
        super().__init__()

        flags: Qt.WindowType = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.scene = QGraphicsScene(self)
        self.screen_geom: QRect = self.screen().availableGeometry()
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

        # Core Particle Manager
        self.particle_manager = ParticleManager(self.scene)

        # Procedural Textures & Sprite Sheets
        self.spark_pix: QPixmap = pg.create_dot(4, QColor("gold"))
        self.smoke_pix: QPixmap = pg.create_dot(3, QColor(220, 220, 220, 180))
        self.rocket_pix: QPixmap = pg.create_glow_circle(
            8, QColor("orangered"), QColor(255, 69, 0, 0)
        )
        self.orb_sheet: QPixmap = generate_animated_orb_spritesheet(32, 32, 4)

    def spawn_companion(self, x: float, y: float) -> InteractiveEntity:
        entity = InteractiveEntity(x, y)
        self.scene.addItem(entity)
        self.entities.append(entity)
        
        config = ParticleConfig(
            lifetime=9999.0,
            fade_out=False,
            local_space=False,
            bounce_bounds=False,
            passthrough_mouse=True,
        )

        # Spawn an orbiting/looping AnimatedParticle attached to companion
        self.particle_manager.spawn_animated_particle(
            sprite_sheet=self.orb_sheet,
            pos=QPointF(x + 16, y - 40),
            velocity=QPointF(0, 0),
            frame_width=32,
            frame_height=32,
            frame_count=4,
            fps=8.0,
            loop=True,
            config=config
        )

        return entity

    def launch_window_projectiles(self, count: int = 15) -> None:
        """Launches tagged projectiles with window collision that trigger spark presets on hit."""
        origin = QPointF(self.screen_geom.width() / 2.0, self.screen_geom.height() - 80)

        for _ in range(count):
            vx: float = random.uniform(-350.0, 350.0)
            vy: float = random.uniform(-600.0, -250.0)

            def on_hit_win(proj: Particle, hit_pos: QPointF) -> None:
                assert proj.has_tag("projectile"), "Window projectile missing 'projectile' tag!"
                # Spawn procedural spark explosion on window contact
                ParticlePresets.spark_impact(
                    manager=self.particle_manager,
                    pixmap=self.spark_pix,
                    pos=hit_pos,
                    count=16,
                )
            
            config = ParticleConfig(
                gravity=220.0,
                lifetime=6.0,
                tags={"projectile", "energy_bolt"},
                orient_to_velocity=True,
                collide_windows=True,
                collide_entities=True,
                passthrough_mouse=True,
                on_hit_window=on_hit_win,
            )

            self.particle_manager.spawn_projectile(
                pixmap=("glow_circle", 6, "cyan", "transparent"),
                pos=QPointF(origin.x(), origin.y()),
                velocity=QPointF(vx, vy),
                config=config
            )

    def launch_homing_missile(self) -> None:
        """
        Fires a homing missile featuring `orient_to_velocity`, 
        smoke trail sub-emitter, and cluster explosion.
        """
        if not self.entities:
            return

        target_entity: InteractiveEntity = self.entities[0]
        screen_w: int = self.screen_geom.width()
        screen_h: int = self.screen_geom.height()

        # Spawn near a corner, firing outward initially
        spawn_x: float = random.choice([80.0, screen_w - 80.0])
        spawn_y: float = screen_h - 100.0
        init_vx: float = 300.0 if spawn_x < screen_w / 2 else -300.0
        init_vy: float = -350.0

        # Sub-Emitter 1 (Spawn Trail Hook): Attaches a continuous smoke trail to this missile
        def smoke_trail_hook(manager: ParticleManager, missile: Particle) -> ParticleEmitter:
            config = ParticleEmitterConfig(
                pixmap=self.smoke_pix,
                target=missile,
                offset=QPointF(4.0, 4.0),
                rate=30.0,
                velocity_x_range=(-15.0, 15.0),
                velocity_y_range=(-15.0, 15.0),
                lifetime_range=(0.4, 0.8),
                scale_over_time_range=(0.6, 2.0),
                fade_out=True,
                bounce_bounds=False,
                passthrough_mouse=True,
            )
            return manager.create_emitter(config=config)

        # Sub-Emitter 2 (Expire Cluster Hook): Bursts secondary falling spark cluster when missile dies
        def cluster_expire_hook(manager: ParticleManager, impact_pos: QPointF) -> None:
            config = ParticleEmitterConfig(
                pixmap=self.spark_pix,
                pos=impact_pos,
                velocity_x_range=(-250.0, 250.0),
                velocity_y_range=(-300.0, -80.0),
                gravity_range=(350.0, 500.0),
                lifetime_range=(0.6, 1.4),
                scale_over_time_range=(0.8, 0.2),
                fade_out=True,
                bounce_bounds=True,
                passthrough_mouse=True,
            )
            cluster_emitter: ParticleEmitter = manager.create_emitter(config)
            cluster_emitter.burst(25)

        # Create single-burst emitter for the rocket with nested sub-emitters
        config = ParticleEmitterConfig(
            pixmap=self.rocket_pix,
            pos=QPointF(spawn_x, spawn_y),
            velocity_x_range=(init_vx - 50, init_vx + 50),
            velocity_y_range=(init_vy - 50, init_vy + 50),
            gravity_range=(0.0, 0.0),
            lifetime_range=(4.0, 5.0),
            orient_to_velocity=True,
            homing_target=target_entity,
            homing_speed=200.0,
            tags={"projectile", "homing_missile"},
            collide_windows=True,
            collide_entities=True,
            passthrough_mouse=True,
            on_particle_spawn_emitter=smoke_trail_hook,
            on_particle_expire_emitter=cluster_expire_hook,
        )
        emitter: ParticleEmitter = self.particle_manager.create_emitter(config)
        emitter.burst(1)

    def spawn_procedural_shapes_burst(self) -> None:
        """
        Spawns an array of all procedural shapes
        (dots, squares, rings, glow circles) at screen center.
        """
        center = QPointF(self.screen_geom.width() / 2.0, self.screen_geom.height() / 2.0)
        shapes: list[tuple] = [
            ("dot", 8, "yellow"),
            ("square", 14, "magenta"),
            ("ring", 12, 3, "springgreen"),
            ("glow_circle", 16, "orange", "transparent"),
        ]

        for shape in shapes:
            for _ in range(8):
                angle: float = random.uniform(0, 2 * math.pi)
                spd: float = random.uniform(120.0, 280.0)
                vx: float = math.cos(angle) * spd
                vy: float = math.sin(angle) * spd
                
                config = ParticleConfig(
                    gravity=120.0,
                    lifetime=2.5,
                    rotation_speed=random.uniform(-180.0, 180.0),
                    fade_out=True,
                    bounce_bounds=True,
                )

                self.particle_manager.spawn(
                    pixmap=shape,
                    pos=center,
                    velocity=QPointF(vx, vy),
                    config=config
                )

    def update_systems(self, dt_sec: float) -> None:
        bounds: QRect = self.screen_geom

        # Update companion entity
        for entity in self.entities:
            entity.update_systems(dt_sec, bounds.width(), bounds.height())

        # Update particles, emitters, and collisions
        self.particle_manager.update(
            dt_sec=dt_sec,
            bounds_w=bounds.width(),
            bounds_h=bounds.height(),
            window_tracker=self.window_tracker,
            active_entities=cast(list["BaseEntity"], self.entities),
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
                self.launch_window_projectiles(15)
            case Qt.Key.Key_1:
                self.launch_homing_missile()
            case Qt.Key.Key_2:
                self.spawn_procedural_shapes_burst()
            case Qt.Key.Key_3:
                # Radial explosion preset
                center = QPointF(self.screen_geom.width() / 2.0, self.screen_geom.height() / 2.0)
                generated_pixmap: QPixmap = pg.resolve_texture(
                    ("glow_circle", 10, "red", "yellow")
                )
                ParticlePresets.explode(
                    manager=self.particle_manager,
                    pixmap=generated_pixmap,
                    pos=center,
                    count=35,
                )
            case Qt.Key.Key_C:
                # Test manager cleanup
                self.particle_manager.clear_all()
                print("[TestAdvancedParticles] ParticleManager.clear_all() executed.")
            case Qt.Key.Key_Escape:
                QApplication.quit()


class GameManager:
    """Game runner coordinating the tracker, world overlay, and high-frequency update ticks."""

    def __init__(self) -> None:
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
        primary_world.spawn_companion(200.0, 200.0)

        self.active_worlds.append(primary_world)

        self.timer.start(16)
        self.clock.start()

    def _global_tick(self) -> None:
        dt_ms: int = self.clock.restart()
        dt_sec: float = dt_ms / 1000.0

        # Window tracker scan
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
                f"[AdvancedParticlesTest] FPS: {self.frame_count} | "
                f"Active Particles: {total_particles} | Active Emitters: {total_emitters}"
            )
            self.frame_count = 0
            self.fps_timer.restart()


def sigint_handler(*args) -> None:
    print("\n[AdvancedParticlesTest] Terminating cleanly...")
    QApplication.quit()
    sys.exit(0)


if __name__ == "__main__":
    print("=" * 60)
    print("Advanced Particle System Test")
    print("=" * 60)
    print(
        "Interactive Controls:\n"
        "\tSpace  -> Launch Tagged Window-Colliding Projectiles\n"
        "\t1      -> Fire Homing Rocket (orient_to_velocity + smoke trail + cluster)\n"
        "\t2      -> Burst Procedural Shapes (dots, squares, rings, glow circles)\n"
        "\t3      -> Radial Explosion Preset via ParticleAPI\n"
        "\tC      -> Clear All Particles and Active Emitters\n"
        "\tEscape -> Exit Test Application\n"
        "\tCtrl+C -> Terminal Force Terminate\n"
    )
    app = QApplication(sys.argv)
    signal.signal(signal.SIGINT, sigint_handler)

    signal_timer = QTimer()
    signal_timer.start(100)
    signal_timer.timeout.connect(lambda: None)

    manager = GameManager()
    sys.exit(app.exec())


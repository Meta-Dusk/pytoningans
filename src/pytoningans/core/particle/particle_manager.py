from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable
from PySide6.QtCore import QPointF

from .particle import Particle
from .particle_emitter import ParticleEmitter

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
    from ..entity.base_entity import BaseEntity
    from ..window_tracker import WindowTracker


class ParticleManager:
    """Manages active particles and emitters, handling updates and scene cleanup."""

    def __init__(self, scene: QGraphicsScene):
        self.scene = scene
        self.active_particles: list[Particle] = []
        self.active_emitters: list[ParticleEmitter] = []

    def spawn(
        self,
        pixmap: QPixmap,
        pos: QPointF,
        velocity: QPointF,
        gravity: float = 0.0,
        lifetime: float = 3.0,
        fade_out: bool = True,
        scale_over_time: float = 1.0,
        rotation_speed: float = 0.0,
        local_space: bool = False,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_window: Optional[Callable[[Particle, QPointF], None]] = None,
        on_hit_entity: Optional[Callable[[Particle, BaseEntity], None]] = None,
        on_expire: Optional[Callable[[Particle], None]] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> Particle:
        particle = Particle(
            pixmap=pixmap,
            x=pos.x(),
            y=pos.y(),
            vx=velocity.x(),
            vy=velocity.y(),
            gravity=gravity,
            lifetime=lifetime,
            fade_out=fade_out,
            scale_over_time=scale_over_time,
            rotation_speed=rotation_speed,
            local_space=local_space,
            bounce_bounds=bounce_bounds,
            passthrough_mouse=passthrough_mouse,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            on_hit_window=on_hit_window,
            on_hit_entity=on_hit_entity,
            on_expire=on_expire,
            parent=parent,
        )
        
        # If item has no parent, add to scene root.
        #? Parented items join scene automatically.
        if parent is None or particle.scene() is None:
            self.scene.addItem(particle)
            
        self.active_particles.append(particle)
        return particle

    def create_emitter(
        self,
        pixmap: QPixmap,
        pos: QPointF = QPointF(0, 0),
        target: Optional[QGraphicsItem] = None,
        offset: QPointF = QPointF(0, 0),
        local_space: bool = False,
        rate: float = 0.0,
        duration: Optional[float] = None,
        velocity_x_range: tuple[float, float] = (-50.0, 50.0),
        velocity_y_range: tuple[float, float] = (-50.0, 50.0),
        gravity_range: tuple[float, float] = (0.0, 0.0),
        lifetime_range: tuple[float, float] = (1.0, 2.5),
        rotation_speed_range: tuple[float, float] = (0.0, 0.0),
        scale_over_time_range: tuple[float, float] = (1.0, 1.0),
        spawn_radius: float = 0.0,
        fade_out: bool = True,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_window: Optional[Callable[[Particle, QPointF], None]] = None,
        on_hit_entity: Optional[Callable[[Particle, BaseEntity], None]] = None,
        on_expire: Optional[Callable[[Particle], None]] = None,
    ) -> ParticleEmitter:
        emitter = ParticleEmitter(
            particle_manager=self,
            pixmap=pixmap,
            pos=pos,
            target=target,
            offset=offset,
            local_space=local_space,
            rate=rate,
            duration=duration,
            velocity_x_range=velocity_x_range,
            velocity_y_range=velocity_y_range,
            gravity_range=gravity_range,
            lifetime_range=lifetime_range,
            rotation_speed_range=rotation_speed_range,
            scale_over_time_range=scale_over_time_range,
            spawn_radius=spawn_radius,
            fade_out=fade_out,
            bounce_bounds=bounce_bounds,
            passthrough_mouse=passthrough_mouse,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            on_hit_window=on_hit_window,
            on_hit_entity=on_hit_entity,
            on_expire=on_expire,
        )

        if emitter.rate > 0.0 or emitter.duration is not None:
            self.active_emitters.append(emitter)
        else:
            emitter.is_finished = True

        return emitter

    def update(
        self, dt_sec: float,
        bounds_w: float, bounds_h: float,
        window_tracker: Optional[WindowTracker] = None,
        active_entities: Optional[list[BaseEntity]] = None,
    ) -> None:
        surviving_emitters: list[ParticleEmitter] = []
        for emitter in self.active_emitters:
            emitter.update(dt_sec)
            if not emitter.is_finished:
                surviving_emitters.append(emitter)
        self.active_emitters = surviving_emitters

        surviving_particles: list[Particle] = []
        for particle in self.active_particles:
            particle.update_systems(
                dt_sec, bounds_w, bounds_h,
                window_tracker=window_tracker,
                active_entities=active_entities,
            )
            if particle.is_dead:
                if particle.scene():
                    self.scene.removeItem(particle)
            else:
                surviving_particles.append(particle)

        self.active_particles = surviving_particles

    def clear_all(self) -> None:
        for particle in self.active_particles:
            if particle.scene():
                self.scene.removeItem(particle)
        self.active_particles.clear()
        self.active_emitters.clear()

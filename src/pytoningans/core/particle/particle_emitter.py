from __future__ import annotations

import math, random
from typing import TYPE_CHECKING, Callable, Optional
from PySide6.QtCore import QPointF

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QGraphicsItem
    from .particle import Particle
    from .particle_manager import ParticleManager


class ParticleEmitter:
    """Handles spawning continuous streams, shape-based bursts, or trails of particles."""

    def __init__(
        self,
        particle_manager: ParticleManager,
        pixmap: QPixmap,
        pos: QPointF = QPointF(0, 0),
        target: Optional[QGraphicsItem] = None,
        offset: QPointF = QPointF(0, 0),
        local_space: bool = False,  # Glues particles directly to target item hierarchy
        # Emission Rate & Duration
        rate: float = 0.0,
        duration: Optional[float] = None,
        # Randomization Ranges
        velocity_x_range: tuple[float, float] = (-50.0, 50.0),
        velocity_y_range: tuple[float, float] = (-50.0, 50.0),
        gravity_range: tuple[float, float] = (0.0, 0.0),
        lifetime_range: tuple[float, float] = (1.0, 2.5),
        rotation_speed_range: tuple[float, float] = (0.0, 0.0),
        scale_over_time_range: tuple[float, float] = (1.0, 1.0),
        # Shape & Radius
        spawn_radius: float = 0.0,
        # Particle Flags
        fade_out: bool = True,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        # Particle Callbacks
        on_hit_window: Optional[Callable] = None,
        on_hit_entity: Optional[Callable] = None,
        on_expire: Optional[Callable] = None,
    ) -> None:
        self.particle_manager: ParticleManager = particle_manager
        self.pixmap: QPixmap = pixmap
        self.pos: QPointF = pos
        self.target: Optional[QGraphicsItem] = target
        self.offset: QPointF = offset
        self.local_space: bool = local_space

        self.rate: float = rate
        self.duration: Optional[float] = duration
        self.time_active: float = 0.0
        self.emission_accumulator: float = 0.0
        self.is_finished: bool = False
        self.is_active: bool = True

        # Range Toggles
        self.velocity_x_range: tuple[float, float] = velocity_x_range
        self.velocity_y_range: tuple[float, float] = velocity_y_range
        self.gravity_range: tuple[float, float] = gravity_range
        self.lifetime_range: tuple[float, float] = lifetime_range
        self.rotation_speed_range: tuple[float, float] = rotation_speed_range
        self.scale_over_time_range: tuple[float, float] = scale_over_time_range
        self.spawn_radius: float = spawn_radius

        # Defaults
        self.fade_out: bool = fade_out
        self.bounce_bounds: bool = bounce_bounds
        self.passthrough_mouse: bool = passthrough_mouse
        self.collide_windows: bool = collide_windows
        self.collide_entities: bool = collide_entities

        # Callbacks
        self.on_hit_window = on_hit_window
        self.on_hit_entity = on_hit_entity
        self.on_expire = on_expire

    def update(self, dt_sec: float, pos_override: Optional[QPointF] = None) -> None:
        if not self.is_active or self.is_finished:
            return

        # Position tracking for world-space emitters
        if not self.local_space:
            if pos_override is not None:
                self.pos = pos_override
            elif self.target is not None:
                self.pos = self.target.pos() + self.offset

        # Check total emitter duration
        if self.duration is not None:
            self.time_active += dt_sec
            if self.time_active >= self.duration:
                self.is_finished = True
                return

        # Stream emission rate
        if self.rate > 0.0:
            self.emission_accumulator += dt_sec * self.rate
            spawn_count = int(self.emission_accumulator)
            if spawn_count > 0:
                self.emission_accumulator -= spawn_count
                self.burst(spawn_count)

    def burst(self, count: int) -> list[Particle]:
        spawned_particles: list[Particle] = []
        parent_item: Optional[QGraphicsItem]

        for _ in range(count):
            offset_x, offset_y = 0.0, 0.0
            if self.spawn_radius > 0.0:
                angle: float = random.uniform(0, 2 * math.pi)
                dist: float = random.uniform(0, self.spawn_radius)
                offset_x: float = math.cos(angle) * dist
                offset_y: float = math.sin(angle) * dist

            # Choose coordinate space for spawning
            if self.local_space and self.target is not None:
                spawn_pos = QPointF(self.offset.x() + offset_x, self.offset.y() + offset_y)
                parent_item = self.target
            else:
                spawn_pos = QPointF(self.pos.x() + offset_x, self.pos.y() + offset_y)
                parent_item = None

            vx: float = random.uniform(*self.velocity_x_range)
            vy: float = random.uniform(*self.velocity_y_range)
            gravity: float = random.uniform(*self.gravity_range)
            lifetime: float = random.uniform(*self.lifetime_range)
            rot_speed: float = random.uniform(*self.rotation_speed_range)
            scale_target: float = random.uniform(*self.scale_over_time_range)

            particle: Particle = self.particle_manager.spawn(
                pixmap=self.pixmap,
                pos=spawn_pos,
                velocity=QPointF(vx, vy),
                gravity=gravity,
                lifetime=lifetime,
                fade_out=self.fade_out,
                scale_over_time=scale_target,
                rotation_speed=rot_speed,
                local_space=self.local_space,
                bounce_bounds=self.bounce_bounds,
                passthrough_mouse=self.passthrough_mouse,
                collide_windows=self.collide_windows,
                collide_entities=self.collide_entities,
                on_hit_window=self.on_hit_window,
                on_hit_entity=self.on_hit_entity,
                on_expire=self.on_expire,
                parent=parent_item,
            )
            spawned_particles.append(particle)

        return spawned_particles

    def destroy(self) -> None:
        self.is_active = False
        self.is_finished = True
        self.target = None

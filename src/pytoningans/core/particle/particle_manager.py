from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union, Any
from PySide6.QtCore import QPointF

from .particle_emitter import ParticleEmitter
from .procedural_graphics import ProceduralGraphics
from .animated_particle import AnimatedParticle
from .particle import Particle

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
    from ..entity.base_entity import BaseEntity
    from ..window_tracker import WindowTracker
    from .types import (
        OptionalOnParticleExpireEmitterCallback, OptionalOnParticleSpawnEmitterCallback,
        OptionalOnExpireCallback, OptionalOnHitWindowCallback, OptionalOnHitEntityCallback
    )


class ParticleManager:
    """Manages active particles and emitters, handling updates and scene cleanup."""

    def __init__(self, scene: QGraphicsScene):
        self.scene = scene
        self.active_particles: list[Particle] = []
        self.active_emitters: list[ParticleEmitter] = []

    def spawn(
        self,
        pixmap: Union[QPixmap, str, tuple, Any],
        pos: QPointF,
        velocity: QPointF,
        gravity: float = 0.0,
        lifetime: float = 3.0,
        fade_out: bool = True,
        scale_over_time: float = 1.0,
        rotation_speed: float = 0.0,
        # Tags, Motion & Steering
        tags: Optional[set[str]] = None,
        initial_rotation_range: tuple[float, float] = (0.0, 0.0),
        orient_to_velocity: bool = False,
        homing_target: Optional[QGraphicsItem] = None,
        homing_speed: float = 0.0,
        # Collision & Hierarchy Toggles
        local_space: bool = False,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        # Callbacks & Sub-Emitters
        on_hit_window: OptionalOnHitWindowCallback = None,
        on_hit_entity: OptionalOnHitEntityCallback = None,
        on_expire: OptionalOnExpireCallback = None,
        on_particle_expire_emitter: OptionalOnParticleExpireEmitterCallback = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> Particle:
        resolved_pixmap: QPixmap = ProceduralGraphics.resolve_texture(pixmap)

        particle = Particle(
            pixmap=resolved_pixmap,
            x=pos.x(),
            y=pos.y(),
            vx=velocity.x(),
            vy=velocity.y(),
            gravity=gravity,
            lifetime=lifetime,
            fade_out=fade_out,
            scale_over_time=scale_over_time,
            rotation_speed=rotation_speed,
            tags=tags,
            initial_rotation_range=initial_rotation_range,
            orient_to_velocity=orient_to_velocity,
            homing_target=homing_target,
            homing_speed=homing_speed,
            local_space=local_space,
            bounce_bounds=bounce_bounds,
            passthrough_mouse=passthrough_mouse,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            on_hit_window=on_hit_window,
            on_hit_entity=on_hit_entity,
            on_expire=on_expire,
            on_particle_expire_emitter=on_particle_expire_emitter,
            particle_manager=self,
            parent=parent,
        )

        # If item has no parent, add to scene root.
        #? Parented items join scene automatically.
        if parent is None or particle.scene() is None:
            self.scene.addItem(particle)

        self.active_particles.append(particle)
        return particle

    def spawn_projectile(
        self,
        pixmap: Union[QPixmap, str, tuple, Any],
        pos: QPointF,
        velocity: QPointF,
        gravity: float = 0.0,
        lifetime: float = 5.0,
        tags: Optional[set[str]] = None,
        fade_out: bool = True,
        scale_over_time: float = 1.0,
        rotation_speed: float = 0.0,
        initial_rotation_range: tuple[float, float] = (0.0, 0.0),
        orient_to_velocity: bool = True,
        homing_target: Optional[QGraphicsItem] = None,
        homing_speed: float = 0.0,
        local_space: bool = False,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = True,
        collide_entities: bool = True,
        on_hit_window: OptionalOnHitWindowCallback = None,
        on_hit_entity: OptionalOnHitEntityCallback = None,
        on_expire: OptionalOnExpireCallback = None,
        on_particle_expire_emitter: OptionalOnParticleExpireEmitterCallback = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> Particle:
        """
        Spawns an interactive projectile pre-configured with default collision and
        'projectile' tag.
        """
        proj_tags: set[str] = set(tags) if tags is not None else set()
        proj_tags.add("projectile")

        return self.spawn(
            pixmap=pixmap,
            pos=pos,
            velocity=velocity,
            gravity=gravity,
            lifetime=lifetime,
            fade_out=fade_out,
            scale_over_time=scale_over_time,
            rotation_speed=rotation_speed,
            tags=proj_tags,
            initial_rotation_range=initial_rotation_range,
            orient_to_velocity=orient_to_velocity,
            homing_target=homing_target,
            homing_speed=homing_speed,
            local_space=local_space,
            bounce_bounds=bounce_bounds,
            passthrough_mouse=passthrough_mouse,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            on_hit_window=on_hit_window,
            on_hit_entity=on_hit_entity,
            on_expire=on_expire,
            on_particle_expire_emitter=on_particle_expire_emitter,
            parent=parent,
        )

    def spawn_animated_particle(
        self,
        sprite_sheet: Union[QPixmap, str, tuple, Any],
        pos: QPointF,
        velocity: QPointF,
        frame_width: int,
        frame_height: int,
        frame_count: int,
        fps: float,
        loop: bool = True,
        gravity: float = 0.0,
        lifetime: float = 3.0,
        fade_out: bool = True,
        scale_over_time: float = 1.0,
        rotation_speed: float = 0.0,
        tags: Optional[set[str]] = None,
        initial_rotation_range: tuple[float, float] = (0.0, 0.0),
        orient_to_velocity: bool = False,
        homing_target: Optional[QGraphicsItem] = None,
        homing_speed: float = 0.0,
        local_space: bool = False,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_window: OptionalOnHitWindowCallback = None,
        on_hit_entity: OptionalOnHitEntityCallback = None,
        on_expire: OptionalOnExpireCallback = None,
        on_particle_expire_emitter: OptionalOnParticleExpireEmitterCallback = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> AnimatedParticle:
        """Spawns a sprite-sheet animated particle without entity FSM overhead."""
        resolved_sheet: QPixmap = ProceduralGraphics.resolve_texture(sprite_sheet)

        particle = AnimatedParticle(
            sprite_sheet=resolved_sheet,
            frame_width=frame_width,
            frame_height=frame_height,
            frame_count=frame_count,
            fps=fps,
            loop=loop,
            x=pos.x(),
            y=pos.y(),
            vx=velocity.x(),
            vy=velocity.y(),
            gravity=gravity,
            lifetime=lifetime,
            fade_out=fade_out,
            scale_over_time=scale_over_time,
            rotation_speed=rotation_speed,
            tags=tags,
            initial_rotation_range=initial_rotation_range,
            orient_to_velocity=orient_to_velocity,
            homing_target=homing_target,
            homing_speed=homing_speed,
            local_space=local_space,
            bounce_bounds=bounce_bounds,
            passthrough_mouse=passthrough_mouse,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            on_hit_window=on_hit_window,
            on_hit_entity=on_hit_entity,
            on_expire=on_expire,
            on_particle_expire_emitter=on_particle_expire_emitter,
            particle_manager=self,
            parent=parent,
        )

        if parent is None or particle.scene() is None:
            self.scene.addItem(particle)

        self.active_particles.append(particle)
        return particle

    def create_emitter(
        self,
        pixmap: Union[QPixmap, str, tuple, Any],
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
        initial_rotation_range: tuple[float, float] = (0.0, 0.0),
        spawn_radius: float = 0.0,
        # Motion & Steering & Tags
        tags: Optional[set[str]] = None,
        orient_to_velocity: bool = False,
        homing_target: Optional[QGraphicsItem] = None,
        homing_speed: float = 0.0,
        fade_out: bool = True,
        bounce_bounds: bool = True,
        passthrough_mouse: bool = True,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_window: OptionalOnHitWindowCallback = None,
        on_hit_entity: OptionalOnHitEntityCallback = None,
        on_expire: OptionalOnExpireCallback = None,
        on_particle_spawn_emitter: OptionalOnParticleSpawnEmitterCallback = None,
        on_particle_expire_emitter: OptionalOnParticleExpireEmitterCallback = None,
    ) -> ParticleEmitter:
        resolved_pixmap: QPixmap = ProceduralGraphics.resolve_texture(pixmap)

        emitter = ParticleEmitter(
            particle_manager=self,
            pixmap=resolved_pixmap,
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
            initial_rotation_range=initial_rotation_range,
            spawn_radius=spawn_radius,
            tags=tags,
            orient_to_velocity=orient_to_velocity,
            homing_target=homing_target,
            homing_speed=homing_speed,
            fade_out=fade_out,
            bounce_bounds=bounce_bounds,
            passthrough_mouse=passthrough_mouse,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            on_hit_window=on_hit_window,
            on_hit_entity=on_hit_entity,
            on_expire=on_expire,
            on_particle_spawn_emitter=on_particle_spawn_emitter,
            on_particle_expire_emitter=on_particle_expire_emitter,
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
            particle.destroy()
            if particle.scene():
                self.scene.removeItem(particle)
        self.active_particles.clear()

        for emitter in self.active_emitters:
            emitter.destroy()
        self.active_emitters.clear()

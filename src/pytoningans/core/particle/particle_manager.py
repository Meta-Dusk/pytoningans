from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from dataclasses import replace

from .particle_emitter import ParticleEmitter
from .procedural_graphics import ProceduralGraphics
from .animated_particle import AnimatedParticle
from .particle import Particle

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
    from ..entity.base_entity import BaseEntity
    from ..window_tracker import WindowTracker
    from ..api import Pos2D
    from .types import ParticleConfig, ParticleEmitterConfig, PixmapTypes


class ParticleManager:
    """Manages active particles and emitters, handling updates and scene cleanup."""

    def __init__(self, scene: QGraphicsScene):
        self.scene = scene
        self.active_particles: list[Particle] = []
        self.active_emitters: list[ParticleEmitter] = []

    def spawn(
        self,
        pixmap: PixmapTypes,
        pos: Pos2D,
        velocity: Pos2D,
        config: Optional[ParticleConfig] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> Particle:
        resolved_pixmap: QPixmap = ProceduralGraphics.resolve_texture(pixmap)

        particle = Particle(
            pixmap=resolved_pixmap,
            pos=pos,
            velocity=velocity,
            config=config,
            particle_manager=self,
            parent=parent,
        )

        if parent is None or particle.scene() is None:
            self.scene.addItem(particle)

        self.active_particles.append(particle)
        return particle

    def spawn_projectile(
        self,
        pixmap: PixmapTypes,
        pos: Pos2D,
        velocity: Pos2D,
        config: Optional[ParticleConfig] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> Particle:
        """Spawns an interactive projectile pre-configured with collision and 'projectile' tag."""
        base_cfg = config or ParticleConfig()
        
        # Inject projectile defaults cleanly via replace()
        proj_tags = set(base_cfg.tags)
        proj_tags.add("projectile")
        
        proj_config = replace(
            base_cfg,
            lifetime=base_cfg.lifetime if config else 5.0,
            orient_to_velocity=True,
            collide_windows=True,
            collide_entities=True,
            tags=proj_tags,
        )

        return self.spawn(pixmap, pos, velocity, config=proj_config, parent=parent)

    def spawn_animated_particle(
        self,
        sprite_sheet: PixmapTypes,
        pos: Pos2D,
        velocity: Pos2D,
        frame_width: int,
        frame_height: int,
        frame_count: int,
        fps: float,
        loop: bool = True,
        config: Optional[ParticleConfig] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> AnimatedParticle:
        resolved_sheet: QPixmap = ProceduralGraphics.resolve_texture(sprite_sheet)

        particle = AnimatedParticle(
            sprite_sheet=resolved_sheet,
            pos=pos,
            velocity=velocity,
            frame_width=frame_width,
            frame_height=frame_height,
            frame_count=frame_count,
            fps=fps,
            loop=loop,
            config=config,
            particle_manager=self,
            parent=parent,
        )

        if parent is None or particle.scene() is None:
            self.scene.addItem(particle)

        self.active_particles.append(particle)
        return particle

    def create_emitter(self, config: ParticleEmitterConfig) -> ParticleEmitter:
        emitter = ParticleEmitter(self, config)

        if emitter.config.rate > 0.0 or emitter.config.duration is not None:
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
            if particle.scene() is not None:
                self.scene.removeItem(particle)
        self.active_particles.clear()

        for emitter in self.active_emitters:
            emitter.destroy()
        self.active_emitters.clear()
    
    def clear_particles(self) -> None:
        for particle in self.active_particles:
            particle.destroy()
            if particle.scene() is not None:
                self.scene.removeItem(particle)
    
    def clear_emitters(self) -> None:
        for emitter in self.active_emitters:
            emitter.destroy()
        self.active_emitters.clear()

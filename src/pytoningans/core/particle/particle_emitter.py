from __future__ import annotations

import math, random
from typing import TYPE_CHECKING, Optional

from .types import ParticleConfig
from ..api import Pos2D

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsItem
    from .particle import Particle
    from .particle_manager import ParticleManager
    from .types import ParticleEmitterConfig


class ParticleEmitter:
    """Handles spawning continuous streams, shape-based bursts, or trails of particles."""

    def __init__(self, manager: ParticleManager, config: ParticleEmitterConfig) -> None:
        self.manager: ParticleManager = manager
        self.config: ParticleEmitterConfig = config

        # Mutable Runtime State
        self.pos: Pos2D = config.pos
        self.target: Optional[QGraphicsItem] = config.target
        self.time_active: float = 0.0
        self.emission_accumulator: float = 0.0
        self.is_finished: bool = False
        self.is_active: bool = True
        self.sub_emitters: list[ParticleEmitter] = []

    def update(self, dt_sec: float, pos_override: Optional[Pos2D] = None) -> None:
        if not self.is_active or self.is_finished:
            return

        # Position tracking for world-space emitters (mutates self.pos, not self.config.pos)
        if not self.config.local_space:
            if pos_override is not None:
                self.pos = pos_override
            elif self.target is not None:
                target_pos = self.target.pos()
                conv_pos = Pos2D(target_pos.x(), target_pos.y())
                self.pos = conv_pos + self.config.offset

        # Check total emitter duration
        if self.config.duration is not None:
            self.time_active += dt_sec
            if self.time_active >= self.config.duration:
                self.is_finished = True
                return

        # Stream emission rate
        if self.config.rate > 0.0:
            self.emission_accumulator += dt_sec * self.config.rate
            spawn_count = int(self.emission_accumulator)
            if spawn_count > 0:
                self.emission_accumulator -= spawn_count
                self.burst(spawn_count)

    def burst(self, count: int) -> list[Particle]:
        spawned_particles: list[Particle] = []
        cfg: ParticleEmitterConfig = self.config

        for _ in range(count):
            offset = Pos2D()
            spawn_pos: Pos2D
            parent_item: Optional[QGraphicsItem]
            if cfg.spawn_radius > 0.0:
                angle: float = random.uniform(0, 2 * math.pi)
                dist: float = random.uniform(0, cfg.spawn_radius)
                offset = Pos2D(
                    math.cos(angle) * dist,
                    math.sin(angle) * dist
                )

            if cfg.local_space and self.target is not None:
                spawn_pos = cfg.offset + offset
                parent_item = self.target
            else:
                spawn_pos = self.pos + offset
                parent_item = None
            
            velocity = Pos2D(
                random.uniform(*cfg.velocity_x_range),
                random.uniform(*cfg.velocity_y_range)
            )

            particle_cfg = ParticleConfig.from_emitter_config(
                cfg,
                gravity=random.uniform(*cfg.gravity_range),
                lifetime=random.uniform(*cfg.lifetime_range),
                scale_target=random.uniform(*cfg.scale_over_time_range),
                rotation_speed=random.uniform(*cfg.rotation_speed_range),
            )

            particle: Particle = self.manager.spawn(
                pixmap=cfg.pixmap,
                pos=spawn_pos,
                velocity=velocity,
                config=particle_cfg,
                parent=parent_item,
            )

            if cfg.on_particle_spawn_emitter is not None:
                child_emitter: Optional[ParticleEmitter] = cfg.on_particle_spawn_emitter(
                    self.manager, particle
                )
                if child_emitter is not None:
                    particle.attached_emitters.append(child_emitter)
                    self.sub_emitters.append(child_emitter)
                    if child_emitter not in self.manager.active_emitters:
                        if child_emitter.config.rate > 0.0 or child_emitter.config.duration is not None:
                            self.manager.active_emitters.append(child_emitter)

            spawned_particles.append(particle)

        return spawned_particles

    def destroy(self) -> None:
        self.is_active = False
        self.is_finished = True
        self.target = None
        for sub in self.sub_emitters:
            sub.destroy()
        self.sub_emitters.clear()

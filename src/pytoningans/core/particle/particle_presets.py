from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPixmap

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsItem
    from ..entity.base_entity import BaseEntity
    from .particle import Particle
    from .particle_emitter import ParticleEmitter
    from .particle_manager import ParticleManager


class ParticlePresets:
    """Factory containing reusable particle effect configurations for companions and modders."""

    @staticmethod
    def explode(
        manager: ParticleManager,
        pixmap: QPixmap,
        pos: QPointF,
        count: int = 30,
        speed_min: float = 100.0,
        speed_max: float = 300.0,
        gravity: float = 200.0,
        lifetime: float = 1.2,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_entity: Optional[Callable[[Particle, BaseEntity], None]] = None,
    ) -> list[Particle]:
        """Creates a radial burst of particles that arc outward with gravity."""
        emitter: ParticleEmitter = manager.create_emitter(
            pixmap=pixmap,
            pos=pos,
            velocity_x_range=(-speed_max, speed_max),
            velocity_y_range=(-speed_max, speed_max),
            gravity_range=(gravity, gravity * 1.5),
            lifetime_range=(lifetime * 0.5, lifetime),
            scale_over_time_range=(0.2, 0.8),
            fade_out=True,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            on_hit_entity=on_hit_entity,
        )
        return emitter.burst(count)

    @staticmethod
    def dust_trail(
        manager: ParticleManager,
        pixmap: QPixmap,
        pos: QPointF = QPointF(0, 0),
        target: Optional[QGraphicsItem] = None,
        offset: QPointF = QPointF(0, 0),
        rate: float = 15.0,
        duration: Optional[float] = None,
    ) -> ParticleEmitter:
        """Spawns soft, rising dust particles attached to a moving target or position."""
        return manager.create_emitter(
            pixmap=pixmap,
            pos=pos,
            target=target,
            offset=offset,
            rate=rate,
            duration=duration,
            velocity_x_range=(-20.0, 20.0),
            velocity_y_range=(-40.0, -10.0),
            gravity_range=(0.0, 0.0),
            lifetime_range=(0.4, 0.8),
            scale_over_time_range=(1.2, 1.8),
            fade_out=True,
            bounce_bounds=False,
            passthrough_mouse=True,
        )

    @staticmethod
    def spark_impact(
        manager: ParticleManager,
        pixmap: QPixmap,
        pos: QPointF,
        count: int = 12,
    ) -> list[Particle]:
        """Fast, short-lived sparks emitted when a projectile hits a window or entity."""
        emitter: ParticleEmitter = manager.create_emitter(
            pixmap=pixmap,
            pos=pos,
            velocity_x_range=(-250.0, 250.0),
            velocity_y_range=(-250.0, 250.0),
            gravity_range=(100.0, 300.0),
            lifetime_range=(0.15, 0.35),
            rotation_speed_range=(-360.0, 360.0),
            scale_over_time_range=(0.1, 0.5),
            fade_out=True,
            bounce_bounds=False,
            passthrough_mouse=True,
        )
        return emitter.burst(count)

    @staticmethod
    def ambient_aura(
        manager: ParticleManager,
        pixmap: QPixmap,
        pos: QPointF = QPointF(0, 0),
        target: Optional[QGraphicsItem] = None,
        offset: QPointF = QPointF(0, 0),
        radius: float = 25.0,
        rate: float = 10.0,
        local_space: bool = False
    ) -> ParticleEmitter:
        """Orbiting/floating particles surrounding magical pets or active portals."""
        return manager.create_emitter(
            pixmap=pixmap,
            pos=pos,
            target=target,
            offset=offset,
            local_space=local_space,
            rate=rate,
            spawn_radius=radius,
            velocity_x_range=(-15.0, 15.0),
            velocity_y_range=(-30.0, -5.0),
            gravity_range=(-20.0, 0.0),
            lifetime_range=(1.5, 3.0),
            scale_over_time_range=(0.5, 1.0),
            fade_out=True,
            bounce_bounds=False,
            passthrough_mouse=True,
        )

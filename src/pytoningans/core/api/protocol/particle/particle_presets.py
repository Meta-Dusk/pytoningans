from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from .particle_configs import ParticleEmitterConfigDTO
from ...types import Pos2D

if TYPE_CHECKING:
    from .particle import IParticle
    from .particle_manager import IParticleManager
    from .particle_emitter import IParticleEmitter
    from ...types import ResolvableTexture, OptionalOnHitEntityCallback, IGraphicsItem


class ParticlePresets:
    """
    A helper class that wraps the particle manager. Provides access to example implementations.
    """
    def __init__(self, particle_manager: IParticleManager) -> None:
        """The real ParticleManager instance can be found in a IWorld instance."""
        self.manager: IParticleManager = particle_manager
    
    def explode(
        self,
        texture: ResolvableTexture,
        pos: Pos2D,
        count: int = 30,
        speed: float = 300.0,
        gravity: float = 200.0,
        lifetime: float = 1.2,
        collide_windows: bool = False,
        collide_entities: bool = False,
        on_hit_entity: OptionalOnHitEntityCallback = None,
    ) -> list[IParticle]:
        """Creates a radial burst of particles that arc outward with gravity."""
        config = ParticleEmitterConfigDTO(
            pixmap=texture,
            pos=pos,
            velocity_x_range=(-speed, speed),
            velocity_y_range=(-speed, speed),
            gravity_range=(gravity, gravity * 1.5),
            lifetime_range=(lifetime * 0.5, lifetime),
            scale_over_time_range=(0.2, 0.8),
            fade_out=True,
            collide_windows=collide_windows,
            collide_entities=collide_entities,
            on_hit_entity=on_hit_entity,
        )
        emitter: IParticleEmitter = self.manager.create_emitter(config)
        return emitter.burst(count)

    def dust_trail(
        self,
        texture: ResolvableTexture,
        pos: Pos2D = Pos2D(0, 0),
        target: Optional[IGraphicsItem] = None,
        offset: Pos2D = Pos2D(0, 0),
        rate: float = 15.0,
        duration: Optional[float] = None,
    ) -> IParticleEmitter:
        """Spawns soft, rising dust particles attached to a moving target or position."""
        config = ParticleEmitterConfigDTO(
            pixmap=texture,
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
        return self.manager.create_emitter(config)

    def spark_impact(
        self,
        texture: ResolvableTexture,
        pos: Pos2D,
        count: int = 12,
    ) -> list[IParticle]:
        """Fast, short-lived sparks emitted when a projectile hits a window or entity."""
        config = ParticleEmitterConfigDTO(
            pixmap=texture,
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
        emitter: IParticleEmitter = self.manager.create_emitter(config)
        return emitter.burst(count)

    def ambient_aura(
        self,
        texture: ResolvableTexture,
        pos: Pos2D = Pos2D(0, 0),
        target: Optional[IGraphicsItem] = None,
        offset: Pos2D = Pos2D(0, 0),
        radius: float = 25.0,
        rate: float = 10.0,
        local_space: bool = False
    ) -> IParticleEmitter:
        """Orbiting/floating particles."""
        config = ParticleEmitterConfigDTO(
            pixmap=texture,
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
        return self.manager.create_emitter(config)

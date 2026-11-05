from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .particle import IParticle
    from .animated_particle import IAnimatedParticle
    from .particle_emitter import IParticleEmitter
    from .particle_configs import ParticleConfigDTO, ParticleEmitterConfigDTO
    from ...types import Pos2D, IGraphicsItem, ResolvableTexture


@runtime_checkable
class IParticleManager(Protocol):
    """Public interface for spawning particles, and creating emitters."""
    
    active_particles: list[IParticle]
    active_emitters: list[IParticleEmitter]

    def spawn(
        self,
        pixmap: ResolvableTexture,
        pos: Pos2D,
        velocity: Pos2D,
        config: Optional[ParticleConfigDTO] = None,
        parent: Optional[IGraphicsItem] = None,
    ) -> IParticle:
        ...

    def spawn_projectile(
        self,
        pixmap: ResolvableTexture,
        pos: Pos2D,
        velocity: Pos2D,
        config: Optional[ParticleConfigDTO] = None,
        parent: Optional[IGraphicsItem] = None,
    ) -> IParticle:
        """Spawns an interactive projectile pre-configured with collision and 'projectile' tag."""
        ...

    def spawn_animated_particle(
        self,
        sprite_sheet: ResolvableTexture,
        pos: Pos2D,
        velocity: Pos2D,
        frame_width: int,
        frame_height: int,
        frame_count: int,
        fps: float,
        loop: bool = True,
        config: Optional[ParticleConfigDTO] = None,
        parent: Optional[IGraphicsItem] = None,
    ) -> IAnimatedParticle:
        ...

    def create_emitter(self, config: ParticleEmitterConfigDTO) -> IParticleEmitter:
        """Creates a continuous stream or timed duration particle emitter."""
        ...
    
    def clear_all(self) -> None: ...

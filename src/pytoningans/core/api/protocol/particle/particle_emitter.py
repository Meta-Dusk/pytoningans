from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .particle import IParticle
    from .particle_configs import ParticleEmitterConfigDTO
    from ...types import Pos2D, IGraphicsItem


@runtime_checkable
class IParticleEmitter(Protocol):
    """Interface representing a continuous stream, burst, or trail particle emitter."""
    config: ParticleEmitterConfigDTO
    pos: Pos2D
    target: Optional[IGraphicsItem]
    time_active: float
    emission_accumulator: float
    is_finished: bool
    is_active: bool
    sub_emitters: list[IParticleEmitter]

    def burst(self, count: int) -> list[IParticle]:
        """Instantly emits a batch of particles with randomized properties."""
        ...

    def destroy(self) -> None:
        """Stops the emitter and marks it for scene removal."""
        ...


from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .particle import IParticle
    from ..entity import IBaseEntity
    from ...types import Pos2D


@runtime_checkable
class IParticleEmitter(Protocol):
    """Interface representing a continuous stream, burst, or trail particle emitter."""
    pos: Pos2D
    offset: Pos2D
    target: Optional[IBaseEntity]
    local_space: bool
    rate: float
    duration: Optional[float]
    is_active: bool
    is_finished: bool
    sub_emitters: list[IParticleEmitter]
    initial_rotation_range: tuple[float, float]

    def burst(self, count: int) -> list[IParticle]:
        """Instantly emits a batch of particles with randomized properties."""
        ...

    def destroy(self) -> None:
        """Stops the emitter and marks it for scene removal."""
        ...


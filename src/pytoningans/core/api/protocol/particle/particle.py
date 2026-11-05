from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ...types import Pos2D, IGraphicsItem


@runtime_checkable
class IParticle(Protocol):
    """Interface representing a moving particle (can be a projectile as well)."""
    pos: Pos2D
    velocity: Pos2D
    gravity: float
    lifetime: float
    time_alive: float
    is_dead: bool
    local_space: bool
    bounce_bounds: bool
    passthrough_mouse: bool
    collide_windows: bool
    collide_entities: bool
    tags: set[str]
    orient_to_velocity: bool
    homing_target: Optional[IGraphicsItem]
    homing_speed: float

    def has_tag(self, tag: str) -> bool:
        """Returns True if the particle possesses the specified tag."""
        ...

    def add_tag(self, tag: str) -> None:
        """Assigns a tag to the particle."""
        ...

    def remove_tag(self, tag: str) -> None:
        """Removes a tag from the particle."""
        ...

    def destroy(self) -> None:
        """Destroys and removes the particle from the world scene."""
        ...

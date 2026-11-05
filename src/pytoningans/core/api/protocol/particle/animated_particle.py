from __future__ import annotations

from typing import Protocol, runtime_checkable
from .particle import IParticle


@runtime_checkable
class IAnimatedParticle(IParticle, Protocol):
    """Interface representing an AnimatedParticle."""
    frame_width: int
    frame_height: int
    frame_count: int
    fps: float
    loop: bool

    frames: list
    anim_time: float
    current_frame_index: int

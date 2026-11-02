from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from PySide6.QtCore import QPointF
    from .particle import Particle
    from .particle_manager import ParticleManager
    from .particle_emitter import ParticleEmitter
    from ..entity.base_entity import BaseEntity


type OptionalOnParticleSpawnEmitterCallback = Optional[
    Callable[[ParticleManager, Particle], Optional[ParticleEmitter]]
]

type OptionalOnParticleExpireEmitterCallback = Optional[
    Callable[[ParticleManager, QPointF], None]
]

type OptionalOnExpireCallback = Optional[Callable[[Particle], None]]

type OptionalOnHitWindowCallback = Optional[Callable[[Particle, QPointF], None]]

type OptionalOnHitEntityCallback = Optional[Callable[[Particle, BaseEntity], None]]

"""
PyToNingans Modding API - Protocols
=====================================================
Structural subtyping protocols defining the public interfaces for
particles, entities, items, and structures on the desktop.
"""

from __future__ import annotations

from .entity import (
    IBaseEntity,
    IEntity,
    IStructure,
    IItem
)

from .particle import (
    IParticle,
    IAnimatedParticle,
    IParticleManager,
    IParticleEmitter,
    ParticleConfigDTO,
    ParticleEmitterConfigDTO,
    ParticlePresets
)

from .core import (
    IEntityManager,
    IWorld,
    IModInfo
)

__all__ = [
    # Entity Protocols
    "IBaseEntity",
    "IEntity",
    "IStructure",
    "IItem",
    
    # Particle Protocols
    "IParticle",
    "IAnimatedParticle",
    "IParticleManager",
    "IParticleEmitter",
    "ParticleConfigDTO",
    "ParticleEmitterConfigDTO",
    "ParticlePresets",
    
    # Core
    "IEntityManager",
    "IWorld",
    "IModInfo"
]

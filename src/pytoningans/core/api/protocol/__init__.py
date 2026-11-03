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
    IParticleAPI,
    IParticleEmitter,
    ParticleAPI
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
    "IParticleAPI",
    "IParticleEmitter",
    "ParticleAPI",
    
    # Core
    "IEntityManager",
    "IWorld",
    "IModInfo"
]

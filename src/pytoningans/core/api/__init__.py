"""
PyToNingans Modding API Reference
=================================
Open the 'mods' folder as a workspace in VS Code for full autocompletion, type hinting, and documentation.
This package is strictly decoupled from engine internals and Qt dependencies so that it functions seamlessly
in any standalone development environment or IDE.

Modular Package Structure:
- `api.types`: Coordinates, primitives, geometry protocols, and state enums.
- `api.components`: Entity and structure component system base classes and protocols.
- `api.protocols`: Structural subtyping interfaces for entities, structures, managers, worlds, and particles.
- `api.behaviors`: Base hook classes for writing custom entity and structure AI in `behavior.py`.
"""
from __future__ import annotations

from .protocol.core import (
    IEntityManager,
    IModInfo
)

from .protocol.particle import (
    IParticle,
    IAnimatedParticle,
    IParticleManager,
    IParticleEmitter,
    ParticleConfigDTO,
    ParticleEmitterConfigDTO,
    ParticlePresets
)

from .protocol.entity import (
    IBaseEntity,
    IEntity,
    IItem,
    IStructure
)

from .types import (
    Pos2D,
    Rect2D,
    IRect,
    Colors,
    IColor,
    ColorType,
    ITexture,
    IGraphicsItem,
    TupleTextureDescriptor,
    ResolvableTexture,
    EntityType,
    EntityState,
    StructureState,
    ItemState,
    BehaviorType,
    AttackType,
    DeathAnimation,
    OptionalOnHitWindowCallback,
    OptionalOnHitEntityCallback,
    OptionalOnExpireCallback,
    OptionalOnParticleSpawnEmitterCallback,
    OptionalOnParticleExpireEmitterCallback
)

from .components import (
    IComponent,
    BaseComponent,
    ITeleportationComponent,
)

from .protocol.core import IWorld

from .behaviors import (
    BaseEntityBehavior,
    BaseStructureBehavior,
    BaseItemBehavior,
    BaseBehavior,
)

from .modpack import (
    BaseModPack,
    PackMenuAction,
)

__all__ = [
    # Core Types and Geometry
    "Pos2D",
    "Rect2D",
    "IRect",
    
    # Color Types
    "Colors",
    "IColor",
    "ColorType",
    
    # Graphical Types
    "ITexture",
    "IGraphicsItem",
    "TupleTextureDescriptor",
    "ResolvableTexture",
    
    # Enums
    "EntityType",
    "EntityState",
    "StructureState",
    "ItemState",
    "BehaviorType",
    "AttackType",
    "DeathAnimation",
    
    # Callback Types
    "OptionalOnHitWindowCallback",
    "OptionalOnHitEntityCallback",
    "OptionalOnExpireCallback",
    "OptionalOnParticleSpawnEmitterCallback",
    "OptionalOnParticleExpireEmitterCallback",
    
    # Components
    "IComponent",
    "BaseComponent",
    "ITeleportationComponent",
    
    # Engine, and World
    "IModInfo",
    "IEntityManager",
    "IWorld",
    
    # Particle Protocols
    "IParticle",
    "IAnimatedParticle",
    "IParticleManager",
    "IParticleEmitter",
    "ParticleConfigDTO",
    "ParticleEmitterConfigDTO",
    "ParticlePresets",
    
    # Entity Protocols
    "IBaseEntity",
    "IEntity",
    "IStructure",
    "IItem",
    
    # Behavior Base Classes
    "BaseEntityBehavior",
    "BaseStructureBehavior",
    "BaseItemBehavior",
    "BaseBehavior",

    # Modpacks
    "BaseModPack",
    "PackMenuAction"
]

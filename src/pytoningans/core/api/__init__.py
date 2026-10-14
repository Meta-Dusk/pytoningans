"""
PyToNingans Modding API Reference
=================================
Open the 'mods' folder as a workspace in VS Code for full autocompletion, type hinting, and documentation.
This package is strictly decoupled from engine internals and Qt dependencies so that it functions seamlessly
in any standalone development environment or IDE.

Modular Package Structure:
- `api.types`: Coordinates, primitives, geometry protocols, and state enums.
- `api.components`: Entity and structure component system base classes and protocols.
- `api.protocols`: Structural subtyping interfaces for entities, structures, managers, and worlds.
- `api.behaviors`: Base hook classes for writing custom entity and structure AI in `behavior.py`.
"""
from __future__ import annotations

# Primitives, Coordinates, and Enums
from pytoningans.core.api.types import (
    Pos2D,
    Rect2D,
    IRect,
    EntityType,
    EntityState,
    StructureState,
    BehaviorType,
    AttackType,
    DeathAnimation,
)

# Component System
from pytoningans.core.api.components import (
    IComponent,
    BaseComponent,
    ITeleportationComponent,
)

# Protocols
from pytoningans.core.api.protocols import (
    IModInfo,
    IEntityManager,
    IWorld,
    IBaseEntity,
    IEntity,
    IStructure,
)

# Behaviors
from pytoningans.core.api.behaviors import (
    BaseEntityBehavior,
    BaseStructureBehavior,
    BaseBehavior,
)

__all__ = [
    # Types & Geometry
    "Pos2D",
    "Rect2D",
    "IRect",
    
    # Enums
    "EntityType",
    "EntityState",
    "StructureState",
    "BehaviorType",
    "AttackType",
    "DeathAnimation",
    
    # Components
    "IComponent",
    "BaseComponent",
    "ITeleportationComponent",
    
    # Engine & World Protocols
    "IModInfo",
    "IEntityManager",
    "IWorld",
    
    # Entity Protocols
    "IBaseEntity",
    "IEntity",
    "IStructure",
    
    # Behavior Base Classes
    "BaseEntityBehavior",
    "BaseStructureBehavior",
    "BaseBehavior",
]


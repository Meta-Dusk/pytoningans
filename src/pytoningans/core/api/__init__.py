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
from .types import (
    Pos2D,
    Rect2D,
    IRect,
    EntityType,
    EntityState,
    StructureState,
    ItemState,
    BehaviorType,
    AttackType,
    DeathAnimation,
)

# Component System
from .components import (
    IComponent,
    BaseComponent,
    ITeleportationComponent,
)

# Protocols
from .protocols import (
    IModInfo,
    IEntityManager,
    IWorld,
    IBaseEntity,
    IEntity,
    IStructure,
    IItem,
)

# Behaviors
from .behaviors import (
    BaseEntityBehavior,
    BaseStructureBehavior,
    BaseItemBehavior,
    BaseBehavior,
)

# Modpacks
from .modpack import (
    BaseModPack,
    PackMenuAction,
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
    "ItemState",
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
    "IItem",
    
    # Behavior Base Classes
    "BaseEntityBehavior",
    "BaseStructureBehavior",
    "BaseItemBehavior",
    "BaseBehavior",

    # Modpacks
    "BaseModPack",
    "PackMenuAction",
]


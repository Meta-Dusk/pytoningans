"""
PyToNingans Modding API - Primitives, Geometry, and State Enums
==============================================================
Core data types, coordinates, and operational state enumerations
used across the PyToNingans modding engine.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable
from enum import StrEnum, unique
from dataclasses import dataclass


# =============================================================================
#* Primitives, Coordinates and Geometry
# =============================================================================

@dataclass(slots=True)
class Pos2D:
    """Represents a 2D floating-point position in the world."""
    x: float
    y: float


@dataclass(slots=True)
class Rect2D:
    """Represents a 2D rectangle in the world."""
    x: float
    y: float
    width: float
    height: float


@runtime_checkable
class IRect(Protocol):
    """Protocol for bounding boxes and hitboxes returned by scene/entity queries."""
    def x(self) -> float: ...
    def y(self) -> float: ...
    def width(self) -> float: ...
    def height(self) -> float: ...
    def left(self) -> float: ...
    def top(self) -> float: ...
    def right(self) -> float: ...
    def bottom(self) -> float: ...
    def isEmpty(self) -> bool: ...
    def isNull(self) -> bool: ...
    def intersects(self, other: IRect) -> bool: ...
    def contains(self, x: float, y: float) -> bool: ...


# =============================================================================
#* State and Configuration Enums
# =============================================================================

@unique
class EntityType(StrEnum):
    """Declared archetype of a mod item."""
    ENTITY = "entity"
    STRUCTURE = "structure"
    ITEM = "item"


@unique
class ItemState(StrEnum):
    """Operational and animation states for items."""
    IDLE = "idle"
    HELD = "held"
    DROPPED = "dropped"
    USED = "used"


@unique
class EntityState(StrEnum):
    """Engine animation and behavior states for living entities."""
    IDLE = "idle"
    DRAG = "drag"
    CLICKED = "clicked"
    INTERACT = "interact"
    MOVING = "moving"
    JUMPING = "jumping"
    CLIMBING = "climbing"
    DYING = "dying"
    REVIVING = "reviving"
    ATTACK = "attack"


@unique
class StructureState(StrEnum):
    """Operational states for environmental structures."""
    IDLE = "idle"
    ACTIVE = "active"
    OPEN = "open"


@unique
class BehaviorType(StrEnum):
    """Default AI brain combat and targeting disposition."""
    PASSIVE = "passive"
    NEUTRAL = "neutral"
    HOSTILE = "hostile"


@unique
class AttackType(StrEnum):
    """Determines target count and splash calculations for combat."""
    SINGLE = "single"
    AOE = "aoe"
    MULTI = "multi"


@unique
class DeathAnimation(StrEnum):
    """Animation style triggered when an entity dies."""
    SPRITE = "sprite"
    ROTATE_LEFT = "rotate_left"
    ROTATE_RIGHT = "rotate_right"
    ROTATE_LEFT_OR_RIGHT = "rotate_left_or_right"


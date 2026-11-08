"""
PyToNingans Modding API - Primitives, Geometry, and State Enums
==============================================================
Core data types, coordinates, and operational state enumerations
used across the PyToNingans modding engine.
"""
from __future__ import annotations

from typing import (
    TYPE_CHECKING, Protocol, runtime_checkable, Optional, Callable, Any,
    overload, Union, Self
)
from enum import StrEnum, unique, IntEnum
from dataclasses import dataclass, fields

if TYPE_CHECKING:
    from .protocol import IParticle, IBaseEntity, IParticleEmitter


# =============================================================================
#* Primitives, Coordinates and Geometry
# =============================================================================

@dataclass(slots=True)
class Pos2D:
    """Represents a 2D floating-point position in the world."""
    x: float = 0.0
    y: float = 0.0
    
    def __iter__(self):
        return iter(tuple(getattr(self, field.name) for field in fields(self)))

    def __add__(self, other: Pos2D) -> Self:
        return type(self)(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Pos2D) -> Self:
        return type(self)(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Self:
        return type(self)(self.x * scalar, self.y * scalar)
    
    def distance_to(self, other: Pos2D) -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


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
#* Color Types
# =============================================================================

class Colors(IntEnum):
    """
    Contains preset colors. This enum class is also just a direct copy-paste from
    the internal global colors available.
    """
    color0        = 0x0
    """Placeholder color? Might remove in the future."""
    color1        = 0x1
    """Placeholder color? Might remove in the future."""
    black         = 0x2
    white         = 0x3
    darkGray      = 0x4
    gray          = 0x5
    lightGray     = 0x6
    red           = 0x7
    green         = 0x8
    blue          = 0x9
    cyan          = 0xa
    magenta       = 0xb
    yellow        = 0xc
    darkRed       = 0xd
    darkGreen     = 0xe
    darkBlue      = 0xf
    darkCyan      = 0x10
    darkMagenta   = 0x11
    darkYellow    = 0x12
    transparent   = 0x13


@runtime_checkable
class IColor(Protocol):
    """Represents a color object."""    
    @overload
    def __init__(self, r: int, g: int, b: int, /, a: int = ...) -> None:
        """A Color instance made with RGBA values.

        Args:
            r (int): Red value
            g (int): Green value
            b (int): Blue value
            a (int, optional): Alpha (Transparency). Defaults to ....
        """
        ...
    
    @overload
    def __init__(self, color: Colors, /) -> None:
        """A Color instance made with a preset color.

        Args:
            color (Colors): Each member from `Colors` has value of type `int`.
        """
        ...


type ColorType = Union[IColor, Colors, str]


# =============================================================================
#* Abstract Graphical Representations
# =============================================================================

@runtime_checkable
class ITexture(Protocol):
    """Interface representing a renderable image."""
    ...


@runtime_checkable
class IGraphicsItem(Protocol):
    """Interface representing a graphics item used internally."""
    def x(self) -> float: ...
    def y(self) -> float: ...


type TupleTextureDescriptor = tuple[str, *tuple[Any, ...]]

type ResolvableTexture = Union[ITexture, str, TupleTextureDescriptor]
"""
You can procedurally create textures by passing in either a tuple or a string.
Refer to the explanations below:

### Syntax

**shape** : _str_\n
    Choose between: "dot, square, ring, glow_circle, or glow."
**radius** : _int_
**size** : _int_
**color** : _ColorType_\n
    Can be of type `IColor`, `str`, or `Colors`.
**core_color** : _ColorType_
**outer_color** : _ColorType_

### Formatting

Passing a `tuple` will need the first member as the **shape**.
You can omit the rest, which will have defaults.\n
The following possible formats are (with **shape** filled in):\n
**("dot", radius, color)**; defaults to `radius=6, color="white"`\n
**("square", size, color)**; defaults to `size=10, color="white"`\n
**("ring", radius, color)**; defaults to `radius=10, color="white"`\n
**("glow_circle" or "glow", size, core_color, outer_color)**; defaults to\n
`size=15, core_color="white", outer_color="transparent"`\n\n

An alternative is a oneline string, that is colon-separated. Except, it must start
with 'procedural:'.\n
`"procedural:dot:radius:color"`\n
`"procedural:square:shape:color"`\n
`"procedural:ring:radius:color"`\n
`"procedural:glow_circle:radius:core_color:outer_color"`\n
`"procedural:glow:radius:core_color:outer_color"`\n
"""


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


# =============================================================================
#* Particle System Callbacks
# =============================================================================

type OptionalOnHitWindowCallback = Optional[Callable[[IParticle, Pos2D], None]]
type OptionalOnHitEntityCallback = Optional[Callable[[IParticle, IBaseEntity], None]]
type OptionalOnExpireCallback = Optional[Callable[[IParticle], None]]
type OptionalOnParticleExpireEmitterCallback = Optional[Callable[[Any, Pos2D], None]]
type OptionalOnParticleSpawnEmitterCallback = Optional[Callable[[Any, IParticle], Optional[IParticleEmitter]]]


"""
PyToNingans Modding API Reference
Open the 'mods' folder as a workspace in VS Code for full autocompletion.
"""
from __future__ import annotations
from typing import Protocol, Optional, Any, runtime_checkable
from enum import StrEnum, unique
from dataclasses import dataclass

# --- Primitives & Enums ---

@dataclass
class Pos2D:
    x: float
    y: float

@dataclass
class Rect2D:
    x: float
    y: float
    width: float
    height: float

@unique
class EntityState(StrEnum):
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
    IDLE = "idle"
    ACTIVE = "active"
    OPEN = "open"

@unique
class BehaviorType(StrEnum):
    PASSIVE = "passive"
    NEUTRAL = "neutral"
    HOSTILE = "hostile"

@unique
class AttackType(StrEnum):
    SINGLE = "single"
    AOE = "aoe"
    MULTI = "multi"

@unique
class DeathAnimation(StrEnum):
    SPRITE = "sprite"
    ROTATE_LEFT = "rotate_left"
    ROTATE_RIGHT = "rotate_right"
    ROTATE_LEFT_OR_RIGHT = "rotate_left_or_right"

# --- Component Protocols & Base ---

@runtime_checkable
class IComponent(Protocol):
    name: str
    enabled: bool
    owner: Optional[IBaseEntity]

    def on_attach(self) -> None: ...
    def update(self, dt: int) -> None: ...
    def on_detach(self) -> None: ...

class BaseComponent:
    """Base class for writing custom mod components in pure Python."""
    name: str = "custom"

    def __init__(self, owner: Optional[IBaseEntity] = None) -> None:
        self.owner: Optional[IBaseEntity] = owner
        self.enabled: bool = True

    def on_attach(self) -> None: pass
    def update(self, dt: int) -> None: pass
    def on_detach(self) -> None: pass

@runtime_checkable
class ITeleportationComponent(Protocol):
    name: str
    enabled: bool
    target_world: Any
    linked_portal: Optional[IStructure]
    exit_offset_x: float
    exit_offset_y: float

    def teleport_entity(self, entity: IEntity) -> None: ...

# --- Entity & World Protocols ---

@runtime_checkable
class IBaseEntity(Protocol):
    mod_manager: Any
    world: Any
    state: Any | str
    facing_left: bool
    sprite_rotation: float
    velocity_y: float
    components: dict[str, Any]

    def x(self) -> float: ...
    def y(self) -> float: ...
    def setPos(self, x: float, y: float) -> None: ...
    def move(self, x: float, y: float) -> None: ...
    def width(self) -> int: ...
    def height(self) -> int: ...
    def toFront(self) -> None: ...
    def destroy(self) -> None: ...

    # Component API
    def add_component(self, component: Any) -> Any: ...
    def get_component(self, name: str) -> Optional[Any]: ...
    def has_component(self, name: str) -> bool: ...
    def remove_component(self, name: str) -> Optional[Any]: ...

@runtime_checkable
class IEntity(IBaseEntity, Protocol):
    state: EntityState
    is_dead: bool
    current_health: int
    target_pos: Optional[Pos2D]
    behavior_type: BehaviorType
    entity_manager: Any

    def jump(self) -> None: ...
    def take_damage(self, amount: int) -> None: ...
    def die(self) -> None: ...
    def revive(self) -> None: ...
    def force_talk(self) -> None: ...

@runtime_checkable
class IStructure(IBaseEntity, Protocol):
    state: StructureState

    def attach_teleportation(
        self,
        target_world: Optional[Any] = None,
        exit_offset_x: float = 80.0,
        exit_offset_y: float = 0.0
    ) -> ITeleportationComponent: ...

# --- Behaviors ---

class BaseEntityBehavior:
    """Inherit from this class in your pet's behavior.py."""
    def on_spawn(self, entity: IEntity) -> None: pass
    def on_update(self, entity: IEntity, dt: int) -> None: pass
    def on_decision_tick(self, entity: IEntity) -> bool: return False
    def on_interact(self, entity: IEntity, other_entity: IEntity) -> bool: return False
    def on_death(self, entity: IEntity) -> None: pass
    def on_revive(self, entity: IEntity) -> None: pass
    def on_attack(self, entity: IEntity, target: IEntity) -> bool: return False

class BaseStructureBehavior:
    """Inherit from this class in your structure's behavior.py."""
    def on_spawn(self, structure: IStructure) -> None: pass
    def on_update(self, structure: IStructure, dt: int) -> None: pass
    def on_interact(self, structure: IStructure, entity: IEntity) -> None: pass

type BaseBehavior = BaseEntityBehavior | BaseStructureBehavior
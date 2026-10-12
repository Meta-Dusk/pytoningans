"""
PyToNingans Modding API Reference
=================================
Open the 'mods' folder as a workspace in VS Code for full autocompletion, type hinting, and documentation.
This module is strictly decoupled from engine internals and Qt dependencies so that it functions seamlessly
in any standalone development environment or IDE.
"""
from __future__ import annotations
from typing import Protocol, Optional, Union, runtime_checkable
from enum import StrEnum, unique
from dataclasses import dataclass


# =============================================================================
# Primitives, Coordinates & Geometry
# =============================================================================

@dataclass
class Pos2D:
    """Represents a 2D floating-point position in the world."""
    x: float
    y: float


@dataclass
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
# State & Configuration Enums
# =============================================================================

@unique
class EntityType(StrEnum):
    """Declared archetype of a mod item."""
    PET = "pet"
    STRUCTURE = "structure"


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
# Component System
# =============================================================================

@runtime_checkable
class IComponent(Protocol):
    """Protocol representing a reusable entity component."""
    name: str
    enabled: bool
    owner: Optional[IBaseEntity]

    def on_attach(self) -> None:
        """Invoked when the component is bound to an entity."""
        ...

    def update(self, dt: int) -> None:
        """Invoked every engine tick (dt in milliseconds)."""
        ...

    def on_detach(self) -> None:
        """Invoked when the component is removed from an entity."""
        ...


class BaseComponent:
    """Base class for writing custom mod components in pure Python."""
    name: str = "custom"

    def __init__(self, owner: Optional[IBaseEntity] = None) -> None:
        self.owner: Optional[IBaseEntity] = owner
        self.enabled: bool = True

    def on_attach(self) -> None:
        """Called immediately after being attached to an owner entity."""
        pass

    def update(self, dt: int) -> None:
        """Called every frame update with the delta time in milliseconds."""
        pass

    def on_detach(self) -> None:
        """Called when the component is removed or the owner is destroyed."""
        pass


@runtime_checkable
class ITeleportationComponent(IComponent, Protocol):
    """Protocol for structures capable of teleporting entities across worlds."""
    target_world: Optional[IWorld]
    linked_portal: Optional[IStructure]
    exit_offset_x: float
    exit_offset_y: float

    def teleport_entity(self, entity: IEntity) -> None:
        """Transports the specified entity to the target world or linked structure."""
        ...


# =============================================================================
# Engine, Manager & World Protocols
# =============================================================================

@runtime_checkable
class IModInfo(Protocol):
    """Metadata and runtime configuration for a loaded mod."""
    current_mod_name: str
    current_mod_folder: str
    entity_type: str
    max_health: int
    attack_damage: int
    attack_range: int
    jump_height: int
    can_fly: bool
    behavior_type: BehaviorType
    attack_type: AttackType
    plain_dialogue: list[str]
    death_animation: DeathAnimation
    auto_close_on_death: bool


@runtime_checkable
class IEntityManager(Protocol):
    """Global entity coordinator across all active monitor screens."""
    active_worlds: list[IWorld]
    active_entities: list[IEntity]
    active_structures: list[IStructure]

    def spawn_entity(
        self,
        x: float,
        y: float,
        mod_folder: str,
        target_world: Optional[IWorld] = None
    ) -> None:
        """Spawns an entity or structure into the game world."""
        ...

    def remove_entity(self, entity: IBaseEntity) -> None:
        """Removes an entity or structure from all tracking and world scenes."""
        ...


@runtime_checkable
class IWorld(Protocol):
    """Represents a fullscreen monitor overlay containing active entities."""
    manager: IEntityManager
    active_entities: list[IEntity]
    active_structures: list[IStructure]


# =============================================================================
# Entity & Structure Protocols
# =============================================================================

@runtime_checkable
class IBaseEntity(Protocol):
    """Foundational interface for all entities and structures rendered on desktop."""
    mod_manager: Optional[IModInfo]
    world: Optional[IWorld]
    facing_left: bool
    sprite_rotation: float
    velocity_y: float
    components: dict[str, IComponent]

    @property
    def state(self) -> str:
        """Returns the current state string of the entity."""
        ...

    @state.setter
    def state(self, value: Union[str, EntityState, StructureState]) -> None:
        """Transitions the entity to a new state, updating animation and callbacks."""
        ...

    def x(self) -> float:
        """Current X coordinate in world scene space."""
        ...

    def y(self) -> float:
        """Current Y coordinate in world scene space."""
        ...

    def setPos(self, x: float, y: float) -> None:
        """Directly positions the entity in world scene space."""
        ...

    def move(self, x: float, y: float) -> None:
        """Alias for setPos(x, y)."""
        ...

    def width(self) -> int:
        """Current pixel width of the entity's visual bounding box."""
        ...

    def height(self) -> int:
        """Current pixel height of the entity's visual bounding box."""
        ...

    def toFront(self) -> None:
        """Brings the entity forward in the scene visual stacking order."""
        ...

    def destroy(self) -> None:
        """Removes the entity from the world, detaches components, and cleans up memory."""
        ...

    def flip(self) -> None:
        """Toggles horizontal facing direction and horizontally mirrors collision hitboxes."""
        ...

    def sceneBoundingRect(self) -> IRect:
        """Returns the absolute scene bounding box of the entity."""
        ...

    # Component Management
    def add_component(self, component: IComponent) -> IComponent:
        """Attaches and registers a component to this entity."""
        ...

    def get_component(self, name: str) -> Optional[IComponent]:
        """Retrieves an attached component by name, or None if not present."""
        ...

    def has_component(self, name: str) -> bool:
        """Checks if a component with the specified name is attached."""
        ...

    def remove_component(self, name: str) -> Optional[IComponent]:
        """Detaches and returns the component with the given name, or None."""
        ...


@runtime_checkable
class IEntity(IBaseEntity, Protocol):
    """Living desktop pet entity with health, AI, combat, and dialogue."""
    is_dead: bool
    current_health: int
    target_pos: Optional[Pos2D]
    behavior_type: BehaviorType
    entity_manager: Optional[IEntityManager]

    def jump(self) -> None:
        """Causes the entity to jump upwards if grounded."""
        ...

    def take_damage(self, amount: int) -> None:
        """Inflicts damage on the entity, flashing tint effect and triggering death if depleted."""
        ...

    def heal(self, amount: int) -> None:
        """Restores health up to max health, updating health indicators and visuals."""
        ...

    def die(self) -> None:
        """Triggers the entity's death sequence and animations."""
        ...

    def revive(self) -> None:
        """Restores health to max and revives the entity to an idle state."""
        ...

    def force_talk(self) -> None:
        """Displays a random line from the mod's plain dialogue pool."""
        ...

    def say(self, text: str, duration_ms: int = 4000) -> None:
        """Displays a speech bubble with the given text for duration_ms milliseconds."""
        ...


@runtime_checkable
class IStructure(IBaseEntity, Protocol):
    """Environmental structure or portal on the desktop."""
    def toggle_active(self) -> None:
        """Toggles the structure between IDLE and ACTIVE operational states."""
        ...

    def attach_teleportation(
        self,
        target_world: Optional[IWorld] = None,
        exit_offset_x: float = 80.0,
        exit_offset_y: float = 0.0
    ) -> ITeleportationComponent:
        """Attaches a TeleportationComponent configuring this structure as a travel portal."""
        ...


# =============================================================================
# Behavior Base Classes & Modding Hooks
# =============================================================================

class BaseEntityBehavior:
    """
    Inherit from this class in your pet's `behavior.py`.
    Override any of the hook methods below to implement custom AI logic, interactions,
    combat rules, or dialogue responses.
    """
    def on_spawn(self, entity: IEntity) -> None:
        """Called once when the entity is instantiated and placed in a world."""
        pass

    def on_update(self, entity: IEntity, dt: int) -> None:
        """Called every frame tick. Use for real-time timers and state monitoring."""
        pass

    def on_decision_tick(self, entity: IEntity) -> bool:
        """
        Called when the engine's AI brain evaluates a wander or action decision.
        Return True to override default engine movement/action behavior.
        """
        return False

    def on_interact(self, entity: IEntity, other_entity: IEntity) -> bool:
        """
        Called when this entity collides with or approaches another living entity.
        Return True to override the default social interaction.
        """
        return False

    def on_speak(self, entity: IEntity, text: str) -> None:
        """Called whenever this entity speaks dialogue via say() or force_talk()."""
        pass

    def on_damage(self, entity: IEntity, amount: int) -> None:
        """Called when the entity takes damage."""
        pass

    def on_death(self, entity: IEntity) -> None:
        """Called immediately after the entity's health drops to 0."""
        pass

    def on_revive(self, entity: IEntity) -> None:
        """Called when the entity is revived from death."""
        pass

    def on_attack(self, entity: IEntity, target: IEntity) -> bool:
        """
        Called when the entity initiates an attack against target.
        Return True to override engine combat resolution.
        """
        return False

    def on_state_change(self, entity: IEntity, old_state: str, new_state: str) -> None:
        """Called whenever the entity's state changes (e.g. idle -> moving)."""
        pass


class BaseStructureBehavior:
    """
    Inherit from this class in your structure's `behavior.py`.
    Override hook methods below to implement custom structure activations, portal logic,
    and pet interaction triggers.
    """
    def on_spawn(self, structure: IStructure) -> None:
        """Called once when the structure is placed in a world. Ideal for attaching components."""
        pass

    def on_update(self, structure: IStructure, dt: int) -> None:
        """Called every frame tick."""
        pass

    def on_interact(self, structure: IStructure, entity: IEntity) -> None:
        """Called when a living entity overlaps or touches this structure."""
        pass

    def on_state_change(self, structure: IStructure, old_state: str, new_state: str) -> None:
        """Called when the structure's operational state changes (e.g. idle <-> active)."""
        pass

    def on_destroy(self, structure: IStructure) -> None:
        """Called when the structure is removed or closed."""
        pass


type BaseBehavior = BaseEntityBehavior | BaseStructureBehavior
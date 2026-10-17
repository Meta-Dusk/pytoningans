"""
PyToNingans Modding API - Engine and Entity Protocols
=====================================================
Structural subtyping protocols defining the public interfaces for
worlds, entity managers, entities, and structures on the desktop.
"""
from __future__ import annotations

from typing import Protocol, Optional, Union, runtime_checkable

from .types import (
    Pos2D, IRect, EntityState, StructureState, ItemState, BehaviorType, AttackType, DeathAnimation
)
from .components import IComponent, ITeleportationComponent


# =============================================================================
#* Engine, Manager and World Protocols
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
    move_speed: float
    regen_rate: float
    can_fly: bool
    can_climb_walls: bool
    can_move_windows: bool
    window_move_mode: str
    ignore_window_physics: bool
    behavior_type: BehaviorType
    attack_type: AttackType
    plain_dialogue: list[str]
    death_dialogue: list[str]
    death_animation: DeathAnimation
    auto_close_on_death: bool
    instance_names: list[str]


@runtime_checkable
class IEntityManager(Protocol):
    """Global entity coordinator across all active monitor screens."""
    active_worlds: list[IWorld]
    active_entities: list[IEntity]
    active_structures: list[IStructure]
    active_items: list[IItem]

    def spawn_entity(
        self,
        x: float,
        y: float,
        mod_folder: str,
        target_world: Optional[IWorld] = None,
        instance_name: Optional[str] = None
    ) -> Optional[IBaseEntity]:
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
    active_items: list[IItem]
    active_window_rects: list[IRect]

    def move_window(self, win_rect: IRect, dx: int, dy: int) -> bool:
        """Moves the desktop window associated with win_rect by (dx, dy) pixels."""
        ...


# =============================================================================
#* Entity & Structure Protocols
# =============================================================================

@runtime_checkable
class IBaseEntity(Protocol):
    """Foundational interface for all entities and structures rendered on desktop."""
    mod_manager: Optional[IModInfo]
    world: Optional[IWorld]
    facing_left: bool
    sprite_rotation: float
    velocity_y: float
    move_speed: float
    can_climb_walls: bool
    can_move_windows: bool
    ignore_window_physics: bool
    should_use_window_physics: bool
    is_climbing: bool
    is_cursor_grabbed: bool
    is_following_cursor: bool
    components: dict[str, IComponent]

    @property
    def state(self) -> str:
        """Returns the current state string of the entity."""
        ...

    @state.setter
    def state(self, value: Union[str, EntityState, StructureState, ItemState]) -> None:
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

    def move_window(self, win: IRect, dx: int, dy: int) -> bool:
        """Moves the specified desktop window by (dx, dy) pixels."""
        ...

    #? Cursor Interaction API
    def get_cursor_pos(self) -> tuple[float, float]:
        """Returns the current OS mouse cursor position mapped into this entity's world scene coordinates."""
        ...

    def get_global_cursor_pos(self) -> tuple[int, int]:
        """Returns the current OS mouse cursor coordinates in virtual desktop space."""
        ...

    def set_cursor_pos(self, scene_x: float, scene_y: float) -> None:
        """Moves the OS mouse cursor to the given position in world scene coordinates."""
        ...

    def grab_cursor(
        self,
        offset_x: Optional[int] = None,
        offset_y: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Grabs the OS mouse cursor, locking it to the entity's position (+ offset) as it moves."""
        ...

    def release_cursor(self) -> None:
        """Releases the OS mouse cursor if currently grabbed by this entity."""
        ...

    def follow_cursor(self, enabled: bool = True, min_distance: float = 30.0) -> None:
        """Configures the entity to automatically follow / pathfind towards the mouse cursor."""
        ...

    #? Component Management
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

    is_force_idle: bool
    is_physics_enabled: bool
    is_hovered: bool
    is_dragged: bool
    is_interactable: bool
    instance_name: Optional[str]
    display_name: str
    identification: str

    def set_force_idle(self, enabled: bool) -> None:
        """Toggles force-idle state where the entity plays idle animations but disables AI and gravity."""
        ...

    def set_instance_name(self, name: Optional[str]) -> None:
        """Sets a unique instance name for this entity."""
        ...

    def update_tooltip(self) -> None:
        """Updates the item tooltip to match its entity identification."""
        ...

    #? Entity Tags
    tags: set[str]

    def has_tag(self, tag: str) -> bool:
        """Returns True if the entity has the specified tag (case-insensitive)."""
        ...

    def has_all_tags(self, *tags: str) -> bool:
        """Returns True if the entity contains every specified tag."""
        ...

    def has_any_tag(self, *tags: str) -> bool:
        """Returns True if the entity contains at least one of the specified tags."""
        ...

    def add_tag(self, tag: str) -> None:
        """Dynamically adds a tag to the entity at runtime."""
        ...

    def remove_tag(self, tag: str) -> None:
        """Removes a tag from the entity at runtime."""
        ...


@runtime_checkable
class IEntity(IBaseEntity, Protocol):
    """Living desktop entity with health, AI, combat, and dialogue."""
    is_dead: bool
    current_health: int
    regen_rate: float
    target_pos: Optional[Pos2D]
    behavior_type: BehaviorType
    entity_manager: Optional[IEntityManager]
    held_item: Optional[IItem]

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

    def say(self, text: str, duration_ms: int = 4000, is_death: bool = False) -> None:
        """Displays a speech bubble with the given text for duration_ms milliseconds."""
        ...

    def pick_up(self, item: IItem) -> bool:
        """Picks up an item if one is not already held."""
        ...

    def drop_item(self) -> Optional[IItem]:
        """Drops the currently held item."""
        ...

    def use_item(self) -> bool:
        """Uses the currently held item."""
        ...


@runtime_checkable
class IStructure(IBaseEntity, Protocol):
    """Environmental structure or portal on the desktop."""
    def toggle_active(self) -> None:
        """Toggles the structure between IDLE and ACTIVE operational states."""
        ...

    def toggle_physics(self) -> None:
        """Toggles whether the structure is affected by gravity."""
        ...

    def set_physics_enabled(self, enabled: bool) -> None:
        """Sets whether the structure is affected by gravity."""
        ...

    def attach_teleportation(
        self,
        target_world: Optional[IWorld] = None,
        exit_offset_x: float = 80.0,
        exit_offset_y: float = 0.0
    ) -> ITeleportationComponent:
        """Attaches a TeleportationComponent configuring this structure as a travel portal."""
        ...


@runtime_checkable
class IItem(IBaseEntity, Protocol):
    """Interactable item object on desktop that can be picked up, dropped, and used."""
    holder: Optional[IEntity]
    is_held: bool

    def pick_up(self, entity: IEntity) -> bool:
        """Picks up this item by the specified living entity."""
        ...

    def drop(self, entity: Optional[IEntity] = None) -> None:
        """Drops this item onto the ground/desktop."""
        ...

    def use(self, entity: Optional[IEntity] = None) -> bool:
        """Uses this item (invoking custom behavior hook or triggering interaction)."""
        ...


from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, Union, runtime_checkable

if TYPE_CHECKING:
    from ...components import IComponent
    from ..core import IWorld, IModInfo
    from ...types import EntityState, IRect, ItemState, StructureState, Pos2D


@runtime_checkable
class IBaseEntity(Protocol):
    """Foundational interface for all entities and structures rendered on desktop."""
    mod_manager: Optional[IModInfo]
    world: Optional[IWorld]
    facing_left: bool
    sprite_rotation: float
    velocity_y: float
    move_speed: float
    fade_in_on_spawn: bool
    can_climb_walls: bool
    can_move_windows: bool
    ignore_window_physics: bool
    should_use_window_physics: bool
    is_climbing: bool
    is_cursor_grabbed: bool
    is_following_cursor: bool
    target_pos: Optional[Pos2D]
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

    def fade_in(self, duration_ms: int = 1000) -> None:
        """Smoothly fades in the entity from current opacity to 1.0."""
        ...

    def fade_out(self, duration_ms: int = 1000, destroy_on_complete: bool = False) -> None:
        """Smoothly fades out the entity from current opacity to 0.0."""
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
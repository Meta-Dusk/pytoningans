from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Literal
from PySide6.QtCore import QPointF, QRect

from pytoningans.core.constants import EntityState
from .gravity import tick_gravity_and_collisions
from .helpers import get_effective_hitbox
from .movement import tick_movement
from .repulsion import apply_soft_repulsion

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity
    from pytoningans.core.mod_manager import ModManager


type _ClimbingSide = Literal["left", "right"] | str

class PhysicsSystem:
    """
    Manages translation, gravity, platform landing, window collisions,
    wall climbing, and repulsion for entities.
    """

    def __init__(self, entity: Optional[BaseEntity] = None) -> None:
        self.entity = entity
        self.gravity: float = 0.8
        mod_manager: Optional[ModManager] = entity.mod_manager if entity is not None else None
        if mod_manager is not None:
            self.move_speed: float = mod_manager.move_speed
        self.current_platform_rect: Optional[QRect] = None
        self.is_climbing: bool = False
        self.climbing_window: Optional[QRect] = None
        self.climbing_side: _ClimbingSide = ""

    def update(self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None) -> None:
        """Processes physics calculations based on elapsed time."""
        if self.entity is None or self.entity.world is None:
            return
        if not self.entity.locks.physics:
            if self.is_climbing:
                self.stop_climb()
            self.entity.velocity_y = 0.0
            return

        is_dead: bool = getattr(self.entity, "is_dead", False)
        if is_dead:
            if self.is_climbing:
                self.stop_climb()
            return

        time_scale: float = dt / 16.0

        if self.is_climbing:
            self._tick_climb(time_scale)
            return

        ground_y: float = self.entity.world.scene.sceneRect().bottom()
        current_gravity: float = self.gravity * time_scale
        current_move_speed: float = self.move_speed * time_scale

        self._tick_gravity_and_collisions(ground_y, current_gravity)

        is_dead = getattr(self.entity, "is_dead", False)
        if is_dead: return

        self._tick_soft_collision(current_move_speed, centers)
        self._tick_movement(current_move_speed)

    def start_climb(self, win: QRect, side: _ClimbingSide) -> None:
        """Initiates wall climbing along the vertical edge of a window."""
        if self.entity is None or self.entity.anim_sys is None:
            return
        self.is_climbing = True
        self.climbing_window = win
        self.climbing_side = side
        self.current_platform_rect = None
        self.entity.velocity_y = 0.0
        self.entity.target_pos = None

        self.entity.facing_left = False if side == "left" else True
        self.entity.sprite_rotation = -90.0

        self.entity.anim_sys.set_state(EntityState.CLIMBING)
        self.entity.anim_sys.refresh_frame()

        hitbox: QRect = get_effective_hitbox(self.entity)
        if side == "left":
            aligned_x = float(win.left() - hitbox.x() - hitbox.width())
        else:
            aligned_x = float(win.right() - hitbox.x())
        self.entity.setPos(aligned_x, self.entity.y())

    def stop_climb(self) -> None:
        """Cancels wall climbing, restoring normal rotation and gravity."""
        self.is_climbing = False
        self.climbing_window = None
        self.climbing_side = ""
        if self.entity is None: return
        
        self.entity.sprite_rotation = 0.0
        if self.entity.anim_sys is None: return
        
        self.entity.anim_sys.refresh_frame()
        if self.entity.state == EntityState.CLIMBING:
            self.entity.anim_sys.set_state(EntityState.IDLE)

    def _tick_climb(self, time_scale: float) -> None:
        """Processes vertical climbing movement along a window wall."""
        if (
            self.entity is None or
            self.entity.world is None or
            self.entity.anim_sys is None or
            self.climbing_window is None
        ):
            self.stop_climb()
            return

        window_rects: list[QRect] = self.entity.world.active_window_rects
        active_win: Optional[QRect] = None
        for win in window_rects:
            if win == self.climbing_window or win.intersects(self.climbing_window):
                active_win = win
                break

        if active_win is None:
            self.stop_climb()
            return

        self.climbing_window = active_win
        climb_step: float = self.move_speed * 1.0 * time_scale
        new_y: float = self.entity.y() - climb_step

        hitbox: QRect = get_effective_hitbox(self.entity)

        if self.climbing_side == "left":
            new_x = float(active_win.left() - hitbox.x() - hitbox.width())
        else:
            new_x = float(active_win.right() - hitbox.x())

        # If at the very top of monitor, stop climbing
        if new_y + hitbox.y() <= 0:
            self.stop_climb()
            return

        # Check if reached top roof / ledge of window
        entity_top: float = new_y + hitbox.y()
        if entity_top <= active_win.top() + 4:
            climbing_side = self.climbing_side
            self.is_climbing = False
            self.climbing_window = None
            self.climbing_side = ""
            self.entity.sprite_rotation = 0.0
            self.entity.velocity_y = 0.0
            self.entity.anim_sys.refresh_frame()
            self.entity.target_pos = None

            upright_hitbox: QRect = get_effective_hitbox(self.entity)
            hitbox_bottom_offset: int = upright_hitbox.y() + upright_hitbox.height()
            roof_y: float = float(active_win.top() - hitbox_bottom_offset)

            if climbing_side == "left":
                roof_x = float(active_win.left() - upright_hitbox.x() + 8)
                self.entity.facing_left = False
            else:
                roof_x = float(active_win.right() - upright_hitbox.x() - upright_hitbox.width() - 8)
                self.entity.facing_left = True

            self.entity.setPos(roof_x, roof_y)
            self.current_platform_rect = active_win
            self.entity.anim_sys.set_state(EntityState.IDLE)
            return

        self.entity.setPos(new_x, new_y)

    def _tick_soft_collision(
        self, current_move_speed: float, centers: Optional[dict[BaseEntity, QPointF]] = None
    ) -> None:
        """Gently repels overlapping entities to prevent dense clustering."""
        if self.entity is not None:
            apply_soft_repulsion(self.entity, current_move_speed, centers)

    def _tick_movement(self, current_move_speed: float) -> None:
        """Computes movement towards target position."""
        if self.entity is not None:
            tick_movement(self.entity, current_move_speed)

    def _tick_gravity_and_collisions(self, ground_y: float, current_gravity: float) -> None:
        """Performs gravity, collision resolution, and platform detection."""
        tick_gravity_and_collisions(self, ground_y, current_gravity)



from __future__ import annotations

from typing import TYPE_CHECKING, Optional, cast

from PySide6.QtCore import QRect, QRectF
from pytoningans.core.settings import SettingsManager

if TYPE_CHECKING:
    from pytoningans.core.mod_manager import ModManager
    from pytoningans.core.world import WorldOverlay
    from pytoningans.core.entity.physics import PhysicsSystem
    from pytoningans.core.entity.base_entity import BaseEntity


class EntityWindowMixin:
    """Encapsulates desktop window interaction, climbing checks, and window drop seating."""

    _ignore_window_physics_override: Optional[bool]
    mod_manager: Optional[ModManager]
    world: Optional[WorldOverlay]
    physics_sys: Optional[PhysicsSystem]
    current_hitbox: QRect
    velocity_y: float

    def _entity(self) -> BaseEntity:
        return cast("BaseEntity", self)

    def _init_window_physics(self) -> None:
        self._ignore_window_physics_override = None

    @property
    def can_climb_walls(self) -> bool:
        """Returns True if the entity is configured to climb desktop window walls."""
        if self.mod_manager is not None:
            return getattr(self.mod_manager, "can_climb_walls", False)
        return False

    @property
    def can_move_windows(self) -> bool:
        """Returns True if the entity is configured to push or attack desktop windows."""
        if self.mod_manager is not None:
            return getattr(self.mod_manager, "can_move_windows", False)
        return False

    def move_window(self, win: QRect, dx: int, dy: int) -> bool:
        """Moves the desktop window by (dx, dy) pixels."""
        if self.world is not None:
            return self.world.move_window(win, dx, dy)
        return False

    @property
    def ignore_window_physics(self) -> bool:
        """Returns True if this entity is configured to ignore desktop window physics."""
        if self._ignore_window_physics_override is not None:
            return self._ignore_window_physics_override
        if self.mod_manager is not None:
            return getattr(self.mod_manager, "ignore_window_physics", False)
        return False

    @ignore_window_physics.setter
    def ignore_window_physics(self, value: Optional[bool]) -> None:
        self._ignore_window_physics_override = value

    @property
    def should_use_window_physics(self) -> bool:
        """Returns True if desktop window physics should affect this entity."""
        if self.ignore_window_physics:
            return False
        return SettingsManager.get().settings.enable_window_physics

    @property
    def is_climbing(self) -> bool:
        """Returns True if the entity is currently climbing a window wall."""
        if self.physics_sys is not None:
            return self.physics_sys.is_climbing
        return False

    def _check_window_drop_seat(self) -> None:
        """
        If dropped onto or inside an active desktop window,
        seat entity on the window's top ledge.
        """
        if self.world is None or not self.should_use_window_physics:
            return

        window_rects: list[QRect] = self.world.active_window_rects
        if not window_rects:
            return

        entity: BaseEntity = self._entity()
        hitbox: QRect = self.current_hitbox
        if hitbox.width() <= 0 or hitbox.height() <= 0:
            b_rect: QRectF = entity.boundingRect()
            bw: int = int(b_rect.width()) if b_rect.width() > 0 else 50
            bh: int = int(b_rect.height()) if b_rect.height() > 0 else 50
            hitbox = QRect(0, 0, bw, bh)

        scene_box = QRect(
            int(entity.x() + hitbox.x()),
            int(entity.y() + hitbox.y()),
            hitbox.width(),
            hitbox.height(),
        )

        for win in window_rects:
            if not scene_box.intersects(win): continue
            new_x: float = 0.0
            new_y = float(win.top() - hitbox.y() - hitbox.height())
            world_bounds: QRectF = self.world.scene.sceneRect()
            world_min_x: float = float(world_bounds.left() - hitbox.x())
            world_max_x: float = float(world_bounds.right() - hitbox.x() - hitbox.width())
            min_x: float = max(world_min_x, float(win.left() - hitbox.x() + 4))
            max_x: float = min(world_max_x, float(win.right() - hitbox.x() - hitbox.width() - 4))
            if min_x < max_x:
                new_x = max(min_x, min(float(entity.x()), max_x))
            else:
                new_x = max(world_min_x, min(float(win.left() - hitbox.x()), world_max_x))

            entity.setPos(new_x, new_y)
            self.velocity_y = 0.0
            if self.physics_sys is not None:
                self.physics_sys.current_platform_rect = win
            entity.on_moved()
            break

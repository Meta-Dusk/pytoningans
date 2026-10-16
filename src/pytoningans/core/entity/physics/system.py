from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import QPointF, QRect

from .gravity import tick_gravity_and_collisions
from .movement import tick_movement
from .repulsion import apply_soft_repulsion

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity


class PhysicsSystem:
    """
    Manages translation, gravity, platform landing, window collisions, and repulsion for entities.
    """

    def __init__(self, entity: Optional[BaseEntity] = None) -> None:
        self.entity = entity
        self.gravity: float = 0.8
        self.move_speed: float = 2.0
        self.current_platform_rect: Optional[QRect] = None

    def update(self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None) -> None:
        """Processes physics calculations based on elapsed time."""
        if self.entity is None or self.entity.world is None:
            return
        if not self.entity.locks.physics:
            self.entity.velocity_y = 0.0
            return

        ground_y: float = self.entity.world.scene.sceneRect().bottom()
        time_scale: float = dt / 16.0
        current_gravity: float = self.gravity * time_scale
        current_move_speed: float = self.move_speed * time_scale

        self._tick_gravity_and_collisions(ground_y, current_gravity)

        is_dead: bool = getattr(self.entity, "is_dead", False)
        if is_dead: return

        self._tick_soft_collision(current_move_speed, centers)
        self._tick_movement(current_move_speed)

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


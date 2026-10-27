from __future__ import annotations

from typing import TYPE_CHECKING, Optional, cast

from PySide6.QtCore import Qt

from ...constants import EntityState, EntityType

if TYPE_CHECKING:
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtWidgets import (
        QGraphicsSceneMouseEvent, QGraphicsSceneContextMenuEvent
    )
    from ...constants import SystemLocks
    from ...mod_manager import ModManager
    from ...world import WorldOverlay
    from ...entity.animation import AnimationSystem
    from ...entity.physics import PhysicsSystem
    from ...entity.base_entity import BaseEntity


class EntityDragMixin:
    """Encapsulates mouse dragging, positioning bounds clamping, and context menu events."""

    is_dragged: bool
    sprite_rotation: float
    velocity_y: float
    is_physics_enabled: bool
    locks: SystemLocks
    mod_manager: Optional[ModManager]
    world: Optional[WorldOverlay]
    anim_sys: Optional[AnimationSystem]
    physics_sys: Optional[PhysicsSystem]

    def _entity(self) -> BaseEntity:
        return cast("BaseEntity", self)

    def _init_drag(self) -> None:
        self.is_dragged = False

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self._entity()._hide_hover_tooltip()
        if event.button() == Qt.MouseButton.LeftButton:
            self._entity().release_cursor()
            self.is_dragged = True
            if self.physics_sys is not None and self.physics_sys.is_climbing:
                self.physics_sys.stop_climb()
            self.sprite_rotation = 0.0
            if (
                self.anim_sys is not None and
                self.mod_manager is not None and
                self.mod_manager.entity_type == EntityType.ENTITY and
                EntityState.DRAG in self.mod_manager.animations
            ):
                self.anim_sys.set_state(EntityState.DRAG)
            self.locks.physics = False
            self.velocity_y = 0.0
            event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        entity = self._entity()
        delta: QPointF = event.scenePos() - event.lastScenePos()
        new_x: float = entity.x() + delta.x()
        new_y: float = entity.y() + delta.y()

        if self.world is not None:
            bounds: QRectF = self.world.scene.sceneRect()
            new_x = max(bounds.left(), min(new_x, bounds.right() - entity.width()))
            new_y = max(bounds.top(), min(new_y, bounds.bottom() - entity.height()))

        entity.setPos(new_x, new_y)
        self.on_moved()
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        entity: BaseEntity = self._entity()
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragged = False
            if (
                self.anim_sys is not None and
                self.mod_manager is not None and
                self.mod_manager.entity_type == EntityType.ENTITY and
                EntityState.IDLE in self.mod_manager.animations
            ):
                self.anim_sys.set_state(EntityState.IDLE)
            self.locks.physics = self.is_physics_enabled
            if not self.is_physics_enabled:
                self.velocity_y = 0.0
            else:
                entity._check_window_drop_seat()
            event.accept()

        if entity.is_hovered:
            entity._show_hover_tooltip(event.screenPos())

    def on_moved(self) -> None:
        """Hook for subclasses to update attached items (like speech bubbles) when dragged."""
        entity = self._entity()
        if entity.is_cursor_grabbed:
            entity._sync_grabbed_cursor()

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        from pytoningans.ui.context_menu import EntityContextMenu
        EntityContextMenu.show_for_entity(self._entity(), event.screenPos())
        event.accept()

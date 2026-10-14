from __future__ import annotations

from typing import Optional, TYPE_CHECKING, cast, Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QGraphicsSceneContextMenuEvent, QGraphicsSceneMouseEvent, QMenu

from pytoningans.core.api import (
    BaseBehavior, BaseItemBehavior, BaseEntityBehavior, IItem, IEntity
)
from pytoningans.core.constants import ItemState, EntityState
from pytoningans.core.entity.base_entity import BaseEntity

if TYPE_CHECKING:
    from pytoningans.core.mod_manager import ModManager
    from pytoningans.core.world import WorldOverlay
    from pytoningans.core.entity.living_entity import Entity


class BaseItem(BaseEntity):
    """
    Interactable item object in the desktop game world.
    Inherits physics, dragging, hitboxes, and components from BaseEntity,
    and supports pickup, drop, use mechanics, and holder tracking.
    """
    def __init__(
        self,
        start_x: float,
        start_y: float,
        mod_manager: Optional[ModManager] = None,
        world: Optional[WorldOverlay] = None
    ) -> None:
        super().__init__(start_x, start_y, mod_manager, world)

        can_fly: bool = mod_manager.can_fly if mod_manager else False
        self.is_physics_enabled = not can_fly
        self.locks.physics = self.is_physics_enabled

        self._state: str = ItemState.IDLE.value
        self.holder: Optional[Entity] = None

    @property
    def is_held(self) -> bool:
        """Returns True if the item is currently held by an entity."""
        return self.holder is not None

    def set_physics_enabled(self, enabled: bool) -> None:
        """Sets whether the item is affected by gravity when dropped on the ground."""
        self.is_physics_enabled = enabled
        if not self.is_held:
            self.locks.physics = enabled
        if not enabled:
            self.velocity_y = 0.0

    def toggle_physics(self) -> None:
        """Toggles whether the item is affected by gravity."""
        self.set_physics_enabled(not self.is_physics_enabled)

    def pick_up(self, entity: Entity) -> bool:
        """
        Causes the specified living entity to pick up this item.
        Returns True if successful, False if cancelled by mod behavior or already held.
        """
        if self.holder is entity:
            return True
        if self.holder is not None and self.holder != entity:
            return False

        # Custom behavior hook
        behavior: Optional[BaseBehavior] = self.get_behavior
        if isinstance(behavior, BaseItemBehavior):
            try:
                allowed: bool = behavior.on_pickup(cast(IItem, self), cast(IEntity, entity))
                if not allowed:
                    return False
            except Exception as e:
                print(f"Custom Item on_pickup Error: {e}")
                return False

        # If target entity is already holding another item, drop it first
        if entity.held_item is not None and entity.held_item is not self:
            entity.held_item.drop(entity)

        self.holder = entity
        entity.held_item = self

        # Disable physics simulation while held
        self.locks.physics = False
        self.velocity_y = 0.0
        self.state = ItemState.HELD.value
        self._update_held_position()
        return True

    def _update_held_position(self) -> None:
        """Synchronizes the item position and z-stacking with its current holder."""
        if self.holder is None: return

        hx: float = self.holder.x()
        hy: float = self.holder.y()
        hw: int = self.holder.width()
        hh: int = self.holder.height()
        iw: int = self.width()
        ih: int = self.height()

        target_x: float = hx + (hw - iw) / 2.0
        target_y: float = hy - ih + (hh * 0.2)

        if self.world is not None:
            bounds: QRectF = self.world.scene.sceneRect()
            target_x = max(bounds.left(), min(target_x, bounds.right() - iw))
            target_y = max(bounds.top(), min(target_y, bounds.bottom() - ih))

        self.setPos(target_x, target_y)
        self.setZValue(self.holder.zValue() + 0.05)

    def drop(self, entity: Optional[Entity] = None) -> None:
        """
        Drops the item from its current holder onto the ground/desktop.
        """
        if self.holder is None: return

        prev_holder: Entity = self.holder
        self.holder = None
        if prev_holder.held_item is self:
            prev_holder.held_item = None

        self.locks.physics = self.is_physics_enabled
        self.state = ItemState.DROPPED.value

        behavior: Optional[BaseBehavior] = self.get_behavior
        if isinstance(behavior, BaseItemBehavior):
            try:
                behavior.on_drop(cast(IItem, self), cast(Optional[IEntity], prev_holder))
            except Exception as e:
                print(f"Custom Item on_drop Error: {e}")

    def use(self, entity: Optional[Entity] = None) -> bool:
        """
        Activates or consumes this item.
        Calls modder on_use callback and sets state to USED.
        """
        caller: Optional[Entity] = entity or self.holder
        handled: bool = True

        behavior: Optional[BaseBehavior] = self.get_behavior
        if isinstance(behavior, BaseItemBehavior):
            try:
                handled = behavior.on_use(cast(IItem, self), cast(Optional[IEntity], caller))
            except Exception as e:
                print(f"Custom Item on_use Error: {e}")
                handled = False

        if handled: self.state = ItemState.USED.value
        return handled

    def update_systems(
        self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None
    ) -> None:
        if self.is_paused: return

        # If held, stick to the holder
        if self.holder is not None:
            if getattr(self.holder, "is_dead", False) or self.holder.scene() is None:
                self.drop()
            else:
                self._update_held_position()

        super().update_systems(dt, centers)

        # Ground intersection checks when not held
        if self.holder is None and self.world is not None:
            item_rect: QRectF = self.sceneBoundingRect()
            for entity in list(self.world.active_entities):
                if entity.is_dead or not item_rect.intersects(entity.sceneBoundingRect()):
                    continue

                # Notify item custom behavior
                item_behavior: Optional[BaseBehavior] = self.get_behavior
                if isinstance(item_behavior, BaseItemBehavior):
                    try:
                        handled_item: bool = item_behavior.on_interact(
                            cast(IItem, self), cast(IEntity, entity)
                        )
                        if handled_item:
                            break
                    except Exception as e:
                        print(f"Custom Item on_interact Error: {e}")

                # Notify entity custom behavior
                entity_behavior: Optional[BaseBehavior] = entity.get_behavior
                if isinstance(entity_behavior, BaseEntityBehavior):
                    try:
                        handled_entity: bool = entity_behavior.on_item_interact(
                            cast(IEntity, entity), cast(IItem, self)
                        )
                        if handled_entity:
                            break
                    except Exception as e:
                        print(f"Custom Entity on_item_interact Error: {e}")

        # Tick custom behavior
        behavior: Optional[BaseBehavior] = self.get_behavior
        if isinstance(behavior, BaseItemBehavior):
            try:
                behavior.on_update(cast(IItem, self), dt)
            except Exception as e:
                print(f"Custom Item on_update Error: {e}")

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_held:
                # Dragging the item pulls it out of the holder's grasp
                self.drop()
        super().mousePressEvent(event)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        self.is_force_idle = True
        menu = QMenu(self.world.view) if self.world else QMenu()

        # Close/Destroy item
        menu.addAction("Destroy Item", self.destroy)
        menu.addSeparator()

        # Use Item
        menu.addAction("Use Item", lambda: self.use())

        # Drop or Give options
        if self.is_held:
            menu.addAction("Drop Item", lambda: self.drop())
        elif self.world is not None and self.world.active_entities:
            alive_entities: list[Entity] = [e for e in self.world.active_entities if not e.is_dead]
            if alive_entities:
                give_menu: QMenu = menu.addMenu("Give to Entity")
                for e in alive_entities:
                    give_menu.addAction(e.display_name, lambda target=e: self.pick_up(target))

        menu.addSeparator()

        # Flip Horizontally
        menu.addAction("Flip Horizontally", self.flip)

        # Toggle Physics / Gravity
        physics_action: QAction = menu.addAction("Affected by Gravity")
        physics_action.setCheckable(True)
        physics_action.setChecked(self.is_physics_enabled)
        physics_action.toggled.connect(self.set_physics_enabled)

        menu.exec(event.screenPos())
        self.is_force_idle = False

    def _on_destroy(self) -> None:
        behavior: Optional[BaseBehavior] = self.get_behavior
        if not isinstance(behavior, BaseItemBehavior): return
        try:
            behavior.on_destroy(cast(IItem, self))
        except Exception as e:
            print(f"Custom Item on_destroy Error: {e}")

    def destroy(self) -> None:
        self._on_destroy()
        if self.is_held:
            self.drop()

        if self.world is not None and self.world.manager is not None:
            self.world.manager.remove_entity(self)
        elif self.world is not None:
            if self in self.world.active_items:
                self.world.active_items.remove(self)
            if self.scene():
                self.scene().removeItem(self)

        super().destroy()


from __future__ import annotations

from typing import Optional, TYPE_CHECKING, cast, Any

from PySide6.QtWidgets import (
    QGraphicsPixmapItem, QGraphicsColorizeEffect, QGraphicsSceneMouseEvent, QGraphicsSceneHoverEvent
)
from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPixmap, QTransform

from pytoningans.core.constants import EntityState, SystemLocks
from pytoningans.core.entity.animation import AnimationSystem
from pytoningans.core.entity.physics import PhysicsSystem
from pytoningans.core.api import (
    IEntity, BaseEntityBehavior, BaseBehavior, BaseStructureBehavior, IStructure
)
from pytoningans.core.components.base_component import BaseComponent

if TYPE_CHECKING:
    from pytoningans.core.mod_manager import ModManager
    from pytoningans.core.world import WorldOverlay


class BaseEntity(QGraphicsPixmapItem):
    """The foundational class for all rendered objects in the game world."""
    def __init__(
        self, start_x: float, start_y: float,
        mod_manager: Optional[ModManager] = None,
        world: Optional[WorldOverlay] = None
    ) -> None:
        super().__init__()
        self.mod_manager = mod_manager
        self.world = world
        
        self._state: str = EntityState.IDLE
        self.facing_left: bool = False
        self.sprite_rotation: float = 0.0
        self.is_paused: bool = False
        self._is_force_idle: bool = False
        self.is_physics_enabled: bool = True
        self.velocity_y: float = 0.0
        
        self.components: dict[str, BaseComponent] = {}
        
        self.current_hitbox: QRect = QRect()
        self.current_attack_hitbox: QRect = QRect()
        
        self.locks: SystemLocks = SystemLocks()
        self.anim_sys: Optional[AnimationSystem] = AnimationSystem(self)
        self.physics_sys: Optional[PhysicsSystem] = PhysicsSystem(self)
        
        self._instance_name: Optional[str] = None
        self.is_hovered: bool = False
        self.setAcceptHoverEvents(True)
        
        self._setup_ui(start_x, start_y)
        self.update_tooltip()

    @property
    def instance_name(self) -> Optional[str]:
        return self._instance_name

    @instance_name.setter
    def instance_name(self, value: Optional[str]) -> None:
        self.set_instance_name(value)

    def set_instance_name(self, name: Optional[str]) -> None:
        """Sets a custom instance name for this entity and updates its tooltip."""
        self._instance_name = name
        self.update_tooltip()

    @property
    def display_name(self) -> str:
        if self._instance_name:
            return self._instance_name
        if self.mod_manager is not None:
            if self.mod_manager.current_mod_name:
                return self.mod_manager.current_mod_name
            if self.mod_manager.current_mod_folder:
                return self.mod_manager.current_mod_folder
        return "Entity"

    def update_tooltip(self) -> None:
        """Updates the item tooltip to match its display name."""
        self.setToolTip(self.display_name)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.on_hover_enter()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.on_hover_leave()
        super().hoverLeaveEvent(event)

    def on_hover_enter(self) -> None:
        """Hook called when the mouse cursor enters the entity's bounding area."""
        self.is_hovered = True
        self._on_hover_enter()

    def on_hover_leave(self) -> None:
        """Hook called when the mouse cursor leaves the entity's bounding area."""
        self.is_hovered = False
        self._on_hover_leave()

    def _on_hover_enter(self) -> None:
        if self.mod_manager is not None and self.mod_manager.custom_behavior is not None:
            behavior: BaseBehavior = self.mod_manager.custom_behavior
            try:
                if isinstance(behavior, BaseEntityBehavior):
                    behavior.on_hover_enter(cast(IEntity, self))
                elif isinstance(behavior, BaseStructureBehavior):
                    behavior.on_hover_enter(cast(IStructure, self))
            except Exception as e:
                print(f"Custom Behavior on_hover_enter Error: {e}")

    def _on_hover_leave(self) -> None:
        if self.mod_manager is not None and self.mod_manager.custom_behavior is not None:
            behavior: BaseBehavior = self.mod_manager.custom_behavior
            try:
                if isinstance(behavior, BaseEntityBehavior):
                    behavior.on_hover_leave(cast(IEntity, self))
                elif isinstance(behavior, BaseStructureBehavior):
                    behavior.on_hover_leave(cast(IStructure, self))
            except Exception as e:
                print(f"Custom Behavior on_hover_leave Error: {e}")
    
    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value: Any) -> None:
        val_str = value.value if hasattr(value, "value") else str(value)
        if getattr(self, "_state", None) == val_str:
            return
        old_state: str = self._state
        self._state = val_str
        if self.anim_sys is not None:
            self.anim_sys.set_state(val_str)
        self._on_state_change(old_state, val_str)

    @property
    def is_force_idle(self) -> bool:
        return self._is_force_idle

    @is_force_idle.setter
    def is_force_idle(self, value: bool) -> None:
        self._is_force_idle = value
        if not value: return
        self.velocity_y = 0.0
        if hasattr(self, "_target_pos"):
            self._target_pos = None
        if hasattr(self, "target_pos"):
            self.target_pos = None
        if not getattr(self, "is_dead", False) and self.anim_sys:
            self.anim_sys.set_state(EntityState.IDLE)

    def set_force_idle(self, enabled: bool) -> None:
        """Toggles force-idle state where the entity plays idle animations but disables AI and gravity."""
        self.is_force_idle = enabled

    def _on_state_change(self, old_state: str, new_state: str) -> None:
        if self.mod_manager is None or self.mod_manager.custom_behavior is None:
            return
        behavior: BaseBehavior = self.mod_manager.custom_behavior
        try:
            if isinstance(behavior, BaseEntityBehavior):
                behavior.on_state_change(cast(IEntity, self), old_state, new_state)
            elif isinstance(behavior, BaseStructureBehavior):
                behavior.on_state_change(cast(IStructure, self), old_state, new_state)
        except Exception as e:
            print(f"Custom Behavior on_state_change Error: {e}")

    def flip(self) -> None:
        """Toggles horizontal facing direction and horizontally mirrors collision hitboxes."""
        self.facing_left = not self.facing_left
        if self.anim_sys is not None:
            self.anim_sys.refresh_frame()
        else:
            pix: QPixmap = self.pixmap()
            if pix.isNull(): return
            
            transform: QTransform = QTransform().scale(-1, 1)
            self.setPixmap(pix.transformed(transform))
            if self.current_hitbox.isNull(): return
            
            w: int = pix.width()
            dx: int = w - (self.current_hitbox.x() + self.current_hitbox.width())
            self.current_hitbox = QRect(
                dx, self.current_hitbox.y(),
                self.current_hitbox.width(), self.current_hitbox.height()
            )
    
    def move(self, x: float, y: float) -> None:
        """Convenience method matching the protocol definition."""
        self.setPos(x, y)

    def _setup_ui(self, x: float, y: float) -> None:
        self.setPos(x, y)
        self.tint_effect = QGraphicsColorizeEffect()
        self.tint_effect.setColor(QColor(255, 0, 0)) 
        self.tint_effect.setEnabled(False)
        self.setGraphicsEffect(self.tint_effect)
        
    def width(self) -> int:
        return int(self.boundingRect().width())
        
    def height(self) -> int:
        return int(self.boundingRect().height())
        
    def toFront(self) -> None:
        self.setZValue(self.zValue() + 0.1)
    
    # --- Component Management API ---
    def add_component(self, component: BaseComponent) -> BaseComponent:
        component.owner = self
        self.components[component.name] = component
        component.on_attach()
        return component

    def get_component(self, name: str) -> Optional[BaseComponent]:
        return self.components.get(name)

    def has_component(self, name: str) -> bool:
        return name in self.components

    def remove_component(self, name: str) -> Optional[BaseComponent]:
        comp: Optional[BaseComponent] = self.components.pop(name, None)
        if comp is not None:
            comp.on_detach()
            comp.owner = None
        return comp

    def update_systems(
        self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None
    ) -> None:
        if self.is_paused: return
        
        if (
            self.locks.physics and
            not self.is_force_idle and
            self.physics_sys is not None
        ):
            self.physics_sys.update(dt, centers)
        if (
            self.locks.animation and
            self.anim_sys is not None
        ):
            self.anim_sys.update(dt)
        
        # Dispatch ticks to all active components
        for comp in list(self.components.values()):
            if comp.enabled: comp.update(dt)

    def destroy(self) -> None:
        for comp in list(self.components.values()):
            comp.on_detach()
            comp.owner = None
        self.components.clear()
        
        if self.scene(): self.scene().removeItem(self)
        self.anim_sys = None
        self.physics_sys = None

    # Universal Drag Logic
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.anim_sys is not None:
                self.anim_sys.set_state(EntityState.DRAG)
            self.locks.physics = False
            event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        delta: QPointF = event.scenePos() - event.lastScenePos()
        new_x: float = self.x() + delta.x()
        new_y: float = self.y() + delta.y()
        
        if self.world is not None:
            bounds: QRectF = self.world.scene.sceneRect()
            new_x = max(bounds.left(), min(new_x, bounds.right() - self.width()))
            new_y = max(bounds.top(), min(new_y, bounds.bottom() - self.height()))
        
        self.setPos(new_x, new_y)
        
        # Give subclasses a chance to react to moving
        self.on_moved()
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.anim_sys is not None:
                self.anim_sys.set_state(EntityState.IDLE)
            self.locks.physics = self.is_physics_enabled
            if not self.is_physics_enabled:
                self.velocity_y = 0.0
            event.accept()
            
    def on_moved(self) -> None:
        """Hook for subclasses to update attached items (like speech bubbles) when dragged."""
        pass

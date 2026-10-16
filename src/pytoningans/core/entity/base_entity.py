from __future__ import annotations

from typing import Optional, TYPE_CHECKING, cast, Any

from PySide6.QtWidgets import (
    QGraphicsPixmapItem, QGraphicsColorizeEffect, QGraphicsSceneMouseEvent,
    QGraphicsSceneHoverEvent, QGraphicsSceneContextMenuEvent
)
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPixmap, QTransform, QCursor

from pytoningans.core.constants import EntityState, SystemLocks, EntityType
from pytoningans.core.entity.animation import AnimationSystem
from pytoningans.core.entity.physics import PhysicsSystem
from pytoningans.core.entity.indicators import HighlightOutlineItem
from pytoningans.core.api import (
    IEntity, BaseEntityBehavior, BaseBehavior, BaseStructureBehavior, IStructure,
    BaseItemBehavior, IItem
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
        self.is_dragged: bool = False
        self.velocity_y: float = 0.0
        
        self.components: dict[str, BaseComponent] = {}
        
        self.current_hitbox: QRect = QRect()
        self.current_attack_hitbox: QRect = QRect()
        
        self.locks: SystemLocks = SystemLocks()
        self.anim_sys: Optional[AnimationSystem] = AnimationSystem(self)
        self.physics_sys: Optional[PhysicsSystem] = PhysicsSystem(self)
        
        self._instance_name: Optional[str] = None
        self.tags: set[str] = (
            set(self.mod_manager.tags) if self.mod_manager is not None else set()
        )
        self.is_hovered: bool = False
        self.setAcceptHoverEvents(True)
        
        self._setup_ui(start_x, start_y)
        self.update_tooltip()
        self._highlight_item: Optional[Any] = None
        self._active_context_menu: Optional[Any] = None

    def pause_death_animations(self) -> None:
        """Hook for subclasses to pause death animations while context menu is open."""
        pass

    def resume_death_animations(self) -> None:
        """Hook for subclasses to resume death animations when context menu is closed."""
        pass

    def set_highlighted(self, enabled: bool) -> None:
        """Toggles visual selection highlight outline around this entity."""
        if enabled:
            if self._highlight_item is None:
                self._highlight_item = HighlightOutlineItem(self)
            self._highlight_item.setVisible(True)
        elif self._highlight_item is not None:
            self._highlight_item.setVisible(False)
    
    @property
    def is_static(self) -> bool:
        """Returns whether this entity is static (single-sprite / non-animated)."""
        if self.mod_manager is not None:
            return getattr(self.mod_manager, "is_static", False)
        return False

    @property
    def can_climb_walls(self) -> bool:
        """Returns True if the entity is configured to climb desktop window walls."""
        if self.mod_manager is not None:
            return getattr(self.mod_manager, "can_climb_walls", False)
        return False

    @property
    def is_climbing(self) -> bool:
        """Returns True if the entity is currently climbing a window wall."""
        if self.physics_sys is not None:
            return getattr(self.physics_sys, "is_climbing", False)
        return False

    @property
    def behavior(self) -> Optional[BaseBehavior]:
        return self.mod_manager.custom_behavior if self.mod_manager is not None else None
    
    @property
    def instance_name(self) -> Optional[str]:
        return self._instance_name

    @instance_name.setter
    def instance_name(self, value: Optional[str]) -> None:
        self.set_instance_name(value)

    def set_instance_name(self, name: Optional[str]) -> None:
        """Sets a custom instance name for this entity and updates HUD and tooltip."""
        self._instance_name = name
        self.update_tooltip()
        self.on_instance_name_changed()
        if self.is_hovered:
            self._show_hover_tooltip(QCursor.pos())

    def on_instance_name_changed(self) -> None:
        """Hook for subclasses to react to instance name updates (e.g. updating HUD elements)."""
        pass

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

    @property
    def identification(self) -> str:
        """Formatted identification string for the entity: '<entity_type> from <mod_name>'."""
        type_str: str = "Entity"
        if self.mod_manager is not None and self.mod_manager.entity_type:
            type_str = str(self.mod_manager.entity_type).capitalize()
        else:
            cls_name: str = self.__class__.__name__
            if "Structure" in cls_name:
                type_str = "Structure"
            elif "Item" in cls_name:
                type_str = "Item"
            else:
                type_str = "Entity"

        mod_name: str = "Unknown"
        if self.mod_manager is not None:
            if self.mod_manager.current_mod_name:
                mod_name = self.mod_manager.current_mod_name
            elif self.mod_manager.current_mod_folder:
                mod_name = self.mod_manager.current_mod_folder

        return f"{type_str} from \"{mod_name}\""

    def update_tooltip(self) -> None:
        """Updates the item tooltip to match its identification."""
        self.setToolTip(self.identification)

    #? Entity Tags API
    def has_tag(self, tag: str) -> bool:
        """Returns True if the entity has the specified tag (case-insensitive)."""
        return tag.lower().strip() in self.tags

    def has_all_tags(self, *tags: str) -> bool:
        """Returns True if the entity contains every specified tag."""
        return all(t.lower().strip() in self.tags for t in tags)

    def has_any_tag(self, *tags: str) -> bool:
        """Returns True if the entity contains at least one of the specified tags."""
        return any(t.lower().strip() in self.tags for t in tags)

    def add_tag(self, tag: str) -> None:
        """Dynamically adds a tag to the entity at runtime."""
        clean_tag: str = tag.lower().strip()
        if clean_tag:
            self.tags.add(clean_tag)

    def remove_tag(self, tag: str) -> None:
        """Removes a tag from the entity at runtime."""
        self.tags.discard(tag.lower().strip())

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.on_hover_enter()
        self._show_hover_tooltip(event.screenPos())
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        if self.is_hovered:
            self._show_hover_tooltip(event.screenPos())
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.on_hover_leave()
        self._hide_hover_tooltip()
        super().hoverLeaveEvent(event)

    def _show_hover_tooltip(self, screen_pos: QPoint) -> None:
        tip_text: str = self.identification
        if tip_text:
            from pytoningans.ui.tool_tip import CustomToolTipManager
            CustomToolTipManager.get().show_tip(None, tip_text, screen_pos)

    def _hide_hover_tooltip(self) -> None:
        from pytoningans.ui.tool_tip import CustomToolTipManager
        CustomToolTipManager.get().hide_tip()

    def on_hover_enter(self) -> None:
        """Hook called when the mouse cursor enters the entity's bounding area."""
        self.is_hovered = True
        self._on_hover_enter()

    def on_hover_leave(self) -> None:
        """Hook called when the mouse cursor leaves the entity's bounding area."""
        self.is_hovered = False
        self._on_hover_leave()

    def _on_hover_enter(self) -> None:
        behavior: Optional[BaseBehavior] = self.behavior
        if behavior is None: return
        try:
            if isinstance(behavior, BaseEntityBehavior):
                behavior.on_hover_enter(cast(IEntity, self))
            elif isinstance(behavior, BaseStructureBehavior):
                behavior.on_hover_enter(cast(IStructure, self))
            elif isinstance(behavior, BaseItemBehavior):
                behavior.on_hover_enter(cast(IItem, self))
        except Exception as e:
            print(f"Custom Behavior on_hover_enter Error: {e}")

    def _on_hover_leave(self) -> None:
        behavior: Optional[BaseBehavior] = self.behavior
        if behavior is None: return
        try:
            if isinstance(behavior, BaseEntityBehavior):
                behavior.on_hover_leave(cast(IEntity, self))
            elif isinstance(behavior, BaseStructureBehavior):
                behavior.on_hover_leave(cast(IStructure, self))
            elif isinstance(behavior, BaseItemBehavior):
                behavior.on_hover_leave(cast(IItem, self))
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
        old_state: str = getattr(self, "_state", "")
        if self.anim_sys is not None:
            self.anim_sys.set_state(val_str)
        else:
            self._state = val_str
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

    @property
    def is_interactable(self) -> bool:
        """Returns True if the entity is currently eligible for interactions."""
        return not self.is_dragged and not self.is_force_idle and not self.is_paused

    def _on_state_change(self, old_state: str, new_state: str) -> None:
        behavior: Optional[BaseBehavior] = self.behavior
        if behavior is None: return
        try:
            if isinstance(behavior, BaseEntityBehavior):
                behavior.on_state_change(cast(IEntity, self), old_state, new_state)
            elif isinstance(behavior, BaseStructureBehavior):
                behavior.on_state_change(cast(IStructure, self), old_state, new_state)
            elif isinstance(behavior, BaseItemBehavior):
                behavior.on_state_change(cast(IItem, self), old_state, new_state)
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
        self.is_dragged = False
        self._hide_hover_tooltip()
        for comp in list(self.components.values()):
            comp.on_detach()
            comp.owner = None
        self.components.clear()
        
        if self.scene():
            self.scene().removeItem(self)
        if self.anim_sys is not None:
            self.anim_sys.entity = None
            self.anim_sys = None
        if self.physics_sys is not None:
            self.physics_sys.entity = None
            self.physics_sys = None
        if self._highlight_item is not None:
            self._highlight_item.setVisible(False)
            if self.scene() and self._highlight_item.scene():
                self.scene().removeItem(self._highlight_item)
        if hasattr(self, "_active_context_menu") and self._active_context_menu is not None:
            menu = self._active_context_menu
            self._active_context_menu = None
            try:
                menu.close()
            except RuntimeError:
                pass
        self.setGraphicsEffect(cast(Any, None))
        self.tint_effect = None
        self.world = None
        self.mod_manager = None

    # Universal Drag Logic
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self._hide_hover_tooltip()
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragged = True
            if self.physics_sys is not None and getattr(self.physics_sys, "is_climbing", False):
                self.physics_sys.stop_climb()
            self.sprite_rotation = 0.0
            if (
                self.anim_sys is not None and
                self.mod_manager is not None and
                self.mod_manager.entity_type == EntityType.ENTITY.value and
                EntityState.DRAG in self.mod_manager.animations
            ):
                self.anim_sys.set_state(EntityState.DRAG)
            self.locks.physics = False
            self.velocity_y = 0.0
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
            self.is_dragged = False
            if (
                self.anim_sys is not None and
                self.mod_manager is not None and
                self.mod_manager.entity_type == EntityType.ENTITY.value and
                EntityState.IDLE in self.mod_manager.animations
            ):
                self.anim_sys.set_state(EntityState.IDLE)
            self.locks.physics = self.is_physics_enabled
            if not self.is_physics_enabled:
                self.velocity_y = 0.0
            else:
                self._check_window_drop_seat()
            event.accept()
        if self.is_hovered:
            self._show_hover_tooltip(event.screenPos())

    def _check_window_drop_seat(self) -> None:
        """
        If dropped onto or inside an active desktop window,
        seat entity on the window's top ledge.
        """
        if self.world is None:
            return
        from pytoningans.core.settings import SettingsManager
        if not SettingsManager.get().settings.enable_window_physics:
            return

        window_rects: list[QRect] = getattr(self.world, "active_window_rects", [])
        if not window_rects:
            return

        hitbox: QRect = self.current_hitbox
        if hitbox.width() <= 0 or hitbox.height() <= 0:
            b_rect: QRectF = self.boundingRect()
            bw: int = int(b_rect.width()) if b_rect.width() > 0 else 50
            bh: int = int(b_rect.height()) if b_rect.height() > 0 else 50
            hitbox = QRect(0, 0, bw, bh)

        scene_box = QRect(
            int(self.x() + hitbox.x()),
            int(self.y() + hitbox.y()),
            hitbox.width(),
            hitbox.height(),
        )

        for win in window_rects:
            if scene_box.intersects(win):
                new_x: float = 0.0
                new_y = float(win.top() - hitbox.y() - hitbox.height())
                world_bounds: QRectF = self.world.scene.sceneRect()
                world_min_x: float = float(world_bounds.left() - hitbox.x())
                world_max_x: float = float(world_bounds.right() - hitbox.x() - hitbox.width())
                min_x = max(world_min_x, float(win.left() - hitbox.x() + 4))
                max_x = min(world_max_x, float(win.right() - hitbox.x() - hitbox.width() - 4))
                if min_x < max_x:
                    new_x = max(min_x, min(float(self.x()), max_x))
                else:
                    new_x = max(world_min_x, min(float(win.left() - hitbox.x()), world_max_x))

                self.setPos(new_x, new_y)
                self.velocity_y = 0.0
                if self.physics_sys is not None:
                    self.physics_sys.current_platform_rect = win
                self.on_moved()
                break
            
    def on_moved(self) -> None:
        """Hook for subclasses to update attached items (like speech bubbles) when dragged."""
        pass

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        from pytoningans.ui.context_menu import EntityContextMenu
        EntityContextMenu.show_for_entity(self, event.screenPos())
        event.accept()

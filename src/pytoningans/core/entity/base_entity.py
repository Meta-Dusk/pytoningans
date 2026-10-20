from __future__ import annotations

from typing import Optional, TYPE_CHECKING, cast, Any, Union

from PySide6.QtWidgets import (
    QGraphicsPixmapItem, QGraphicsColorizeEffect
)
from PySide6.QtCore import QPoint, QPointF, QRect, QVariantAnimation
from PySide6.QtGui import QColor, QPixmap, QTransform

from pytoningans.core.constants import EntityState, SystemLocks
from pytoningans.core.entity.animation import AnimationSystem
from pytoningans.core.entity.physics import PhysicsSystem
from pytoningans.core.entity.indicators import HighlightOutlineItem, DebugHitboxOverlayItem
from pytoningans.core.api import (
    IEntity, BaseEntityBehavior, BaseBehavior, BaseStructureBehavior, IStructure,
    BaseItemBehavior, IItem, Pos2D
)
from pytoningans.core.entity.mixins import (
    EntityCursorMixin,
    EntityDragMixin,
    EntityWindowMixin,
    EntityTooltipMixin,
    EntityTagMixin,
    EntityComponentMixin,
)

if TYPE_CHECKING:
    from pytoningans.core.mod_manager import ModManager
    from pytoningans.core.world import WorldOverlay
    from pytoningans.ui.context_menu import EntityContextMenu


type _UniPos2D = Union[Pos2D, QPointF, tuple[float, float], list[float]]

class BaseEntity(
    EntityCursorMixin,
    EntityDragMixin,
    EntityWindowMixin,
    EntityTooltipMixin,
    EntityTagMixin,
    EntityComponentMixin,
    QGraphicsPixmapItem,
):
    """The foundational class for all rendered objects in the game world."""

    def __init__(
        self, start_x: float, start_y: float,
        mod_manager: Optional[ModManager] = None,
        world: Optional[WorldOverlay] = None
    ) -> None:
        super().__init__()
        self.mod_manager: Optional[ModManager] = mod_manager
        self.world: Optional[WorldOverlay] = world
        
        self._state: str = EntityState.IDLE
        self.facing_left: bool = False
        self.sprite_rotation: float = 0.0
        self.is_paused: bool = False
        self._is_force_idle: bool = False
        self.is_physics_enabled: bool = True
        self.velocity_y: float = 0.0
        self._target_pos: Optional[QPointF] = None
        self.current_hold_offset: Optional[QPoint] = None
        
        self.current_hitbox: QRect = QRect()
        self.current_attack_hitbox: QRect = QRect()
        
        self.locks: SystemLocks = SystemLocks()
        self.anim_sys: Optional[AnimationSystem] = AnimationSystem(self)
        self.physics_sys: Optional[PhysicsSystem] = PhysicsSystem(self)
        
        self.fade_in_on_spawn: bool = (
            mod_manager.fade_in_on_spawn if mod_manager is not None else False
        )
        self._fade_anim: Optional[QVariantAnimation] = None
        self._highlight_item: Optional[HighlightOutlineItem] = None
        self._debug_overlay: Optional[DebugHitboxOverlayItem] = None
        self._active_context_menu: Optional[EntityContextMenu] = None

        # Initialize modular mixins
        self._init_tags()
        self._init_components()
        self._init_tooltip()
        self._init_window_physics()
        self._init_cursor()
        self._init_drag()

        self._setup_ui(start_x, start_y)

    def pause_death_animations(self) -> None:
        """Pauses active fade/death animations while context menu is open."""
        if (
            self._fade_anim is not None and
            self._fade_anim.state() == QVariantAnimation.State.Running
        ):
            self._fade_anim.pause()

    def resume_death_animations(self) -> None:
        """Resumes active fade/death animations when context menu is closed."""
        if (
            self._fade_anim is not None and
            self._fade_anim.state() == QVariantAnimation.State.Paused
        ):
            self._fade_anim.resume()

    def set_highlighted(self, enabled: bool) -> None:
        """Toggles visual selection highlight outline around this entity."""
        if enabled:
            if self._highlight_item is None:
                self._highlight_item = HighlightOutlineItem(self)
            self._highlight_item.setVisible(True)
        elif self._highlight_item is not None:
            self._highlight_item.setVisible(False)
    
    @property
    def is_debug_hitbox_visible(self) -> bool:
        """Returns whether physics/attack hitboxes are visually displayed."""
        return self._debug_overlay is not None and self._debug_overlay.show_hitboxes

    @property
    def is_debug_attack_range_visible(self) -> bool:
        """Returns whether the aggro/attack range circle is visually displayed."""
        return self._debug_overlay is not None and self._debug_overlay.show_attack_range

    def toggle_debug_hitboxes(self) -> None:
        """Toggles visual debug display for physics collision and attack hitboxes."""
        if self._debug_overlay is None:
            self._debug_overlay = DebugHitboxOverlayItem(self)
        
        self._debug_overlay.show_hitboxes = not self._debug_overlay.show_hitboxes
        is_active = self._debug_overlay.show_hitboxes or self._debug_overlay.show_attack_range
        self._debug_overlay.setVisible(is_active)
        if is_active:
            self._debug_overlay.update_overlay()

    def toggle_debug_attack_range(self) -> None:
        """Toggles visual debug display for attack/aggro range circle."""
        if self._debug_overlay is None:
            self._debug_overlay = DebugHitboxOverlayItem(self)
        
        self._debug_overlay.show_attack_range = not self._debug_overlay.show_attack_range
        is_active = self._debug_overlay.show_hitboxes or self._debug_overlay.show_attack_range
        self._debug_overlay.setVisible(is_active)
        if is_active:
            self._debug_overlay.update_overlay()

    @property
    def is_static(self) -> bool:
        """Returns whether this entity is static (single-sprite / non-animated)."""
        return self.mod_manager.is_static if self.mod_manager is not None else False

    @property
    def behavior(self) -> Optional[BaseBehavior]:
        return self.mod_manager.custom_behavior if self.mod_manager is not None else None

    @property
    def pack(self) -> Optional[Any]:
        """Returns the parent ModPack controller if this entity belongs to a modpack, or None."""
        if self.mod_manager is not None and self.mod_manager.pack is not None:
            return self.mod_manager.pack.controller
        return None

    @property
    def pack_id(self) -> Optional[str]:
        """Returns the identifier of the parent modpack, or None if standalone."""
        return self.mod_manager.pack_id if self.mod_manager is not None else None

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value: str) -> None:
        if self._state == value:
            return
        old_state: str = self._state
        if self.anim_sys is not None:
            self.anim_sys.set_state(value)
        else:
            self._state = value
        self._on_state_change(old_state, value)

    @property
    def target_pos(self) -> Optional[QPointF]:
        """Destination point the entity is currently moving towards, or None."""
        return self._target_pos

    @target_pos.setter
    def target_pos(self, pos: Optional[_UniPos2D]) -> None:
        if pos is None:
            self._target_pos = None
        elif isinstance(pos, QPointF):
            self._target_pos = pos
        elif isinstance(pos, (tuple, list)) and len(pos) >= 2:
            self._target_pos = QPointF(float(pos[0]), float(pos[1]))
        elif isinstance(pos, Pos2D):
            self._target_pos = QPointF(pos.x, pos.y)
        else:
            self._target_pos = None

    @property
    def current_hold_pos(self) -> Optional[QPointF]:
        """Returns the world scene coordinates where held items should be positioned, or None."""
        if self.current_hold_offset is None:
            return None
        return QPointF(self.x() + self.current_hold_offset.x(), self.y() + self.current_hold_offset.y())

    @property
    def is_force_idle(self) -> bool:
        return self._is_force_idle

    @is_force_idle.setter
    def is_force_idle(self, value: bool) -> None:
        self._is_force_idle = value
        if not value: return
        self.velocity_y = 0.0
        self.target_pos = None
        if not getattr(self, "is_dead", False) and self.anim_sys:
            self.anim_sys.set_state(EntityState.IDLE)

    def set_force_idle(self, enabled: bool) -> None:
        """Toggles force-idle state where the entity plays idle animations but disables AI and gravity."""
        self.is_force_idle = enabled

    @property
    def move_speed(self) -> float:
        """Entity movement speed in pixels per frame."""
        if self.physics_sys is not None:
            return self.physics_sys.move_speed
        if self.mod_manager is not None:
            return self.mod_manager.move_speed
        return 2.0

    @move_speed.setter
    def move_speed(self, value: float) -> None:
        val = float(value)
        if self.physics_sys is not None:
            self.physics_sys.move_speed = val

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
        if self.fade_in_on_spawn:
            self.fade_in()
        
    def fade_in(self, duration_ms: int = 1000) -> None:
        """Smoothly fades in the entity from current opacity (or 0.0) to 1.0."""
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None

        start_val: float = self.opacity()
        if start_val >= 1.0:
            start_val = 0.0
            self.setOpacity(0.0)

        anim = QVariantAnimation(self.world if self.world is not None else None)
        anim.setDuration(duration_ms)
        anim.setStartValue(start_val)
        anim.setEndValue(1.0)
        anim.valueChanged.connect(self.setOpacity)

        def _on_finish() -> None:
            self.setOpacity(1.0)
            self._fade_anim = None

        anim.finished.connect(_on_finish)
        self._fade_anim = anim
        anim.start()

    def fade_out(self, duration_ms: int = 1000, destroy_on_complete: bool = False) -> None:
        """Smoothly fades out the entity from current opacity to 0.0."""
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None

        start_val: float = self.opacity()
        anim = QVariantAnimation(self.world if self.world is not None else None)
        anim.setDuration(duration_ms)
        anim.setStartValue(start_val)
        anim.setEndValue(0.0)
        anim.valueChanged.connect(self.setOpacity)

        def _on_finish() -> None:
            self.setOpacity(0.0)
            self._fade_anim = None
            if destroy_on_complete:
                self.destroy()

        anim.finished.connect(_on_finish)
        self._fade_anim = anim
        anim.start()

    def width(self) -> int:
        return int(self.boundingRect().width())
        
    def height(self) -> int:
        return int(self.boundingRect().height())
        
    def toFront(self) -> None:
        self.setZValue(self.zValue() + 0.1)

    def update_systems(
        self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None
    ) -> None:
        if self.is_paused:
            return

        self._update_cursor_interaction(dt)

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

        self._update_components(dt)

    def destroy(self) -> None:
        self.release_cursor()
        self.follow_cursor(False)
        self.is_dragged = False
        self._hide_hover_tooltip()
        self._destroy_components()

        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None
        
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
            self._highlight_item = None
        if self._debug_overlay is not None:
            self._debug_overlay.setVisible(False)
            if self.scene() and self._debug_overlay.scene():
                self.scene().removeItem(self._debug_overlay)
            self._debug_overlay = None
        if self._active_context_menu is not None:
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

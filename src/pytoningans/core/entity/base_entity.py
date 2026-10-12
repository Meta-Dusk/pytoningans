from __future__ import annotations
import random
from typing import Optional, TYPE_CHECKING, cast, Any

from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsColorizeEffect, QMenu
from PySide6.QtCore import QPointF, QRect, QRectF, QVariantAnimation, QEasingCurve, Qt
from PySide6.QtGui import QColor, QPixmap, QTransform
from PySide6.QtWidgets import QGraphicsSceneMouseEvent, QGraphicsSceneContextMenuEvent

from pytoningans.core.constants import AnimationMeta, EntityState, SystemLocks, DeathAnimation, StructureState
from pytoningans.core.entity.animation import AnimationSystem
from pytoningans.core.entity.physics import PhysicsSystem
from pytoningans.core.entity.ai_brain import AISystem
from pytoningans.core.entity.speech_bubble import SpeechBubble
from pytoningans.core.entity.indicators import HealthBarItem
from pytoningans.core.api import (
    IEntity, Pos2D, BaseEntityBehavior, BaseBehavior, BaseStructureBehavior, IStructure
)
from pytoningans.core.components.base_component import BaseComponent
from pytoningans.core.components.teleportation import TeleportationComponent

if TYPE_CHECKING:
    from pytoningans.core.mod_manager import ModManager
    from pytoningans.core.world import WorldOverlay
    from pytoningans.core.entity_manager import EntityManager


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
        self.velocity_y: float = 0.0
        
        self.components: dict[str, BaseComponent] = {}
        
        self.current_hitbox: QRect = QRect()
        self.current_attack_hitbox: QRect = QRect()
        
        self.locks: SystemLocks = SystemLocks()
        self.anim_sys: Optional[AnimationSystem] = AnimationSystem(self)
        self.physics_sys: Optional[PhysicsSystem] = PhysicsSystem(self)
        
        self._setup_ui(start_x, start_y)
    
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
            nx: int = w - (self.current_hitbox.x() + self.current_hitbox.width())
            self.current_hitbox = QRect(
                nx, self.current_hitbox.y(),
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
        
        if self.locks.physics and self.physics_sys:
            self.physics_sys.update(dt, centers)
        if self.locks.animation and self.anim_sys:
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
            if self.anim_sys:
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
            if self.anim_sys:
                self.anim_sys.set_state(EntityState.IDLE)
            self.locks.physics = True
            event.accept()
            
    def on_moved(self) -> None:
        """Hook for subclasses to update attached items (like speech bubbles) when dragged."""
        pass


class Entity(BaseEntity):
    """Living entities with AI, health, dialogue, and combat (formerly PetWindow)."""
    def __init__(
        self, start_x: float, start_y: float,
        mod_manager: ModManager, world: WorldOverlay, pet_manager: EntityManager
    ) -> None:
        super().__init__(start_x, start_y, mod_manager, world)
        self.entity_manager = pet_manager
        
        self.is_dead: bool = False
        self.current_health: int = mod_manager.max_health if mod_manager else 100
        self.damage_tint_time_left: int = 0
        self.revive_time_left: int = 0
        self._target_pos: Optional[QPointF] = None
        
        self._fade_anim: Optional[QVariantAnimation] = None
        self._rot_anim: Optional[QVariantAnimation] = None
        
        self.ai_sys: Optional[AISystem] = AISystem(self)
        self.bubble: Optional[SpeechBubble] = None
        self.health_bar: Optional[HealthBarItem] = HealthBarItem(self)
        
        if self.anim_sys:
            self.anim_sys.attack_frame_hit.connect(self.ai_sys.process_combat)

    @property
    def is_interactable(self) -> bool:
        return self.state not in (EntityState.DRAG, EntityState.INTERACT) and not self.is_dead

    @property
    def target_pos(self) -> Optional[QPointF]:
        return self._target_pos

    @target_pos.setter
    def target_pos(self, pos: Optional[Pos2D]) -> None:
        if pos is None:
            self._target_pos = None
        else:
            self._target_pos = QPointF(pos.x, pos.y)

    def update_systems(self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None) -> None:
        if self.is_paused: return
        
        if self.bubble: self.bubble.tick(dt)
        if self.health_bar: self.health_bar.tick(dt)
        
        if self.revive_time_left > 0:
            self.revive_time_left -= dt
            if self.revive_time_left <= 0:
                if self.anim_sys: self.anim_sys.set_state(EntityState.IDLE)
                self.locks.ai = True
                self.locks.physics = True
                
        if self.damage_tint_time_left > 0:
            self.damage_tint_time_left -= dt
            if self.damage_tint_time_left <= 0:
                self.tint_effect.setEnabled(False)
            else:
                fade_strength = 0.7 * (self.damage_tint_time_left / 300.0)
                self.tint_effect.setStrength(fade_strength)

        if self.is_dead:
            super().update_systems(dt, centers)
            return
            
        if self.locks.ai and self.ai_sys: self.ai_sys.update(dt)
        super().update_systems(dt, centers)
        
        if self.mod_manager and self.mod_manager.custom_behavior:
            behavior: BaseBehavior = self.mod_manager.custom_behavior
            if isinstance(behavior, BaseEntityBehavior):
                try:
                    behavior.on_update(cast(IEntity, self), dt)
                except Exception as e:
                    print(f"Custom Entity on_update Error: {e}")

    def on_moved(self) -> None:
        if self.health_bar: self.health_bar.update_position()
        if self.bubble: self.bubble.update_position()

    def take_damage(self, amount: int) -> None:
        if self.is_dead: return
        old_hp: int = self.current_health
        self.current_health = max(0, self.current_health - amount)
        actual_damage: int = old_hp - self.current_health
        
        self.damage_tint_time_left = 300
        self.tint_effect.setEnabled(True)
        self.tint_effect.setStrength(0.85)

        if self.health_bar is not None:
            self.health_bar.on_damage_taken(actual_damage, self.current_health, old_hp)

        from pytoningans.core.settings import SettingsManager
        if self.world is not None and SettingsManager.get().settings.show_damage_numbers:
            head_pos: QPointF = self.pos() + QPointF(self.width() / 2.0, -10.0)
            self.world.spawn_damage_number(actual_damage, head_pos, is_heal=False)
        
        self._on_damage(amount)
        
        if self.current_health <= 0:
            self.die()

    def heal(self, amount: int) -> None:
        if self.is_dead or amount <= 0: return
        old_hp: int = self.current_health
        max_hp: int = self.mod_manager.max_health if self.mod_manager else 100
        self.current_health = min(max_hp, self.current_health + amount)
        actual_heal: int = self.current_health - old_hp
        if actual_heal <= 0: return

        if self.health_bar:
            self.health_bar.on_heal(actual_heal, self.current_health, old_hp)

        from pytoningans.core.settings import SettingsManager
        if self.world and SettingsManager.get().settings.show_damage_numbers:
            head_pos: QPointF = self.pos() + QPointF(self.width() / 2.0, -10.0)
            self.world.spawn_damage_number(actual_heal, head_pos, is_heal=True)
            
    def jump(self) -> None:
        if self.mod_manager is None: return
        if self.is_dead or self.mod_manager.can_fly: return
        if self.velocity_y != 0: return
        
        self.velocity_y = -self.mod_manager.jump_height
        if self.anim_sys: self.anim_sys.set_state(EntityState.JUMPING)

    def die(self) -> None:
        if self.is_dead or self.mod_manager is None: return
        self.current_health = 0
        self.is_dead = True
        self.sprite_rotation = 0.0
        if self.anim_sys: self.anim_sys.set_state(EntityState.DYING)
        self._target_pos = None

        if self.health_bar is not None:
            self.health_bar.on_die()
        
        death_type: DeathAnimation = self.mod_manager.death_animation
        target_rot: float = 0.0
        
        match death_type:
            case DeathAnimation.ROTATE_LEFT:
                target_rot = -90.0
            case DeathAnimation.ROTATE_RIGHT:
                target_rot = 90.0
            case DeathAnimation.ROTATE_LEFT_OR_RIGHT:
                target_rot = -90.0 if random.random() > 0.5 else 90.0
                
        if target_rot != 0.0:
            self._rot_anim = QVariantAnimation(self.world)
            self._rot_anim.setDuration(600)
            self._rot_anim.setStartValue(self.sprite_rotation)
            self._rot_anim.setEndValue(target_rot)
            self._rot_anim.setEasingCurve(QEasingCurve.Type.OutBounce)
            
            def _on_rot_change(val: float):
                self.sprite_rotation = val
                if self.anim_sys: self.anim_sys._update_frame() 
                
            self._rot_anim.valueChanged.connect(_on_rot_change)
            self._rot_anim.start()
        
        self._on_die()
        
        if self.mod_manager.auto_close_on_death:
            self._fade_anim = QVariantAnimation(self.world)
            self._fade_anim.setDuration(3000)
            self._fade_anim.setStartValue(1.0)
            self._fade_anim.setEndValue(0.0)
            
            self._fade_anim.valueChanged.connect(self.setOpacity)
            self._fade_anim.finished.connect(self.destroy)
            self._fade_anim.start()

    def revive(self) -> None:
        if self.mod_manager is None or not self.is_dead: return
        
        self.current_health = self.mod_manager.max_health
        self.is_dead = False

        if self.health_bar is not None:
            self.health_bar.on_revive()
        
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None
        
        if self._rot_anim is not None:
            self._rot_anim.stop()
            self._rot_anim = None
        
        self.setOpacity(1.0)
        self.sprite_rotation = 0.0
        
        anim_meta: Optional[AnimationMeta] = self.mod_manager.animations.get(EntityState.REVIVING)
        
        if anim_meta:
            total_frames: int = (anim_meta.end_frame - anim_meta.start_frame) + 1
            ms_per_frame: int = 1000 // max(1, anim_meta.fps)
            
            self.revive_time_left = total_frames * ms_per_frame
            if self.anim_sys: self.anim_sys.set_state(EntityState.REVIVING)
            
            self.locks.ai = False
            self.locks.physics = False
        else:
            if self.anim_sys: self.anim_sys.set_state(EntityState.IDLE)
        self._on_revive()

    def say(self, text: str, duration_ms: int = 4000) -> None:
        """Displays a speech bubble with the given text and notifies custom behavior."""
        if self.is_dead: return
        if self.bubble is None:
            self.bubble = SpeechBubble(self)
            
        self.bubble.speak(text, duration_ms)
        self._on_speak(text)

    def force_talk(self) -> None:
        if self.mod_manager is None: return
        if self.is_dead or not self.mod_manager.plain_dialogue: return
        
        text: str = random.choice(self.mod_manager.plain_dialogue)
        self.say(text, 4000)
            
        if self.anim_sys: self.anim_sys.set_state(EntityState.IDLE)
        self._target_pos = None

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        self._target_pos = None
        self.sprite_rotation = 0.0
        if not self.is_dead and self.anim_sys:
            self.anim_sys.set_state(EntityState.CLICKED)
        
        self.is_paused = True 
        
        menu = QMenu(self.world.view) if self.world else QMenu()
        menu.addAction("Close Pet", self.destroy)
        menu.addSeparator()
        
        if not self.is_dead:
            menu.addAction("Talk To", self.force_talk)
            menu.addAction("Force Jump", self.jump)
            menu.addAction("Kill Pet", self.die)
        else:
            menu.addAction("Revive Pet", self.revive)
        
        if self.is_dead:
            if self._fade_anim and self._fade_anim.state() == QVariantAnimation.State.Running:
                self._fade_anim.pause()
            if self._rot_anim and self._rot_anim.state() == QVariantAnimation.State.Running:
                self._rot_anim.pause()
            
        menu.exec(event.screenPos())
        
        self.is_paused = False
        if not self.is_dead: return
        if self._fade_anim and self._fade_anim.state() == QVariantAnimation.State.Paused:
            self._fade_anim.resume()
        if self._rot_anim and self._rot_anim.state() == QVariantAnimation.State.Paused:
            self._rot_anim.resume()

    def _on_die(self) -> None:
        if (
            self.mod_manager is None
            or self.mod_manager.custom_behavior is None
        ):
            return
        
        behavior: BaseBehavior = self.mod_manager.custom_behavior
        if not isinstance(behavior, BaseEntityBehavior): return
        
        pet_api = cast(IEntity, self)
        behavior.on_death(pet_api)
    
    def _on_revive(self) -> None:
        if (
            self.mod_manager is None
            or self.mod_manager.custom_behavior is None
        ):
            return
        
        behavior: BaseBehavior = self.mod_manager.custom_behavior
        if not isinstance(behavior, BaseEntityBehavior): return
        
        pet_api = cast(IEntity, self)
        behavior.on_revive(pet_api)

    def _on_speak(self, text: str) -> None:
        if (
            self.mod_manager is None
            or self.mod_manager.custom_behavior is None
        ):
            return
        behavior: BaseBehavior = self.mod_manager.custom_behavior
        if not isinstance(behavior, BaseEntityBehavior): return
        try:
            behavior.on_speak(cast(IEntity, self), text)
        except Exception as e:
            print(f"Custom Entity on_speak Error: {e}")

    def _on_damage(self, amount: int) -> None:
        if (
            self.mod_manager is None
            or self.mod_manager.custom_behavior is None
        ):
            return
        behavior: BaseBehavior = self.mod_manager.custom_behavior
        if not isinstance(behavior, BaseEntityBehavior): return
        try:
            behavior.on_damage(cast(IEntity, self), amount)
        except Exception as e:
            print(f"Custom Entity on_damage Error: {e}")

    def destroy(self) -> None:
        if self.health_bar is not None:
            self.health_bar.detach_signals()
            self.health_bar = None
        if (
            self.entity_manager is not None
            and self in self.entity_manager.active_entities
        ):
            self.entity_manager.remove_entity(self)
        if self.ai_sys is not None:
            self.ai_sys.entity = None
        super().destroy()
        self.entity_manager = None


class BaseStructure(BaseEntity):
    """Static or animated environmental objects."""
    def __init__(
        self, start_x: float, start_y: float,
        mod_manager: Optional[ModManager], world: Optional[WorldOverlay]
    ) -> None:
        super().__init__(start_x, start_y, mod_manager, world)
        
        #? Structures usually ignore gravity by default unless specified
        self.locks.physics = False

    def toggle_active(self) -> None:
        """Toggles between IDLE and ACTIVE operational states, updating components."""
        new_state = (
            StructureState.IDLE.value
            if self.state == StructureState.ACTIVE.value
            else StructureState.ACTIVE.value
        )
        self.state = new_state
        teleport_comp = self.get_component("teleportation")
        if isinstance(teleport_comp, TeleportationComponent):
            teleport_comp.enabled = (new_state == StructureState.ACTIVE.value)

    def _set_linked_portal(self, target: Optional[BaseStructure]) -> None:
        teleport_comp = self.get_component("teleportation")
        if isinstance(teleport_comp, TeleportationComponent):
            teleport_comp.linked_portal = target
            if target is not None and target.has_component("teleportation"):
                target_comp = target.get_component("teleportation")
                if isinstance(target_comp, TeleportationComponent):
                    target_comp.linked_portal = self

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        self.is_paused = True
        menu = QMenu(self.world.view) if self.world else QMenu()
        
        # Close Structure
        menu.addAction("Close Structure", self.destroy)
        menu.addSeparator()
        
        # Flip Horizontally
        menu.addAction("Flip Horizontally", self.flip)
        
        # Toggle Active
        status_text = "Deactivate" if self.state == StructureState.ACTIVE.value else "Activate"
        menu.addAction(f"{status_text} Structure", self.toggle_active)
        
        menu.addSeparator()
        
        # Component-specific actions
        teleport_comp = self.get_component("teleportation")
        if isinstance(teleport_comp, TeleportationComponent):
            portal_menu = menu.addMenu("Change Linked Portal")
            
            # Unlink option
            unlink_action = portal_menu.addAction("None (Unlinked)")
            if teleport_comp.linked_portal is None:
                unlink_action.setCheckable(True)
                unlink_action.setChecked(True)
            unlink_action.triggered.connect(lambda: self._set_linked_portal(None))
            portal_menu.addSeparator()
            
            # Available other structures
            other_structures: list[BaseStructure] = []
            if self.world is not None and self.world.manager is not None:
                for struct in self.world.manager.active_structures:
                    if struct is not self:
                        other_structures.append(struct)
                        
            if other_structures:
                for idx, other in enumerate(other_structures):
                    other_name = (
                        other.mod_manager.current_mod_name
                        if other.mod_manager and other.mod_manager.current_mod_name
                        else (other.mod_manager.current_mod_folder if other.mod_manager else f"Structure #{idx + 1}")
                    )
                    world_info = (
                        f"World {self.world.manager.active_worlds.index(other.world) + 1}"
                        if self.world is not None and other.world in self.world.manager.active_worlds
                        else ""
                    )
                    label = f"{other_name} ({world_info} @ {int(other.x())}, {int(other.y())})"
                    action = portal_menu.addAction(label)
                    action.setCheckable(True)
                    if teleport_comp.linked_portal is other:
                        action.setChecked(True)
                    action.triggered.connect(lambda checked=False, target=other: self._set_linked_portal(target))
            else:
                empty_action = portal_menu.addAction("No other structures available")
                empty_action.setEnabled(False)
                
            menu.addAction("Remove Teleportation Component", lambda: self.remove_component("teleportation"))
        else:
            menu.addAction("Add Teleportation Component", lambda: self.attach_teleportation())
            
        menu.exec(event.screenPos())
        self.is_paused = False

    def update_systems(self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None) -> None:
        super().update_systems(dt, centers)
        
        if self.mod_manager is None or self.mod_manager.custom_behavior is None:
            return
        
        behavior: BaseBehavior = self.mod_manager.custom_behavior
        if isinstance(behavior, BaseStructureBehavior):
            try:
                behavior.on_update(cast(IStructure, self), dt)
            except Exception as e:
                print(f"Custom Structure on_update Error: {e}")
                
            # Check interaction collision with living entities
            if self.world is not None:
                struct_rect = self.sceneBoundingRect()
                for ent in list(self.world.active_entities):
                    if not ent.is_dead and struct_rect.intersects(ent.sceneBoundingRect()):
                        try:
                            behavior.on_interact(cast(IStructure, self), cast(IEntity, ent))
                        except Exception as e:
                            print(f"Custom Structure on_interact Error: {e}")
    
    def attach_teleportation(
        self,
        target_world: Optional[WorldOverlay] = None,
        exit_offset_x: float = 80.0,
        exit_offset_y: float = 0.0
    ) -> TeleportationComponent:
        _target_world: Optional[WorldOverlay] = target_world or self.world
        comp = TeleportationComponent(self, _target_world, exit_offset_x, exit_offset_y)
        self.add_component(comp)
        return comp

    def destroy(self) -> None:
        self._on_destroy()
        
        # Clean up any other teleport components linking to this structure
        if self.world is not None and self.world.manager is not None:
            for other in list(self.world.manager.active_structures):
                if other is not self:
                    other_comp = other.get_component("teleportation")
                    if isinstance(other_comp, TeleportationComponent) and other_comp.linked_portal is self:
                        other_comp.linked_portal = None
            self.world.manager.remove_entity(self)
        elif self.world is not None:
            if self in self.world.active_structures:
                self.world.active_structures.remove(self)
            if self.scene():
                self.scene().removeItem(self)
                
        super().destroy()

    def _on_destroy(self) -> None:
        if self.mod_manager is None or self.mod_manager.custom_behavior is None:
            return
        behavior: BaseBehavior = self.mod_manager.custom_behavior
        if isinstance(behavior, BaseStructureBehavior):
            try:
                behavior.on_destroy(cast(IStructure, self))
            except Exception as e:
                print(f"Custom Structure on_destroy Error: {e}")
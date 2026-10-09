from __future__ import annotations
import random
from typing import Optional, TYPE_CHECKING, cast

from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsColorizeEffect, QMenu
from PySide6.QtCore import QPointF, QRect, QRectF, QVariantAnimation, QEasingCurve, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsSceneMouseEvent, QGraphicsSceneContextMenuEvent

from pytoningans.core.components.base_component import BaseComponent
from pytoningans.core.constants import AnimationMeta, EntityState, SystemLocks, DeathAnimation
from pytoningans.core.entity.animation import AnimationSystem
from pytoningans.core.entity.physics import PhysicsSystem
from pytoningans.core.entity.ai_brain import AISystem
from pytoningans.core.entity.speech_bubble import SpeechBubble
from pytoningans.core.api import (
    IEntity, Pos2D, BaseEntityBehavior, BaseStructureBehavior,
    BaseBehavior, IStructure
)
from pytoningans.core.world import WorldOverlay

if TYPE_CHECKING:
    from pytoningans.core.mod_manager import ModManager
    from pytoningans.core.world import WorldOverlay
    from pytoningans.core.entity_manager import EntityManager
    from pytoningans.core.components.base_component import BaseComponent


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
        
        self.state: EntityState = EntityState.IDLE
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
    ):
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

    def on_moved(self) -> None:
        if self.bubble: self.bubble.update_position()

    def take_damage(self, amount: int) -> None:
        if self.is_dead: return
        self.current_health -= amount
        
        self.damage_tint_time_left = 300
        self.tint_effect.setEnabled(True)
        self.tint_effect.setStrength(0.85)
        
        if self.current_health <= 0:
            self.die()
            
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

    def force_talk(self) -> None:
        if self.mod_manager is None: return
        if self.is_dead or not self.mod_manager.plain_dialogue: return
        
        if self.bubble is None:
            self.bubble = SpeechBubble(self)
            
        text: str = random.choice(self.mod_manager.plain_dialogue)
        self.bubble.speak(text, 4000)
            
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

    def destroy(self) -> None:
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
    ):
        super().__init__(start_x, start_y, mod_manager, world)
        
        #? Structures usually ignore gravity by default unless specified
        self.locks.physics = False
    
    def update_systems(self, dt: int, centers: Optional[dict[BaseEntity, QPointF]] = None) -> None:
        super().update_systems(dt, centers)
        
        if (
            self.mod_manager is None
            or self.mod_manager.custom_behavior is None
        ):
            return
        
        behavior: BaseBehavior = self.mod_manager.custom_behavior
        if not isinstance(behavior, BaseStructureBehavior): return
        
        struct_api: IStructure = cast(IStructure, self)
        behavior.on_update(struct_api, dt)
    
    def attach_teleportation(
        self,
        target_world: Optional[WorldOverlay] = None,
        exit_offset_x: float = 80.0,
        exit_offset_y: float = 0.0
    ):
        from pytoningans.core.components.teleportation import TeleportationComponent
        tw: Optional[WorldOverlay] = target_world or self.world
        comp = TeleportationComponent(self, tw, exit_offset_x, exit_offset_y)
        self.add_component(comp)
        return comp
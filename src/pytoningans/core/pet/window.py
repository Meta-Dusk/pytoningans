from __future__ import annotations

import random
from typing import Optional, TYPE_CHECKING, cast

from PySide6.QtWidgets import QMenu, QGraphicsColorizeEffect, QGraphicsPixmapItem
from PySide6.QtCore import (
    QRectF, Qt, QPoint, QRect, QVariantAnimation, QEasingCurve, QPointF
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsSceneMouseEvent, QGraphicsSceneContextMenuEvent

from pytoningans.core.constants import AnimationMeta, DeathAnimation, PetState, SystemLocks
from pytoningans.core.pet.animation import AnimationSystem
from pytoningans.core.pet.physics import PhysicsSystem
from pytoningans.core.pet.ai_brain import AISystem
from pytoningans.core.pet.speech_bubble import SpeechBubble
from pytoningans.core.api import IPet

if TYPE_CHECKING:
    from pytoningans.core.mod_manager import ModManager
    from pytoningans.core.pet_manager import PetManager, WorldOverlay
    from pytoningans.core.api import Pos2D

class PetWindow(QGraphicsPixmapItem):
    """The core Entity holding shared state and routing Scene events."""
    def __init__(
        self, start_x: int, start_y: int,
        mod_manager: Optional[ModManager] = None,
        pet_manager: Optional[PetManager] = None,
        world: Optional['WorldOverlay'] = None
    ) -> None:
        super().__init__()
        self.mod_manager: Optional[ModManager] = mod_manager
        self.pet_manager: Optional[PetManager] = pet_manager
        self.world: Optional['WorldOverlay'] = world
        
        # --- Shared Entity Data ---
        self.state: PetState = PetState.IDLE
        self.facing_left: bool = False
        self.sprite_rotation: float = 0.0
        self.is_dead: bool = False
        self.is_paused: bool = False
        if self.mod_manager:
            self.current_health: int = self.mod_manager.max_health
        
        self.damage_tint_time_left: int = 0
        
        self.velocity_y: float = 0.0
        self._target_pos: Optional[QPointF] = None
        self._drag_start_pos: Optional[QPointF] = None
        self._mouse_down_pos: Optional[QPointF] = None
        
        self.current_hitbox: QRect = QRect()
        self.current_attack_hitbox: QRect = QRect()

        # --- Initialization ---
        self._setup_ui(start_x, start_y)
        
        self.anim_sys: Optional[AnimationSystem] = None
        self.physics_sys: Optional[PhysicsSystem] = None
        self.ai_sys: Optional[AISystem] = None
        self.bubble: Optional[SpeechBubble] = None
        self.locks: SystemLocks = SystemLocks()
        self.revive_time_left: int = 0
        self._fade_anim: Optional[QVariantAnimation] = None
        self._rot_anim: Optional[QVariantAnimation] = None
        
        self._init_systems()

    @property
    def is_interactable(self) -> bool:
        return self.state not in (PetState.DRAG, PetState.INTERACT) and not self.is_dead
    
    @property
    def target_pos(self) -> Optional[QPointF]:
        """The engine reads this as a standard QPoint."""
        return self._target_pos

    @target_pos.setter
    def target_pos(self, pos: Optional[Pos2D]) -> None:
        """Intercepts the modder's Pos2D and converts it to a QPointF."""
        if pos is None:
            self._target_pos = None
        else:
            self._target_pos = QPointF(pos.x, pos.y)
            
    # --- QWidget Compatibility Shims for AI & Physics ---
    def geometry(self) -> QRect:
        return self.sceneBoundingRect().toRect()
        
    def width(self) -> int:
        return int(self.boundingRect().width())
        
    def height(self) -> int:
        return int(self.boundingRect().height())
        
    def screen(self):
        return self.world.target_screen if self.world else None
        
    def raise_(self) -> None:
        self.setZValue(self.zValue() + 0.1)
    
    def _init_systems(self) -> None:
        self.anim_sys = AnimationSystem(self)
        self.physics_sys = PhysicsSystem(self)
        self.ai_sys = AISystem(self)
        self.anim_sys.attack_frame_hit.connect(self.ai_sys.process_combat)
    
    def _setup_ui(self, x: int, y: int) -> None:
        self.setPos(x, y)
        
        # Apply the colorize effect directly to the item
        self.tint_effect = QGraphicsColorizeEffect()
        self.tint_effect.setColor(QColor(255, 0, 0)) # Pure Red
        self.tint_effect.setEnabled(False)
        self.setGraphicsEffect(self.tint_effect)
    
    def update_systems(self, dt: int, centers: Optional[dict[PetWindow, QPointF]] = None) -> None:
        """Called every frame by the WorldOverlay's loop."""
        if self.is_paused: return

        if self.bubble: self.bubble.tick(dt)
        
        if self.revive_time_left > 0:
            self.revive_time_left -= dt
            if self.revive_time_left <= 0:
                if self.anim_sys: self.anim_sys.set_state(PetState.IDLE)
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
            if self.anim_sys: self.anim_sys.update(dt)
            if self.physics_sys: self.physics_sys.update(dt, centers)
            return
            
        if self.locks.ai and self.ai_sys: self.ai_sys.update(dt)
        if self.locks.physics and self.physics_sys: self.physics_sys.update(dt, centers)
        if self.locks.animation and self.anim_sys: self.anim_sys.update(dt)
    
    # --- Core Actions ---
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
        if self.anim_sys: self.anim_sys.set_state(PetState.JUMPING)

    def die(self) -> None:
        if self.is_dead or self.mod_manager is None: return
        self.current_health = 0
        self.is_dead = True
        self.sprite_rotation = 0.0
        if self.anim_sys: self.anim_sys.set_state(PetState.DYING)
        self._target_pos = None
        
        death_type: DeathAnimation = self.mod_manager.death_animation
        target_rot = 0.0
        
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
        
        # --- MODDERS API HOOK ---
        self._on_die()
        
        if self.mod_manager.auto_close_on_death:
            # QVariantAnimation handles opacity since Graphics Items aren't QObjects
            self._fade_anim = QVariantAnimation(self.world)
            self._fade_anim.setDuration(3000)
            self._fade_anim.setStartValue(1.0)
            self._fade_anim.setEndValue(0.0)
            
            self._fade_anim.valueChanged.connect(self.setOpacity)
            self._fade_anim.finished.connect(self.close_pet)
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
        
        anim_meta: Optional[AnimationMeta] = self.mod_manager.animations.get(PetState.REVIVING)
        
        if anim_meta:
            total_frames: int = (anim_meta.end_frame - anim_meta.start_frame) + 1
            ms_per_frame: int = 1000 // max(1, anim_meta.fps)
            
            self.revive_time_left = total_frames * ms_per_frame
            if self.anim_sys: self.anim_sys.set_state(PetState.REVIVING)
            
            self.locks.ai = False
            self.locks.physics = False
        else:
            if self.anim_sys: self.anim_sys.set_state(PetState.IDLE)
        self._on_revive()

    # --- Modding API Hooks ---
    def _on_die(self) -> None:
        if self.mod_manager is None: return
        if self.mod_manager.custom_behavior:
            pet_api = cast(IPet, self)
            self.mod_manager.custom_behavior.on_death(pet_api)
    
    def _on_revive(self) -> None:
        if self.mod_manager is None: return
        if self.mod_manager.custom_behavior:
            pet_api: IPet = cast(IPet, self)
            self.mod_manager.custom_behavior.on_revive(pet_api)
    
    # --- Graphics Scene Events ---
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.is_dead and self.anim_sys:
                self.anim_sys.set_state(PetState.DRAG)
            self.locks.physics = False
            event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        # Calculate the exact distance moved since the last hardware tick
        delta: QPointF = event.scenePos() - event.lastScenePos()
        
        new_x: float = self.x() + delta.x()
        new_y: float = self.y() + delta.y()
        
        # Constrain the pet within the world's scene boundaries
        if self.world is not None:
            bounds: QRectF = self.world.scene.sceneRect()
            new_x = max(bounds.left(), min(new_x, bounds.right() - self.width()))
            new_y = max(bounds.top(), min(new_y, bounds.bottom() - self.height()))
        
        self.setPos(new_x, new_y)
        if self.bubble: self.bubble.update_position()
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.is_dead and self.anim_sys:
                self.anim_sys.set_state(PetState.IDLE)
            self.locks.physics = True
            event.accept()

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        self._target_pos = None
        self.sprite_rotation = 0.0
        if not self.is_dead and self.anim_sys:
            self.anim_sys.set_state(PetState.CLICKED)
        
        self.is_paused = True 
        
        menu = QMenu(self.world.view) if self.world else QMenu()
        menu.addAction("Close Pet", self.close_pet)
        menu.addSeparator()
        
        if not self.is_dead:
            menu.addAction("Talk To", self.force_talk)
            menu.addAction("Force Jump", self.jump)
            menu.addAction("Kill Pet", self.die)
        else:
            menu.addAction("Revive Pet", self.revive)
        
        if self.is_dead:
            if (self._fade_anim is not None and
                self._fade_anim.state() == QVariantAnimation.State.Running):
                self._fade_anim.pause()
            if (self._rot_anim is not None and
                self._rot_anim.state() == QVariantAnimation.State.Running):
                self._rot_anim.pause()
            
        menu.exec(event.screenPos())
        
        self.is_paused = False
        if not self.is_dead: return
        if (self._fade_anim is not None and
            self._fade_anim.state() == QVariantAnimation.State.Paused):
            self._fade_anim.resume()
            
        if (self._rot_anim is not None and
            self._rot_anim.state() == QVariantAnimation.State.Paused):
            self._rot_anim.resume()
    
    # --- Other Events ---
    def close_pet(self) -> None:
        if self.pet_manager:
            self.pet_manager.remove_pet(self)
            
        if self.bubble:
            self.bubble.deleteLater()
        
        if self.anim_sys: self.anim_sys.pet = None
        if self.physics_sys: self.physics_sys.pet = None
        if self.ai_sys: self.ai_sys.pet = None
        
        self.mod_manager = None
        self.pet_manager = None
        self.world = None
    
    def force_talk(self) -> None:
        if self.mod_manager is None: return
        if self.is_dead or not self.mod_manager.plain_dialogue: return
        
        if self.bubble is None:
            self.bubble = SpeechBubble(self)
            
        text: str = random.choice(self.mod_manager.plain_dialogue)
        self.bubble.speak(text, 4000)
            
        if self.anim_sys: self.anim_sys.set_state(PetState.IDLE)
        self._target_pos = None
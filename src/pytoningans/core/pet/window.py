from __future__ import annotations

from typing import Optional, TYPE_CHECKING, cast

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu, QGraphicsColorizeEffect
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent, QContextMenuEvent, QColor, QMoveEvent

from pytoningans.core.constants import WINDOW_CFG, AnimationMeta, PetState, SystemLocks
from pytoningans.core.pet.animation import AnimationSystem
from pytoningans.core.pet.physics import PhysicsSystem
from pytoningans.core.pet.ai_brain import AISystem
from pytoningans.core.pet.speech_bubble import SpeechBubble
from pytoningans.core.api import IPet

if TYPE_CHECKING:
    from pytoningans.core.mod_manager import ModManager
    from pytoningans.core.pet_manager import PetManager
    from pytoningans.core.api import Pos2D

class PetWindow(QWidget):
    """The core Entity holding shared state and routing OS events."""
    def __init__(
        self, start_x: int, start_y: int,
        mod_manager: ModManager, pet_manager: PetManager
    ) -> None:
        super().__init__()
        self.mod_manager: ModManager = mod_manager
        self.pet_manager: PetManager = pet_manager
        
        # --- Shared Entity Data ---
        self.state: PetState = PetState.IDLE
        self.facing_left: bool = False
        self.rotation: float = 0.0
        self.is_dead: bool = False
        self.is_paused: bool = False
        self.current_health: int = self.mod_manager.max_health
        
        self.damage_tint_time_left: int = 0
        
        self.velocity_y: float = 0.0
        self._target_pos: Optional[QPoint] = None
        self._drag_offset: Optional[QPoint] = None

        # --- Initialization ---
        self._setup_ui(start_x, start_y)
        
        self.anim_sys = AnimationSystem(self)
        self.physics_sys = PhysicsSystem(self)
        self.ai_sys = AISystem(self)
        self.bubble = SpeechBubble(self)
        self.locks = SystemLocks()
        self.revive_time_left: int = 0

    @property
    def is_interactable(self) -> bool:
        return self.state not in (PetState.DRAG, PetState.INTERACT) or not self.is_dead
    
    @property
    def target_pos(self) -> Optional[QPoint]:
        """The engine reads this as a standard QPoint."""
        return self._target_pos

    @target_pos.setter
    def target_pos(self, pos: Optional[Pos2D]) -> None:
        """Intercepts the modder's Pos2D and converts it to a QPoint."""
        if pos is None:
            self._target_pos = None
        else:
            self._target_pos = QPoint(pos.x, pos.y)

    def _setup_ui(self, x: int, y: int) -> None:
        flags: Qt.WindowType = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool)
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(WINDOW_CFG.default_width, WINDOW_CFG.default_height)
        self.move(x, y)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.sprite_label = QLabel(WINDOW_CFG.placeholder_text, self)
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sprite_label.setStyleSheet(WINDOW_CFG.placeholder_style)
        
        # Apply the colorize effect
        self.tint_effect = QGraphicsColorizeEffect(self)
        self.tint_effect.setColor(QColor(255, 0, 0)) # Pure Red
        self.tint_effect.setStrength(0.0) # 0.0 means completely invisible
        self.sprite_label.setGraphicsEffect(self.tint_effect)
        
        layout.addWidget(self.sprite_label)
    
    def update_systems(self, dt: int) -> None:
        """Called every frame by the PetManager's global tick."""
        if self.is_paused: return
        
        if self.revive_time_left > 0:
            self.revive_time_left -= dt
            if self.revive_time_left <= 0:
                self.anim_sys.set_state(PetState.IDLE)
                self.locks.ai = True
                self.locks.physics = True
                
        # Handle the red damage flash fade-out
        if self.damage_tint_time_left > 0:
            self.damage_tint_time_left -= dt
            if self.damage_tint_time_left <= 0:
                self.tint_effect.setStrength(0.0)
            else:
                # Calculate a linear fade from 0.7 (70% opacity) down to 0.0 over 300ms
                fade_strength = 0.7 * (self.damage_tint_time_left / 300.0)
                self.tint_effect.setStrength(fade_strength)
            
        if self.is_dead:
            # Let the dying animation finish and allow physics to drop the pet to the ground
            self.anim_sys.update(dt)
            self.physics_sys.update(dt)
            return
            
        if self.locks.ai: self.ai_sys.update(dt)
        if self.locks.physics: self.physics_sys.update(dt)
        if self.locks.animation: self.anim_sys.update(dt)
    
    # --- Core Actions ---
    def take_damage(self, amount: int) -> None:
        """Applies damage, flashes red, and kills the pet if health <= 0."""
        if self.is_dead: return
        self.current_health -= amount
        
        self.damage_tint_time_left = 300
        self.tint_effect.setStrength(0.85)
        
        if self.current_health <= 0:
            self.die()
            
    def jump(self) -> None:
        if self.is_dead or self.mod_manager.can_fly: return
        if self.velocity_y != 0: return
        
        self.velocity_y = -self.mod_manager.jump_height
        self.anim_sys.set_state(PetState.JUMPING)

    def die(self) -> None:
        if self.is_dead: return
        self.current_health = 0
        self.is_dead = True
        self.rotation = 0.0
        self.anim_sys.set_state(PetState.DYING)
        self._target_pos = None
        
        # --- MODDERS API HOOK ---
        self._on_die()

    def _on_die(self) -> None:
        """Modding API hook."""
        if self.mod_manager.custom_behavior:
            pet_api = cast(IPet, self)
            self.mod_manager.custom_behavior.on_death(pet_api)

    def revive(self) -> None:
        if not self.is_dead: return
        
        self.current_health = self.mod_manager.max_health
        self.is_dead = False
        
        anim_meta: AnimationMeta | None = self.mod_manager.animations.get(PetState.REVIVING)
        
        if anim_meta:
            # Calculate: total_frames * ms_per_frame
            total_frames: int = (anim_meta.end_frame - anim_meta.start_frame) + 1
            ms_per_frame: int = 1000 // max(1, anim_meta.fps)
            
            self.revive_time_left = total_frames * ms_per_frame
            self.anim_sys.set_state(PetState.REVIVING)
            
            # Lock systems so the pet doesn't slide or attack while standing up
            self.locks.ai = False
            self.locks.physics = False
        else:
            self.anim_sys.set_state(PetState.IDLE)
        self._on_revive()

    def _on_revive(self) -> None:
        """Modding API hook."""
        if self.mod_manager.custom_behavior:
            pet_api: IPet = cast(IPet, self)
            self.mod_manager.custom_behavior.on_revive(pet_api)

    # --- OS Events ---
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            if not self.is_dead:
                self.anim_sys.set_state(PetState.DRAG)
            self.locks.physics = False
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            if not self.is_dead:
                self.anim_sys.set_state(PetState.IDLE)
            self.locks.physics = True
            event.accept()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Triggered automatically on right-click."""
        self._target_pos = None
        self.rotation = 0.0
        if not self.is_dead: self.anim_sys.set_state(PetState.CLICKED)
        
        # Freeze the systems while the menu is open
        self.is_paused = True 
        
        menu = QMenu(self)
        menu.addAction("Close Pet", self._close_pet)
        menu.addSeparator()
        
        if not self.is_dead:
            menu.addAction("Force Jump", self.jump)
            menu.addAction("Kill Pet", self.die)
        else:
            menu.addAction("Revive Pet", self.revive)
            
        menu.exec(event.globalPos())
        
        # Unfreeze after the user clicks away or selects an option
        self.is_paused = False
    
    # --- Other Events ---
    def _close_pet(self) -> None:
        """Safely unregisters the window before destroying it."""
        self.bubble.close()
        self.pet_manager.remove_pet(self)
        self.close()
    
    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        self.bubble.update_position()
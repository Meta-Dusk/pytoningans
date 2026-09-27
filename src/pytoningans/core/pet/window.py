from __future__ import annotations

from typing import Optional, TYPE_CHECKING, cast

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent, QContextMenuEvent

from pytoningans.core.constants import WINDOW_CFG, PetState
from pytoningans.core.pet.animation import AnimationSystem
from pytoningans.core.pet.physics import PhysicsSystem
from pytoningans.core.pet.ai_brain import AISystem
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
        self.is_dead: bool = False
        self.current_health: int = self.mod_manager.max_health
        
        self.velocity_y: float = 0.0
        self.enable_gravity: bool = True
        self._target_pos: Optional[QPoint] = None
        self._drag_offset: Optional[QPoint] = None

        # --- Initialization ---
        self._setup_ui(start_x, start_y)
        
        self.anim_sys = AnimationSystem(self)
        self.physics_sys = PhysicsSystem(self)
        self.ai_sys = AISystem(self)

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
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(WINDOW_CFG.default_width, WINDOW_CFG.default_height)
        self.move(x, y)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.sprite_label = QLabel(WINDOW_CFG.placeholder_text, self)
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sprite_label.setStyleSheet(WINDOW_CFG.placeholder_style)
        layout.addWidget(self.sprite_label)

    # --- Core Actions ---
    def jump(self) -> None:
        if self.is_dead or self.mod_manager.can_fly: return
        if self.velocity_y != 0: return
        
        self.velocity_y = -self.mod_manager.jump_height
        self.anim_sys.set_state(PetState.JUMPING)

    def die(self) -> None:
        if self.is_dead: return
        self.current_health = 0
        self.is_dead = True
        self.anim_sys.set_state(PetState.DYING)
        
        self.ai_sys.timer.stop()
        self._target_pos = None
        
        # --- MODDERS API HOOK ---
        if self.mod_manager.custom_behavior:
            pet_api = cast(IPet, self)
            self.mod_manager.custom_behavior.on_death(pet_api)

    def revive(self) -> None:
        if not self.is_dead: return
        self.current_health = self.mod_manager.max_health
        self.is_dead = False
        self.anim_sys.set_state(PetState.IDLE)
        self.ai_sys.timer.start(2500)
        
        # --- MODDERS API HOOK ---
        if self.mod_manager.custom_behavior:
            pet_api = cast(IPet, self)
            self.mod_manager.custom_behavior.on_revive(pet_api)

    # --- OS Events ---
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            if not self.is_dead:
                self.anim_sys.set_state(PetState.DRAG)
            self.enable_gravity = False
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
            self.enable_gravity = True
            event.accept()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Triggered automatically on right-click."""
        self._target_pos = None
        if not self.is_dead: self.anim_sys.set_state(PetState.IDLE)
        self.ai_sys.timer.stop()
        
        menu = QMenu(self)
        menu.addAction("Close Pet", self._close_pet)
        menu.addSeparator()
        
        if not self.is_dead:
            menu.addAction("Force Jump", self.jump)
            menu.addAction("Kill Pet", self.die)
        else:
            menu.addAction("Revive Pet", self.revive)
            
        menu.exec(event.globalPos())
        if not self.is_dead: self.ai_sys.timer.start()

    def _close_pet(self) -> None:
        """Safely stops timers and unregisters the window before destroying it."""
        self.anim_sys.timer.stop()
        self.pet_manager.remove_pet(self)
        self.close()
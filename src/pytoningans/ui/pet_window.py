from __future__ import annotations
import random, math

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import (
    QMouseEvent, QPixmap, QContextMenuEvent, QAction, QGuiApplication,
    QTransform
)

from pytoningans.core.constants import WINDOW_CFG, PetState
from pytoningans.core.mod_manager import ModManager

if TYPE_CHECKING:
    from pytoningans.core.pet_manager import PetManager

class PetWindow(QWidget):
    def __init__(
        self, start_x: int, start_y: int,
        mod_manager: ModManager, pet_manager: PetManager
    ) -> None:
        super().__init__()
        self.mod_manager: ModManager = mod_manager
        self.pet_manager = pet_manager
        self._drag_offset: Optional[QPoint] = None
        
        # Animation state
        self._current_state: PetState = PetState.IDLE
        self._current_frame: int = 0
        self._facing_left: bool = False

        # Physics & AI parameters
        self.velocity_y: float = 0.0
        self.gravity: float = 0.8
        self.move_speed: float = 2.0

        # AI State Machine variables
        self._target_pos: Optional[QPoint] = None
        self._interaction_cooldown: int = 0
        self._interact_ticks_left: int = 0

        self._setup_window(start_x, start_y)
        self._setup_ui()
        self._setup_animation()
        self._setup_physics()
        self._setup_ai()
    
    # --- Animations and UI ---
    def _setup_window(self, x: int, y: int) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool 
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(WINDOW_CFG.default_width, WINDOW_CFG.default_height)
        self.move(x, y)

    def _setup_ui(self) -> None:
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.sprite_label: QLabel = QLabel(WINDOW_CFG.placeholder_text, self)
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sprite_label.setStyleSheet(WINDOW_CFG.placeholder_style)
        layout.addWidget(self.sprite_label)

    def _setup_animation(self) -> None:
        self._anim_timer: QTimer = QTimer(self)
        self._anim_timer.timeout.connect(self._update_frame)
        
        # Dynamically set initial speed based on IDLE state
        meta = self.mod_manager.animations.get(self._current_state)
        interval = 1000 // max(1, meta.fps) if meta else 100
        
        self._anim_timer.start(interval)
        self._update_frame()

    def _update_frame(self) -> None:
        self._current_frame += 1
        frame: Optional[QPixmap] = self.mod_manager.get_frame(
            self._current_state, self._current_frame
        )

        if frame is not None:
            # Mirror the frame horizontally if facing left
            if self._facing_left:
                frame = frame.transformed(QTransform().scale(-1, 1))

            self.sprite_label.setPixmap(frame)
            self.sprite_label.setStyleSheet("")
            self.sprite_label.setText("")
            self.resize(frame.width(), frame.height())

    def set_state(self, new_state: PetState) -> None:
        """Helper to cleanly swap animation states and update speed dynamically."""
        if self._current_state is not new_state:
            self._current_state = new_state
            self._current_frame = 0
            
            # Fetch the new speed and update the running timer
            meta = self.mod_manager.animations.get(new_state)
            if meta:
                self._anim_timer.setInterval(1000 // max(1, meta.fps))
                
            self._update_frame()

    # --- Mouse & Context Menu Events ---
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.set_state(PetState.DRAG)
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            self.set_state(PetState.IDLE)
            event.accept()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Triggered automatically on right-click."""
        # Force the pet to stop and clear its current destination
        self._target_pos = None
        self.set_state(PetState.IDLE)
        
        # Pause AI decisions so it doesn't walk away while the menu is open
        self._ai_timer.stop()
        
        context_menu = QMenu(self)
        close_action = QAction("Close Pet", self)
        close_action.triggered.connect(self._close_pet)
        context_menu.addAction(close_action)
        
        # exec() blocks the local flow until the user clicks or dismisses the menu
        context_menu.exec(event.globalPos())
        
        # Resume AI once the menu is closed
        self._ai_timer.start()

    def _close_pet(self) -> None:
        """Safely stops timers and unregisters the window before destroying it."""
        self._anim_timer.stop()
        self.pet_manager.remove_pet(self)
        self.close()
    
    # --- Physics & Movement Execution ---
    def _setup_physics(self) -> None:
        """Initializes a 60 FPS physics loop for movement and gravity."""
        self._physics_timer: QTimer = QTimer(self)
        self._physics_timer.timeout.connect(self._physics_tick)
        self._physics_timer.start(16) # ~60 FPS

    def _physics_tick(self) -> None:
        if self._current_state is PetState.DRAG:
            self.velocity_y = 0
            return

        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        if not screen:
            return

        ground_y = screen.availableGeometry().bottom()

        # Apply Gravity for Grounded Pets
        if not self.mod_manager.can_fly:
            pet_bottom = self.geometry().bottom()
            if pet_bottom < ground_y:
                self.velocity_y += self.gravity
                new_y = int(self.y() + self.velocity_y)
                if new_y + self.height() > ground_y:
                    new_y = ground_y - self.height() + 1
                self.move(self.x(), new_y)
            else:
                self.velocity_y = 0

        # Count down interaction state duration
        if self._current_state is PetState.INTERACT:
            self._interact_ticks_left -= 1
            if self._interact_ticks_left <= 0:
                self.set_state(PetState.IDLE)
            return

        # Check for nearby companions
        self._check_pet_interactions()

        # Handle autonomous movement toward target position
        if self._current_state is PetState.MOVING and self._target_pos is not None:
            curr_x = self.x()
            curr_y = self.y()
            target_x = self._target_pos.x()
            target_y = self._target_pos.y() if self.mod_manager.can_fly else curr_y

            dx = target_x - curr_x
            dy = target_y - curr_y
            dist = math.hypot(dx, dy)

            if dist < self.move_speed:
                # Target reached
                self.move(target_x, target_y)
                self._target_pos = None
                self.set_state(PetState.IDLE)
            else:
                # Step toward target
                step_x = int(curr_x + (dx / dist) * self.move_speed)
                step_y = int(curr_y + (dy / dist) * self.move_speed) if self.mod_manager.can_fly else curr_y

                # Turn sprite in direction of travel
                self._facing_left = (dx < 0)

                self.move(step_x, step_y)
    
    # --- AI State Machine & Proximity ---
    def _setup_ai(self) -> None:
        self._ai_timer: QTimer = QTimer(self)
        self._ai_timer.timeout.connect(self._ai_decision_tick)
        self._ai_timer.start(2500)  # Re-evaluates goal every 2.5 seconds
    
    def _ai_decision_tick(self) -> None:
        """Periodic decision maker determining if the pet should rest or explore."""
        if self._current_state in (PetState.DRAG, PetState.INTERACT):
            return

        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        if not screen:
            return

        geom = screen.availableGeometry()

        # 60% chance to roam, 40% chance to pause/idle
        if random.random() < 0.60:
            dest_x = random.randint(geom.left() + 50, geom.right() - self.width() - 50)
            if self.mod_manager.can_fly:
                dest_y = random.randint(geom.top() + 50, geom.bottom() - self.height() - 50)
            else:
                dest_y = self.y()

            self._target_pos = QPoint(dest_x, dest_y)
            self.set_state(PetState.MOVING)
        else:
            self._target_pos = None
            self.set_state(PetState.IDLE)

    def _check_pet_interactions(self) -> None:
        """Detects if another pet is nearby to trigger an interaction."""
        if self._interaction_cooldown > 0:
            self._interaction_cooldown -= 1
            return

        if self._current_state in (PetState.DRAG, PetState.INTERACT):
            return

        my_center = self.geometry().center()

        for other_pet in self.pet_manager.active_pets:
            if other_pet is self or other_pet._current_state in (PetState.DRAG, PetState.INTERACT):
                continue

            other_center = other_pet.geometry().center()
            distance = math.hypot(my_center.x() - other_center.x(), my_center.y() - other_center.y())

            # Interaction distance threshold (in pixels)
            if distance < 120:
                # Face each other
                self._facing_left = other_center.x() < my_center.x()
                other_pet._facing_left = my_center.x() < other_center.x()

                # Trigger interaction state
                self._start_interaction()
                other_pet._start_interaction()
                break

    def _start_interaction(self) -> None:
        self._target_pos = None
        self._interact_ticks_left = 180  # ~3 seconds at 60 FPS
        self._interaction_cooldown = 400  # Avoid immediately re-interacting
        self.set_state(PetState.INTERACT)
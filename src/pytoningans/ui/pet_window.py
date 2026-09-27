from __future__ import annotations
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QMouseEvent, QPixmap, QContextMenuEvent, QAction
from typing import Optional, TYPE_CHECKING

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
        
        # Animation State Tracking
        self._current_state: PetState = PetState.IDLE
        self._current_frame: int = 0
        
        self._setup_window(start_x, start_y)
        self._setup_ui()
        self._setup_animation()

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
        frame: Optional[QPixmap] = self.mod_manager.get_frame(self._current_state, self._current_frame)
        
        if frame is not None:
            self.sprite_label.setPixmap(frame)
            self.sprite_label.setStyleSheet("")
            self.sprite_label.setText("")
            
            # Snap the OS window size to the exact sprite frame dimensions
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

    # --- Mouse Events ---
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
    
    # --- Context Menu Logic ---
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Triggered automatically on right-click."""
        context_menu = QMenu(self)
        
        close_action = QAction("Close Pet", self)
        close_action.triggered.connect(self._close_pet)
        
        context_menu.addAction(close_action)
        
        # Display the menu at the exact cursor position
        context_menu.exec(event.globalPos())

    def _close_pet(self) -> None:
        """Safely stops timers and unregisters the window before destroying it."""
        self._anim_timer.stop()
        self.pet_manager.remove_pet(self)
        self.close()
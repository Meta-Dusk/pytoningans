import random

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QApplication, QLabel, QComboBox, QFrame
)
from PySide6.QtCore import Qt
from typing import Optional

from pytoningans.core.pet_manager import PetManager
from pytoningans.ui.mod_manager_hub import ModManagerHub
from pytoningans.ui.theme import LIGHT_THEME, DARK_THEME
from pytoningans.ui.title_bar import CustomTitleBar

class MainMenu(QWidget):
    def __init__(self, manager: PetManager) -> None:
        super().__init__()
        self.manager: PetManager = manager
        self.hub_window: Optional[ModManagerHub] = None
        self._is_dark_mode: bool = True
        self._setup_ui()

    def _setup_ui(self) -> None:
        # Strip the OS window frame
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(300, 275)
        
        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar: CustomTitleBar = CustomTitleBar(self, "Control Panel")
        main_layout.addWidget(self.title_bar)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(10)
        
        # --- Spawning Section ---
        spawn_label = QLabel("--- Spawn a Pet ---")
        spawn_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spawn_label.setObjectName("SectionHeader")
        
        self.mod_combo = QComboBox()
        self.mod_combo.addItems(self.manager.mod_manager.get_available_mods())
        
        self.spawn_btn: QPushButton = QPushButton("Spawn Pet")
        self.spawn_btn.clicked.connect(self._on_spawn_clicked)
        
        content_layout.addWidget(spawn_label)
        content_layout.addWidget(self.mod_combo)
        content_layout.addWidget(self.spawn_btn)
        
        # --- Visual Separator ---
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("MenuSeparator")
        content_layout.addWidget(separator)
        
        # --- Utilities Section ---
        utils_label = QLabel("Utilities:")
        utils_label.setObjectName("SectionHeader")
        
        self.manage_btn: QPushButton = QPushButton("Manage Mods")
        self.manage_btn.clicked.connect(self._open_hub)
        
        self.theme_btn: QPushButton = QPushButton("Switch to Light Mode")
        self.theme_btn.clicked.connect(self._toggle_theme)
        
        content_layout.addWidget(utils_label)
        content_layout.addWidget(self.manage_btn)
        content_layout.addWidget(self.theme_btn)
        content_layout.addStretch()
        
        main_layout.addWidget(content_widget)
    
    def _on_spawn_clicked(self) -> None:
        random_x: int = random.randint(300, 1500)
        random_y: int = random.randint(200, 800)
        selected_mod = self.mod_combo.currentText()
        if selected_mod:
            self.manager.spawn_pet(random_x, random_y, selected_mod)

    def _toggle_theme(self) -> None:
        self._is_dark_mode = not self._is_dark_mode
        app = QApplication.instance()
        
        if not isinstance(app, QApplication): return
        if self._is_dark_mode:
            app.setStyleSheet(DARK_THEME)
            self.theme_btn.setText("Switch to Light Mode")
        else:
            app.setStyleSheet(LIGHT_THEME)
            self.theme_btn.setText("Switch to Dark Mode")
    
    def _open_hub(self) -> None:
        if self.hub_window is None or not self.hub_window.isVisible():
            self.hub_window = ModManagerHub(self.manager.mod_manager)
            self.hub_window.show()
        else:
            self.hub_window.activateWindow()
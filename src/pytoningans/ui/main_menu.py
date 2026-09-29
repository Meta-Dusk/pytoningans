import random

from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QApplication, QLabel, QComboBox, QFrame,
    QSpinBox, QHBoxLayout
)
from PySide6.QtCore import QCoreApplication, QRect, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QScreen

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
        self.resize(300, 310)
        
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
        spawn_label = QLabel("Spawn a Pet:")
        spawn_label.setObjectName("SectionHeader")
        
        self.mod_combo = QComboBox()
        self.mod_combo.addItems(self.manager.mod_manager.get_available_mods())
        
        # Group the amount spinbox and spawn button horizontally
        spawn_action_layout = QHBoxLayout()
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(1, 100)
        self.amount_spin.setValue(1)
        self.amount_spin.setToolTip("Number of pets to spawn at once")
        
        self.spawn_btn: QPushButton = QPushButton("Spawn Pet")
        self.spawn_btn.clicked.connect(self._on_spawn_clicked)
        
        spawn_action_layout.addWidget(self.amount_spin)
        spawn_action_layout.addWidget(self.spawn_btn, stretch=1)
        
        content_layout.addWidget(spawn_label)
        content_layout.addWidget(self.mod_combo)
        content_layout.addLayout(spawn_action_layout)
        
        # --- Live Stats Section ---
        stats_layout = QHBoxLayout()
        self.active_count_label = QLabel("Active Pets: 0")
        self.dead_count_label = QLabel("Dead Pets: 0")
        self.active_count_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.dead_count_label.setStyleSheet("color: #F44336; font-weight: bold;")
        
        stats_layout.addWidget(self.active_count_label)
        stats_layout.addWidget(self.dead_count_label)
        content_layout.addLayout(stats_layout)
        
        # --- Visual Separator ---
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("MenuSeparator")
        content_layout.addWidget(separator)
        
        # --- Utilities Section ---
        utils_label = QLabel("Utilities:")
        utils_label.setObjectName("SectionHeader")
        
        self.close_all_btn: QPushButton = QPushButton("Close All Pets")
        self.close_all_btn.clicked.connect(self._on_close_all_clicked)
        
        self.manage_btn: QPushButton = QPushButton("Manage Mods")
        self.manage_btn.clicked.connect(self._open_hub)

        self.theme_btn: QPushButton = QPushButton("Switch to Light Mode")
        self.theme_btn.clicked.connect(self._toggle_theme)
        
        content_layout.addWidget(utils_label)
        content_layout.addWidget(self.close_all_btn)
        content_layout.addWidget(self.manage_btn)
        content_layout.addWidget(self.theme_btn)
        content_layout.addStretch()
        
        main_layout.addWidget(content_widget)
        
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(500)
    
    def _update_stats(self) -> None:
        """Polls the PetManager to update the UI counters."""
        total_active: int = len(self.manager.active_pets)
        total_dead: int = sum(1 for p in self.manager.active_pets if p.is_dead)
        
        self.active_count_label.setText(f"Active Pets: {total_active}")
        self.dead_count_label.setText(f"Dead Pets: {total_dead}")
    
    def _on_spawn_clicked(self) -> None:
        selected_mod: str = self.mod_combo.currentText()
        if not selected_mod:
            return
            
        screen: QScreen = QGuiApplication.primaryScreen()
        geom: Optional[QRect] = screen.availableGeometry() if screen else None
        
        amount: int = self.amount_spin.value()
        for _ in range(amount):
            if geom:
                # Constrain random coordinates to the visible screen area
                random_x = random.randint(geom.left() + 50, geom.right() - 150)
                random_y = random.randint(geom.top() + 50, geom.bottom() - 150)
            else:
                random_x = random.randint(300, 1500)
                random_y = random.randint(200, 800)
                
            self.manager.spawn_pet(random_x, random_y, selected_mod)

    def _on_close_all_clicked(self) -> None:
        # We iterate over a list copy `list(self.manager.active_pets)` because 
        # _close_pet() removes the pet from the original list during iteration
        for pet in list(self.manager.active_pets):
            pet._close_pet()

    def _toggle_theme(self) -> None:
        self._is_dark_mode = not self._is_dark_mode
        app: Optional[QCoreApplication] = QApplication.instance()
        
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
            self.hub_window.mods_updated.connect(self._refresh_spawn_list)
            self.hub_window.show()
        else:
            self.hub_window.activateWindow()
    
    def _refresh_spawn_list(self) -> None:
        """Rebuilds the dropdown/list of available pets to spawn."""
        self.mod_combo.clear()
        valid_mods: List[str] = self.manager.mod_manager.get_available_mods()
        self.mod_combo.addItems(valid_mods)
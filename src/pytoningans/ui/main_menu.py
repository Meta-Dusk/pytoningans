import random
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QApplication, QLabel, QComboBox, QFrame,
    QSpinBox, QHBoxLayout
)
from PySide6.QtCore import QCoreApplication, QRectF, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QScreen

from pytoningans.core.entity_manager import EntityManager
from pytoningans.core.constants import EntityType
from pytoningans.core.world import WorldOverlay
from pytoningans.ui.mod_manager_hub import ModManagerHub
from pytoningans.ui.theme import LIGHT_THEME, DARK_THEME
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.utils.assets import get_main_icon

class MainMenu(QWidget):
    def __init__(self, manager: EntityManager) -> None:
        super().__init__(
            windowTitle="Control Panel",
            windowIcon=get_main_icon()
        )
        self.manager: EntityManager = manager
        self.hub_window: Optional[ModManagerHub] = None
        self._is_dark_mode: bool = True
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(320, 390)
        
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
        spawn_label = QLabel("Spawn Objects:")
        spawn_label.setObjectName("SectionHeader")
        content_layout.addWidget(spawn_label)

        # Category Filter Row
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Entities", "all")
        self.category_combo.addItem("Pets Only", EntityType.PET.value)
        self.category_combo.addItem("Structures Only", EntityType.STRUCTURE.value)
        self.category_combo.currentIndexChanged.connect(self._refresh_spawn_list)
        filter_layout.addWidget(self.category_combo, stretch=1)
        content_layout.addLayout(filter_layout)

        # Monitor Selection Row (Shown only if multiple monitors exist)
        self.monitor_layout = QHBoxLayout()
        self.monitor_label = QLabel("Monitor:")
        self.monitor_combo = QComboBox()
        self.monitor_layout.addWidget(self.monitor_label)
        self.monitor_layout.addWidget(self.monitor_combo, stretch=1)
        content_layout.addLayout(self.monitor_layout)
        self._populate_monitors()
        
        # Target Mod Dropdown
        self.mod_combo = QComboBox()
        content_layout.addWidget(self.mod_combo)
        
        # Amount and Spawn Button
        spawn_action_layout = QHBoxLayout()
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(1, 100)
        self.amount_spin.setValue(1)
        self.amount_spin.setToolTip("Number of items to spawn")
        
        self.spawn_btn: QPushButton = QPushButton("Spawn")
        self.spawn_btn.clicked.connect(self._on_spawn_clicked)
        
        spawn_action_layout.addWidget(self.amount_spin)
        spawn_action_layout.addWidget(self.spawn_btn, stretch=1)
        content_layout.addLayout(spawn_action_layout)
        
        # --- Live Stats Section ---
        stats_layout = QHBoxLayout()
        self.active_count_label = QLabel("Active: 0")
        self.dead_count_label = QLabel("Dead: 0")
        self.active_count_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.dead_count_label.setStyleSheet("color: #F44336; font-weight: bold;")
        
        stats_layout.addWidget(self.active_count_label)
        stats_layout.addWidget(self.dead_count_label)
        content_layout.addLayout(stats_layout)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("MenuSeparator")
        content_layout.addWidget(separator)
        
        # --- Utilities Section ---
        utils_label = QLabel("Utilities:")
        utils_label.setObjectName("SectionHeader")
        content_layout.addWidget(utils_label)
        
        self.close_all_btn = QPushButton("Close All Objects")
        self.close_all_btn.clicked.connect(self._on_close_all_clicked)
        
        self.close_all_dead_btn = QPushButton("Close All Dead Pets")
        self.close_all_dead_btn.clicked.connect(self._on_close_all_dead_clicked)
        
        self.manage_btn = QPushButton("Manage Mods")
        self.manage_btn.clicked.connect(self._open_hub)

        self.theme_btn = QPushButton("Switch to Light Mode")
        self.theme_btn.clicked.connect(self._toggle_theme)
        
        content_layout.addWidget(self.close_all_btn)
        content_layout.addWidget(self.close_all_dead_btn)
        content_layout.addWidget(self.manage_btn)
        content_layout.addWidget(self.theme_btn)
        content_layout.addStretch()
        
        main_layout.addWidget(content_widget)
        
        self._refresh_spawn_list()
        
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(500)

    def _populate_monitors(self) -> None:
        """Populates the monitor combo box if more than one screen is active."""
        self.monitor_combo.clear()
        worlds: list[WorldOverlay] = self.manager.active_worlds
        
        if len(worlds) <= 1:
            self.monitor_label.hide()
            self.monitor_combo.hide()
            return
            
        self.monitor_label.show()
        self.monitor_combo.show()

        primary_screen: Optional[QScreen] = QGuiApplication.primaryScreen()
        
        for i, world in enumerate(worlds):
            is_primary = (world.target_screen == primary_screen)
            label = f"Monitor {i + 1} ({'Primary' if is_primary else 'Secondary'})"
            self.monitor_combo.addItem(label, userData=world)
            
        self.monitor_combo.addItem("Random Monitor", userData="random")

    def _refresh_spawn_list(self) -> None:
        """Filters the spawn dropdown based on the active category filter."""
        self.mod_combo.clear()
        selected_category: str = self.category_combo.currentData()
        
        mods: dict[str, tuple[str, str]] = self.manager.mod_manager.get_available_mods_with_type()
        for folder, (name, entity_type) in mods.items():
            if selected_category == "all" or entity_type == selected_category:
                self.mod_combo.addItem(f"[{entity_type.capitalize()}] {name}", userData=folder)

    def _update_stats(self) -> None:
        total_pets: int = len(self.manager.active_entities)
        total_structs: int = len(self.manager.active_structures)
        total_dead: int = sum(1 for p in self.manager.active_entities if p.is_dead)
        
        self.active_count_label.setText(f"Pets: {total_pets} | Structs: {total_structs}")
        self.dead_count_label.setText(f"Dead: {total_dead}")

    def _on_spawn_clicked(self) -> None:
        selected_mod: str = self.mod_combo.currentData()
        if not selected_mod or not self.manager.active_worlds:
            return
            
        selected_target = self.monitor_combo.currentData() if self.monitor_combo.isVisible() else None
        amount: int = self.amount_spin.value()

        for _ in range(amount):
            # Resolve target WorldOverlay
            if selected_target == "random":
                target_world: WorldOverlay = random.choice(self.manager.active_worlds)
            elif isinstance(selected_target, WorldOverlay):
                target_world = selected_target
            else:
                target_world = self.manager.active_worlds[0]
                
            # Compute position inside the target world's scene boundaries
            scene_rect: QRectF = target_world.scene.sceneRect()
            random_x = random.uniform(scene_rect.left() + 50, scene_rect.right() - 150)
            random_y = random.uniform(scene_rect.top() + 50, scene_rect.bottom() - 150)
                
            self.manager.spawn_entity(random_x, random_y, selected_mod, target_world=target_world)

    def _on_close_all_clicked(self) -> None:
        for entity in list(self.manager.active_entities):
            entity.destroy()
        for struct in list(self.manager.active_structures):
            struct.destroy()

    def _on_close_all_dead_clicked(self) -> None:
        for entity in list(self.manager.active_entities):
            if entity.is_dead:
                entity.destroy()

    def _toggle_theme(self) -> None:
        self._is_dark_mode = not self._is_dark_mode
        app: Optional[QCoreApplication] = QApplication.instance()
        
        if not isinstance(app, QApplication): 
            return
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
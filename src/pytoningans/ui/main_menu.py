from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QApplication, QLabel, QComboBox, QFrame,
    QSpinBox, QHBoxLayout, QCheckBox
)
from PySide6.QtCore import QCoreApplication, QRect, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QScreen, QResizeEvent, QShowEvent, QHideEvent, QKeyEvent

from pytoningans.core.entity_manager import EntityManager
from pytoningans.core.constants import EntityType
from pytoningans.core.world import WorldOverlay
from pytoningans.core.settings import SettingsManager
from pytoningans.core.spawning import SpawnAreaMode
from pytoningans.ui.mod_manager_hub import ModManagerHub
from pytoningans.ui.combat_settings_dialog import CombatSettingsDialog
from pytoningans.ui.theme import LIGHT_THEME, DARK_THEME
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.mod_editor.components import CustomSizeGrip
from pytoningans.utils.assets import get_main_icon


class MainMenu(QWidget):
    def __init__(self, manager: EntityManager) -> None:
        super().__init__(
            windowTitle="Control Panel",
            windowIcon=get_main_icon()
        )
        self.manager: EntityManager = manager
        self.hub_window: Optional[ModManagerHub] = None
        self.combat_settings_dialog: Optional[CombatSettingsDialog] = None
        self._is_dark_mode: bool = True
        self._setup_ui()

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("MenuSeparator")
        return sep

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(480, 720)
        self.setMinimumSize(480, 720)
        
        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar: CustomTitleBar = CustomTitleBar(self, "Control Panel")
        main_layout.addWidget(self.title_bar)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(14, 12, 14, 14)
        content_layout.setSpacing(8)
        
        # --- Spawning Section ---
        spawn_label = QLabel("Spawn Objects:")
        spawn_label.setObjectName("SectionHeader")
        content_layout.addWidget(spawn_label)

        # Category Filter Row
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Entities", "all")
        self.category_combo.addItem("Entities Only", EntityType.ENTITY.value)
        self.category_combo.addItem("Structures Only", EntityType.STRUCTURE.value)
        self.category_combo.addItem("Items Only", EntityType.ITEM.value)
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

        # Spawning Area Selection Row
        area_layout = QHBoxLayout()
        area_layout.addWidget(QLabel("Area:"))
        self.area_combo = QComboBox()
        self.area_combo.addItem("World Bounds (Full Screen)", SpawnAreaMode.SCREEN.value)
        self.area_combo.addItem("Ground Level", SpawnAreaMode.GROUND.value)
        self.area_combo.addItem("Sky / High Air", SpawnAreaMode.SKY.value)
        self.area_combo.addItem("Custom Region...", SpawnAreaMode.CUSTOM.value)

        saved_area: str = SettingsManager.get().settings.spawn_area_mode
        area_idx: int = self.area_combo.findData(saved_area)
        if area_idx >= 0:
            self.area_combo.setCurrentIndex(area_idx)
        self.area_combo.currentIndexChanged.connect(self._on_area_changed)
        area_layout.addWidget(self.area_combo, stretch=1)
        content_layout.addLayout(area_layout)

        # Custom Region Row (Visible only when Custom Region is chosen)
        self.custom_region_frame = QFrame()
        custom_reg_layout = QHBoxLayout(self.custom_region_frame)
        custom_reg_layout.setContentsMargins(0, 0, 0, 0)
        custom_reg_layout.setSpacing(6)

        self.region_info_label = QLabel("Region: Not Set")
        self.region_info_label.setObjectName("HelperText")
        self.select_region_btn = QPushButton("Select on Screen")
        self.select_region_btn.setObjectName("RowBtn")
        self.select_region_btn.clicked.connect(self._on_select_region_clicked)

        custom_reg_layout.addWidget(self.region_info_label, stretch=1)
        custom_reg_layout.addWidget(self.select_region_btn)
        content_layout.addWidget(self.custom_region_frame)
        self.custom_region_frame.setVisible(self.area_combo.currentData() == SpawnAreaMode.CUSTOM.value)

        # Spawning Options Row (Avoid Desktop Windows)
        options_layout = QHBoxLayout()
        self.avoid_windows_chk = QCheckBox("Avoid Desktop Windows")
        self.avoid_windows_chk.setToolTip("Prevent entities from spawning inside windows to avoid crushing/ejection deaths")
        self.avoid_windows_chk.setChecked(SettingsManager.get().settings.avoid_window_spawn)
        self.avoid_windows_chk.toggled.connect(self._on_avoid_windows_toggled)
        options_layout.addWidget(self.avoid_windows_chk)
        content_layout.addLayout(options_layout)
        
        # Actions Row: Amount + Spawn Random + Place with Cursor
        spawn_action_layout = QHBoxLayout()
        spawn_action_layout.setSpacing(6)
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(1, 100)
        self.amount_spin.setValue(1)
        self.amount_spin.setToolTip("Number of items to spawn")
        
        self.spawn_btn: QPushButton = QPushButton("Spawn Random")
        self.spawn_btn.clicked.connect(self._on_spawn_clicked)

        self.place_btn: QPushButton = QPushButton("Place with Cursor")
        self.place_btn.setToolTip("Interactively place entities on the desktop with a ghost cursor preview")
        self.place_btn.clicked.connect(self._on_place_clicked)
        
        spawn_action_layout.addWidget(self.amount_spin)
        spawn_action_layout.addWidget(self.spawn_btn, stretch=1)
        spawn_action_layout.addWidget(self.place_btn, stretch=1)
        content_layout.addLayout(spawn_action_layout)

        # Interactive Mode Status Banner
        self.placement_banner = QFrame()
        self.placement_banner.setObjectName("ActionRow")
        banner_layout = QHBoxLayout(self.placement_banner)
        banner_layout.setContentsMargins(10, 6, 10, 6)
        banner_layout.setSpacing(8)

        self.placement_status_label = QLabel("Click to place. Esc to cancel.")
        self.cancel_interactive_btn = QPushButton("Cancel")
        self.cancel_interactive_btn.setObjectName("RowBtn")
        self.cancel_interactive_btn.clicked.connect(self._on_cancel_interactive_clicked)

        banner_layout.addWidget(self.placement_status_label, stretch=1)
        banner_layout.addWidget(self.cancel_interactive_btn)
        content_layout.addWidget(self.placement_banner)
        self.placement_banner.hide()
        
        content_layout.addWidget(self._create_separator())
        
        # --- Live Controls Section (Value Display + Context Actions) ---
        live_label = QLabel("Live Controls:")
        live_label.setObjectName("SectionHeader")
        content_layout.addWidget(live_label)

        # Row 1: Alive Entities
        alive_frame = QFrame()
        alive_frame.setObjectName("ActionRow")
        alive_layout = QHBoxLayout(alive_frame)
        alive_layout.setContentsMargins(10, 5, 10, 5)
        alive_layout.setSpacing(6)

        self.alive_count_label = QLabel("Alive: 0")
        self.alive_count_label.setObjectName("StatAliveLabel")
        alive_layout.addWidget(self.alive_count_label)
        alive_layout.addStretch()

        self.kill_alive_btn = QPushButton("Kill All")
        self.kill_alive_btn.setObjectName("RowBtn")
        self.kill_alive_btn.setToolTip("Trigger death animation for alive entities")
        self.kill_alive_btn.clicked.connect(self._on_kill_alive_clicked)
        alive_layout.addWidget(self.kill_alive_btn)

        self.close_alive_btn = QPushButton("Close All")
        self.close_alive_btn.setObjectName("RowBtn")
        self.close_alive_btn.setToolTip("Close all alive entities immediately")
        self.close_alive_btn.clicked.connect(self._on_close_alive_clicked)
        alive_layout.addWidget(self.close_alive_btn)

        content_layout.addWidget(alive_frame)

        # Row 2: Dead Entities
        dead_frame = QFrame()
        dead_frame.setObjectName("ActionRow")
        dead_layout = QHBoxLayout(dead_frame)
        dead_layout.setContentsMargins(10, 5, 10, 5)
        dead_layout.setSpacing(6)

        self.dead_count_label = QLabel("Dead: 0")
        self.dead_count_label.setObjectName("StatDeadLabel")
        dead_layout.addWidget(self.dead_count_label)
        dead_layout.addStretch()

        self.revive_dead_btn = QPushButton("Revive All")
        self.revive_dead_btn.setObjectName("RowBtn")
        self.revive_dead_btn.setToolTip("Revive all dead entities back to life")
        self.revive_dead_btn.clicked.connect(self._on_revive_dead_clicked)
        dead_layout.addWidget(self.revive_dead_btn)

        self.close_dead_btn = QPushButton("Close All")
        self.close_dead_btn.setObjectName("RowBtn")
        self.close_dead_btn.setToolTip("Remove all dead entities from the screen")
        self.close_dead_btn.clicked.connect(self._on_close_dead_clicked)
        dead_layout.addWidget(self.close_dead_btn)

        content_layout.addWidget(dead_frame)

        # Row 3: Structures
        struct_frame = QFrame()
        struct_frame.setObjectName("ActionRow")
        struct_layout = QHBoxLayout(struct_frame)
        struct_layout.setContentsMargins(10, 5, 10, 5)
        struct_layout.setSpacing(6)

        self.struct_count_label = QLabel("Structures: 0")
        self.struct_count_label.setObjectName("StatStructLabel")
        struct_layout.addWidget(self.struct_count_label)
        struct_layout.addStretch()

        self.close_struct_btn = QPushButton("Close All")
        self.close_struct_btn.setObjectName("RowBtn")
        self.close_struct_btn.setToolTip("Close all active structures")
        self.close_struct_btn.clicked.connect(self._on_close_structures_clicked)
        struct_layout.addWidget(self.close_struct_btn)

        content_layout.addWidget(struct_frame)

        # Row 4: Items
        item_frame = QFrame()
        item_frame.setObjectName("ActionRow")
        item_layout = QHBoxLayout(item_frame)
        item_layout.setContentsMargins(10, 5, 10, 5)
        item_layout.setSpacing(6)

        self.item_count_label = QLabel("Items: 0")
        self.item_count_label.setObjectName("StatItemLabel")
        item_layout.addWidget(self.item_count_label)
        item_layout.addStretch()

        self.close_item_btn = QPushButton("Close All")
        self.close_item_btn.setObjectName("RowBtn")
        self.close_item_btn.setToolTip("Close all active items")
        self.close_item_btn.clicked.connect(self._on_close_items_clicked)
        item_layout.addWidget(self.close_item_btn)

        content_layout.addWidget(item_frame)

        content_layout.addWidget(self._create_separator())

        # --- Global Actions Section ---
        global_label = QLabel("Global Actions:")
        global_label.setObjectName("SectionHeader")
        content_layout.addWidget(global_label)

        global_layout = QHBoxLayout()
        global_layout.setSpacing(8)

        self.close_all_entities_btn = QPushButton("Close All Entities")
        self.close_all_entities_btn.setToolTip("Close all entities regardless of alive/dead state")
        self.close_all_entities_btn.clicked.connect(self._on_close_all_entities_clicked)

        self.close_all_objects_btn = QPushButton("Close All Objects")
        self.close_all_objects_btn.setToolTip("Close all entities and structures on all screens")
        self.close_all_objects_btn.clicked.connect(self._on_close_all_objects_clicked)

        global_layout.addWidget(self.close_all_entities_btn)
        global_layout.addWidget(self.close_all_objects_btn)
        content_layout.addLayout(global_layout)

        content_layout.addWidget(self._create_separator())

        # --- Mod Management & Settings Section ---
        mod_label = QLabel("Management & Settings:")
        mod_label.setObjectName("SectionHeader")
        content_layout.addWidget(mod_label)

        mgmt_layout = QHBoxLayout()
        mgmt_layout.setSpacing(8)

        self.manage_btn = QPushButton("Manage Mods")
        self.manage_btn.setToolTip("Open the Mod Manager Hub")
        self.manage_btn.clicked.connect(self._open_hub)

        self.combat_settings_btn = QPushButton("Combat Settings")
        self.combat_settings_btn.setToolTip("Configure damage indicators and health bar display preferences")
        self.combat_settings_btn.clicked.connect(self._open_combat_settings)

        mgmt_layout.addWidget(self.manage_btn)
        mgmt_layout.addWidget(self.combat_settings_btn)
        content_layout.addLayout(mgmt_layout)

        content_layout.addWidget(self._create_separator())

        # --- System Controls Section ---
        sys_layout = QHBoxLayout()
        sys_layout.setSpacing(8)

        self.theme_btn = QPushButton("Switch to Light Mode")
        self.theme_btn.clicked.connect(self._toggle_theme)

        self.shutdown_btn = QPushButton("Shutdown")
        self.shutdown_btn.setObjectName("DangerBtn")
        self.shutdown_btn.setToolTip("Completely quit PyToNingans")
        self.shutdown_btn.clicked.connect(QApplication.quit)

        sys_layout.addWidget(self.theme_btn)
        sys_layout.addWidget(self.shutdown_btn)
        content_layout.addLayout(sys_layout)

        content_layout.addStretch()
        
        main_layout.addWidget(content_widget)
        
        self.grip = CustomSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        
        self._refresh_spawn_list()
        self._update_stats()

        # Connect interactive spawning system signals
        self.manager.spawning_system.placement_started.connect(self._on_placement_started)
        self.manager.spawning_system.placement_count_changed.connect(self._on_placement_count_changed)
        self.manager.spawning_system.placement_ended.connect(self._on_placement_ended)
        self.manager.spawning_system.region_selection_started.connect(self._on_region_selection_started)
        self.manager.spawning_system.region_selection_ended.connect(self._on_region_selection_ended)
        
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._update_stats)
        if self.isVisible():
            self.stats_timer.start(500)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self.manager.spawning_system.is_active:
            self.manager.spawning_system.cancel_all()
            event.accept()
            return
        super().keyPressEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._update_stats()
        if not self.stats_timer.isActive():
            self.stats_timer.start(500)

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)
        self.stats_timer.stop()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.grip.move(
            self.width() - self.grip.width(),
            self.height() - self.grip.height()
        )

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
        total_entities: int = len(self.manager.active_entities)
        dead_entities: int = sum(1 for p in self.manager.active_entities if p.is_dead)
        alive_entities: int = total_entities - dead_entities
        total_structs: int = len(self.manager.active_structures)
        total_items: int = len(self.manager.active_items)
        
        self.alive_count_label.setText(f"Alive: {alive_entities}")
        self.dead_count_label.setText(f"Dead: {dead_entities}")
        self.struct_count_label.setText(f"Structures: {total_structs}")
        self.item_count_label.setText(f"Items: {total_items}")

        self.kill_alive_btn.setEnabled(alive_entities > 0)
        self.close_alive_btn.setEnabled(alive_entities > 0)

        self.revive_dead_btn.setEnabled(dead_entities > 0)
        self.close_dead_btn.setEnabled(dead_entities > 0)

        self.close_struct_btn.setEnabled(total_structs > 0)
        self.close_item_btn.setEnabled(total_items > 0)

        self.close_all_entities_btn.setEnabled(total_entities > 0)
        self.close_all_objects_btn.setEnabled(
            total_entities > 0 or total_structs > 0 or total_items > 0
        )

    def _on_area_changed(self, _: int) -> None:
        mode: str = self.area_combo.currentData()
        self.custom_region_frame.setVisible(mode == SpawnAreaMode.CUSTOM.value)
        SettingsManager.get().update_settings(spawn_area_mode=mode)

    def _on_avoid_windows_toggled(self, checked: bool) -> None:
        SettingsManager.get().update_settings(avoid_window_spawn=checked)

    def _on_select_region_clicked(self) -> None:
        self.manager.spawning_system.start_region_selection()

    def _on_place_clicked(self) -> None:
        selected_mod: str = self.mod_combo.currentData()
        if not selected_mod:
            return
        amount: int = self.amount_spin.value()
        avoid_win: bool = self.avoid_windows_chk.isChecked()
        self.manager.spawning_system.start_placement(selected_mod, amount, avoid_win)

    def _on_cancel_interactive_clicked(self) -> None:
        self.manager.spawning_system.cancel_all()

    def _on_placement_started(self, mod_name: str, count: int) -> None:
        self.placement_status_label.setText(
            f"Placing '{mod_name}'\n"
            f"({count} left)\n"
            "Click to spawn, Esc to cancel"
        )
        self.placement_banner.show()
        self.place_btn.setEnabled(False)
        self.spawn_btn.setEnabled(False)
        self.resize(480, 800)

    def _on_placement_count_changed(self, count: int) -> None:
        mod_name = self.manager.spawning_system.placement_mod_name
        self.placement_status_label.setText(
            f"Placing '{mod_name}'\n"
            f"({count} left)\n"
            "Click to spawn, Esc to cancel"
        )

    def _on_placement_ended(self) -> None:
        self.placement_banner.hide()
        self.place_btn.setEnabled(True)
        self.spawn_btn.setEnabled(True)
        self.resize(480, 720)

    def _on_region_selection_started(self) -> None:
        self.placement_status_label.setText(
            "Click and drag on screen to select region.\nEsc to cancel."
        )
        self.placement_banner.show()
        self.select_region_btn.setEnabled(False)
        self.resize(500, 820)

    def _on_region_selection_ended(self, succeeded: bool, rect: QRect) -> None:
        self.placement_banner.hide()
        self.select_region_btn.setEnabled(True)
        if succeeded and not rect.isEmpty():
            self.region_info_label.setText(
                f"Region: {rect.width()}x{rect.height()}\n"
                f"at ({rect.x()},{rect.y()})"
            )
            self.resize(480, 760)
        else: self.resize(480, 720)

    def _on_spawn_clicked(self) -> None:
        selected_mod: str = self.mod_combo.currentData()
        if not selected_mod or not self.manager.active_worlds:
            return

        selected_target = (
            self.monitor_combo.currentData() if self.monitor_combo.isVisible() else None
        )
        amount: int = self.amount_spin.value()
        area_mode: str = self.area_combo.currentData()
        avoid_win: bool = self.avoid_windows_chk.isChecked()
        custom_rect: Optional[QRect] = (
            self.manager.spawning_system.custom_region
            if area_mode == SpawnAreaMode.CUSTOM.value
            else None
        )

        target_world: Optional[WorldOverlay]
        if selected_target == "random":
            target_world = None
        elif isinstance(selected_target, WorldOverlay):
            target_world = selected_target
        else:
            target_world = self.manager.active_worlds[0]

        self.manager.spawning_system.spawn_random(
            mod_folder=selected_mod,
            amount=amount,
            target_world=target_world,
            area_mode=area_mode,
            custom_rect=custom_rect,
            avoid_windows=avoid_win,
        )

    def _on_kill_alive_clicked(self) -> None:
        """Triggers the death state/animation for all currently alive entities."""
        for entity in list(self.manager.active_entities):
            if not entity.is_dead:
                entity.die()

    def _on_close_alive_clicked(self) -> None:
        """Immediately destroys all currently alive entities."""
        for entity in list(self.manager.active_entities):
            if not entity.is_dead:
                entity.destroy()

    def _on_revive_dead_clicked(self) -> None:
        """Revives all dead entities."""
        for entity in list(self.manager.active_entities):
            if entity.is_dead:
                entity.revive()

    def _on_close_dead_clicked(self) -> None:
        """Immediately destroys all dead entities."""
        for entity in list(self.manager.active_entities):
            if entity.is_dead:
                entity.destroy()

    def _on_close_structures_clicked(self) -> None:
        """Destroys all active structures."""
        for struct in list(self.manager.active_structures):
            struct.destroy()

    def _on_close_items_clicked(self) -> None:
        """Destroys all active items."""
        for item in list(self.manager.active_items):
            item.destroy()

    def _on_close_all_entities_clicked(self) -> None:
        """Destroys all entities regardless of alive/dead state."""
        for entity in list(self.manager.active_entities):
            entity.destroy()

    def _on_close_all_objects_clicked(self) -> None:
        """Destroys all entities, structures, and items across all worlds."""
        for entity in list(self.manager.active_entities):
            entity.destroy()
        for struct in list(self.manager.active_structures):
            struct.destroy()
        for item in list(self.manager.active_items):
            item.destroy()

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
    
    def _on_hub_destroyed(self) -> None:
        self.hub_window = None

    def _on_combat_settings_destroyed(self) -> None:
        self.combat_settings_dialog = None

    def _open_hub(self) -> None:
        if self.hub_window is None or not self.hub_window.isVisible():
            self.hub_window = ModManagerHub(self.manager.mod_manager)
            self.hub_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.hub_window.destroyed.connect(self._on_hub_destroyed)
            self.hub_window.mods_updated.connect(self._refresh_spawn_list)
            self.hub_window.show()
        else:
            self.hub_window.activateWindow()

    def _open_combat_settings(self) -> None:
        if self.combat_settings_dialog is None or not self.combat_settings_dialog.isVisible():
            self.combat_settings_dialog = CombatSettingsDialog(self)
            self.combat_settings_dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.combat_settings_dialog.destroyed.connect(self._on_combat_settings_destroyed)
            self.combat_settings_dialog.show()
        else:
            self.combat_settings_dialog.activateWindow()
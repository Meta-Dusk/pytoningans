from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, QFrame,
    QSpinBox, QHBoxLayout, QCheckBox
)
from PySide6.QtCore import QRect, Signal
from PySide6.QtGui import QGuiApplication, QScreen

from pytoningans.core.constants import EntityType
from pytoningans.core.world import WorldOverlay
from pytoningans.core.settings import SettingsManager
from pytoningans.core.spawning import SpawnAreaMode

if TYPE_CHECKING:
    from pytoningans.core.entity_manager import EntityManager


class SpawnPanel(QWidget):
    """Panel managing object selection, spawn area configuration, and interactive placement."""

    size_change_requested: Signal = Signal()

    def __init__(self, manager: EntityManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.manager: EntityManager = manager
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        spawn_label = QLabel("Spawn Objects:")
        spawn_label.setObjectName("SectionHeader")
        layout.addWidget(spawn_label)

        # Category Filter Row
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Entities", "all")
        self.category_combo.addItem("Entities Only", EntityType.ENTITY)
        self.category_combo.addItem("Structures Only", EntityType.STRUCTURE)
        self.category_combo.addItem("Items Only", EntityType.ITEM)
        self.category_combo.currentIndexChanged.connect(self.refresh_spawn_list)
        filter_layout.addWidget(self.category_combo, stretch=1)
        layout.addLayout(filter_layout)

        # Monitor Selection Row (Shown only if multiple monitors exist)
        self.monitor_layout = QHBoxLayout()
        self.monitor_label = QLabel("Monitor:")
        self.monitor_combo = QComboBox()
        self.monitor_layout.addWidget(self.monitor_label)
        self.monitor_layout.addWidget(self.monitor_combo, stretch=1)
        layout.addLayout(self.monitor_layout)
        self._populate_monitors()

        # Target Mod Dropdown
        self.mod_combo = QComboBox()
        layout.addWidget(self.mod_combo)

        # Spawning Area Selection Row
        area_layout = QHBoxLayout()
        area_layout.addWidget(QLabel("Area:"))
        self.area_combo = QComboBox()
        self.area_combo.addItem("World Bounds (Full Screen)", SpawnAreaMode.SCREEN)
        self.area_combo.addItem("Ground Level", SpawnAreaMode.GROUND)
        self.area_combo.addItem("Sky / High Air", SpawnAreaMode.SKY)
        self.area_combo.addItem("Custom Region...", SpawnAreaMode.CUSTOM)

        saved_area: str = SettingsManager.get().settings.spawn_area_mode
        area_idx: int = self.area_combo.findData(saved_area)
        if area_idx >= 0:
            self.area_combo.setCurrentIndex(area_idx)
        self.area_combo.currentIndexChanged.connect(self._on_area_changed)
        area_layout.addWidget(self.area_combo, stretch=1)
        layout.addLayout(area_layout)

        # Custom Region Row (Visible only when Custom Region is chosen)
        self.custom_region_frame = QFrame()
        self.custom_region_frame.setObjectName("ActionRow")
        custom_reg_layout = QHBoxLayout(self.custom_region_frame)
        custom_reg_layout.setContentsMargins(8, 4, 8, 4)
        custom_reg_layout.setSpacing(6)

        self.region_info_label = QLabel("Region: Not Set")
        self.region_info_label.setObjectName("HelperText")
        self.region_info_label.setWordWrap(True)
        self.select_region_btn = QPushButton("Select on Screen")
        self.select_region_btn.setObjectName("RowBtn")
        self.select_region_btn.clicked.connect(self._on_select_region_clicked)

        custom_reg_layout.addWidget(self.region_info_label, stretch=1)
        custom_reg_layout.addWidget(self.select_region_btn)
        layout.addWidget(self.custom_region_frame)
        self.custom_region_frame.setVisible(self.area_combo.currentData() == SpawnAreaMode.CUSTOM)

        # Spawning Options Row (Avoid Desktop Windows)
        options_layout = QHBoxLayout()
        self.avoid_windows_chk = QCheckBox("Avoid Desktop Windows")
        self.avoid_windows_chk.setToolTip(
            "Prevent entities from spawning inside windows to avoid crushing/ejection deaths"
        )
        self.avoid_windows_chk.setChecked(SettingsManager.get().settings.avoid_window_spawn)
        self.avoid_windows_chk.toggled.connect(self._on_avoid_windows_toggled)
        options_layout.addWidget(self.avoid_windows_chk)
        layout.addLayout(options_layout)

        # Actions Row: Amount + Spawn Random + Place with Cursor
        spawn_action_layout = QHBoxLayout()
        spawn_action_layout.setSpacing(6)
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(1, 100)
        self.amount_spin.setValue(1)
        self.amount_spin.setToolTip("Number of items to spawn")
        self.amount_spin.setMinimumWidth(50)

        self.spawn_btn: QPushButton = QPushButton("Spawn Random")
        self.spawn_btn.clicked.connect(self._on_spawn_clicked)

        self.place_btn: QPushButton = QPushButton("Place with Cursor")
        self.place_btn.setToolTip(
            "Interactively place entities on the desktop with a ghost cursor preview"
        )
        self.place_btn.clicked.connect(self._on_place_clicked)

        spawn_action_layout.addWidget(self.amount_spin)
        spawn_action_layout.addWidget(self.spawn_btn, stretch=1)
        spawn_action_layout.addWidget(self.place_btn, stretch=1)
        layout.addLayout(spawn_action_layout)

        # Interactive Mode Status Banner
        self.placement_banner = QFrame()
        self.placement_banner.setObjectName("ActionRow")
        banner_layout = QHBoxLayout(self.placement_banner)
        banner_layout.setContentsMargins(10, 6, 10, 6)
        banner_layout.setSpacing(8)

        self.placement_status_label = QLabel("Click to place. Esc to cancel.")
        self.placement_status_label.setWordWrap(True)
        self.cancel_interactive_btn = QPushButton("Cancel")
        self.cancel_interactive_btn.setObjectName("RowBtn")
        self.cancel_interactive_btn.clicked.connect(self._on_cancel_interactive_clicked)

        banner_layout.addWidget(self.placement_status_label, stretch=1)
        banner_layout.addWidget(self.cancel_interactive_btn)
        layout.addWidget(self.placement_banner)
        self.placement_banner.hide()

        layout.addStretch()
        self.refresh_spawn_list()

    def _connect_signals(self) -> None:
        self.manager.spawning_system.placement_started.connect(self._on_placement_started)
        self.manager.spawning_system.placement_count_changed.connect(self._on_placement_count_changed)
        self.manager.spawning_system.placement_ended.connect(self._on_placement_ended)
        self.manager.spawning_system.region_selection_started.connect(self._on_region_selection_started)
        self.manager.spawning_system.region_selection_ended.connect(self._on_region_selection_ended)

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

    def refresh_spawn_list(self) -> None:
        """Filters the spawn dropdown based on the active category filter."""
        self.mod_combo.clear()
        selected_category: str = self.category_combo.currentData()

        mods: dict[str, tuple[str, str]] = self.manager.mod_manager.get_available_mods_with_type()
        for folder, (name, entity_type) in mods.items():
            if selected_category == "all" or entity_type == selected_category:
                self.mod_combo.addItem(f"[{entity_type.capitalize()}] {name}", userData=folder)

    def _on_area_changed(self, _: int) -> None:
        mode: str = self.area_combo.currentData()
        self.custom_region_frame.setVisible(mode == SpawnAreaMode.CUSTOM.value)
        SettingsManager.get().update_settings(spawn_area_mode=mode)
        self.size_change_requested.emit()

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
            f"Placing '{mod_name}' ({count} left)\n"
            "Click to spawn, Esc to cancel"
        )
        self.placement_banner.show()
        self.place_btn.setEnabled(False)
        self.spawn_btn.setEnabled(False)
        self.size_change_requested.emit()

    def _on_placement_count_changed(self, count: int) -> None:
        mod_name: str = self.manager.spawning_system.placement_mod_name
        self.placement_status_label.setText(
            f"Placing '{mod_name}' ({count} left)\n"
            "Click to spawn, Esc to cancel"
        )
        self.size_change_requested.emit()

    def _on_placement_ended(self) -> None:
        self.placement_banner.hide()
        self.place_btn.setEnabled(True)
        self.spawn_btn.setEnabled(True)
        self.size_change_requested.emit()

    def _on_region_selection_started(self) -> None:
        self.placement_status_label.setText(
            "Click and drag on screen to select region.\nEsc to cancel."
        )
        self.placement_banner.show()
        self.select_region_btn.setEnabled(False)
        self.size_change_requested.emit()

    def _on_region_selection_ended(self, succeeded: bool, rect: QRect) -> None:
        self.placement_banner.hide()
        self.select_region_btn.setEnabled(True)
        if succeeded and not rect.isEmpty():
            self.region_info_label.setText(
                f"Region: {rect.width()}x{rect.height()} "
                f"at ({rect.x()},{rect.y()})"
            )
        self.size_change_requested.emit()

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


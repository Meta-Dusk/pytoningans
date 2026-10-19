from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QHBoxLayout
)
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QResizeEvent, QShowEvent, QHideEvent, QKeyEvent

from pytoningans.ui.mod_manager_hub import ModManagerHub
from pytoningans.ui.mod_browser import ModBrowserDialog
from pytoningans.ui.combat_settings_dialog import CombatSettingsDialog
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.mod_editor.components import CustomSizeGrip
from pytoningans.ui.main_menu.spawn_panel import SpawnPanel
from pytoningans.ui.main_menu.live_controls_panel import LiveControlsPanel
from pytoningans.ui.main_menu.system_controls_panel import SystemControlsPanel
from pytoningans.utils.assets import get_main_icon

if TYPE_CHECKING:
    from pytoningans.core.entity_manager import EntityManager


class MainMenu(QWidget):
    """The central control panel window for PyToNingans, assembling modular control panels."""

    def __init__(self, manager: EntityManager) -> None:
        super().__init__(
            windowTitle="Control Panel", windowIcon=get_main_icon()
        )
        self.manager: EntityManager = manager
        self.hub_window: Optional[ModManagerHub] = None
        self.browser_dialog: Optional[ModBrowserDialog] = None
        self.combat_settings_dialog: Optional[CombatSettingsDialog] = None
        self._setup_ui()

    def _create_vertical_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setObjectName("MenuSeparatorV")
        return sep

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar: CustomTitleBar = CustomTitleBar(self, "Control Panel")
        main_layout.addWidget(self.title_bar)

        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(14, 12, 14, 14); content_layout.setSpacing(14)

        # Left Pane: Spawning and Interactive Placement
        self.spawn_panel = SpawnPanel(self.manager, self)
        self.spawn_panel.size_change_requested.connect(self._adjust_size_if_needed)
        content_layout.addWidget(self.spawn_panel, stretch=1)

        # Vertical Separator Divider
        content_layout.addWidget(self._create_vertical_separator())

        # Right Pane: Live Controls, Global Actions, Management and Settings
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0); right_layout.setSpacing(8)

        self.live_controls_panel = LiveControlsPanel(self.manager, right_widget)
        right_layout.addWidget(self.live_controls_panel)

        self.system_controls_panel = SystemControlsPanel(right_widget)
        self.system_controls_panel.open_browser_requested.connect(self._open_browser)
        self.system_controls_panel.open_hub_requested.connect(self._open_hub)
        self.system_controls_panel.open_combat_settings_requested.connect(self._open_combat_settings)
        right_layout.addWidget(self.system_controls_panel)

        right_layout.addStretch()
        content_layout.addWidget(right_widget, stretch=1)

        main_layout.addWidget(content_widget)

        self.grip = CustomSizeGrip(self); self.grip.setFixedSize(16, 16)

        # Dynamic layout sizing
        self.setMinimumSize(self.minimumSizeHint())
        self.resize(self.sizeHint())

        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.live_controls_panel.update_stats)
        if self.isVisible():
            self.stats_timer.start(500)

    def _adjust_size_if_needed(self) -> None:
        """Dynamically adjusts window size if content constraints exceed current dimensions."""
        hint: QSize = self.sizeHint()
        min_hint: QSize = self.minimumSizeHint()
        target_w: int = max(self.width(), hint.width(), min_hint.width())
        target_h: int = max(self.height(), hint.height(), min_hint.height())
        if target_w != self.width() or target_h != self.height():
            self.resize(target_w, target_h)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self.manager.spawning_system.is_active:
            self.manager.spawning_system.cancel_all()
            event.accept()
            return
        super().keyPressEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.live_controls_panel.update_stats()
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

    def _open_hub(self) -> None:
        if self.hub_window is None or not self.hub_window.isVisible():
            self.hub_window = ModManagerHub(self.manager.mod_manager)
            self.hub_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.hub_window.destroyed.connect(self._on_hub_destroyed)
            self.hub_window.mods_updated.connect(self.spawn_panel.refresh_spawn_list)
            self.hub_window.show()
        else:
            self.hub_window.activateWindow()

    def _on_hub_destroyed(self) -> None:
        self.hub_window = None

    def _open_combat_settings(self) -> None:
        if self.combat_settings_dialog is None or not self.combat_settings_dialog.isVisible():
            self.combat_settings_dialog = CombatSettingsDialog(self)
            self.combat_settings_dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.combat_settings_dialog.destroyed.connect(self._on_combat_settings_destroyed)
            self.combat_settings_dialog.show()
        else:
            self.combat_settings_dialog.activateWindow()

    def _on_combat_settings_destroyed(self) -> None:
        self.combat_settings_dialog = None

    def _open_browser(self) -> None:
        if self.browser_dialog is None or not self.browser_dialog.isVisible():
            self.browser_dialog = ModBrowserDialog(self.manager.mod_manager)
            self.browser_dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.browser_dialog.destroyed.connect(self._on_browser_destroyed)
            self.browser_dialog.mods_updated.connect(self.spawn_panel.refresh_spawn_list)
            self.browser_dialog.show()
        else:
            self.browser_dialog.activateWindow()

    def _on_browser_destroyed(self) -> None:
        self.browser_dialog = None


from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QApplication, QLabel, QFrame, QHBoxLayout
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QGuiApplication

from pytoningans.ui.theme import LIGHT_THEME, DARK_THEME


class SystemControlsPanel(QWidget):
    """Panel managing mod hub, combat settings dialogs, theme toggling, and shutdown."""

    open_hub_requested: Signal = Signal()
    open_combat_settings_requested: Signal = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._is_dark_mode: bool = True
        self._setup_ui()

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("MenuSeparator")
        return sep

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Mod Management & Settings Section
        mod_label = QLabel("Management & Settings:")
        mod_label.setObjectName("SectionHeader")
        layout.addWidget(mod_label)

        mgmt_layout = QHBoxLayout()
        mgmt_layout.setSpacing(8)

        self.manage_btn = QPushButton("Manage Mods")
        self.manage_btn.setToolTip("Open the Mod Manager Hub")
        self.manage_btn.clicked.connect(self.open_hub_requested.emit)

        self.combat_settings_btn = QPushButton("Combat Settings")
        self.combat_settings_btn.setToolTip("Configure damage indicators and health bar display preferences")
        self.combat_settings_btn.clicked.connect(self.open_combat_settings_requested.emit)

        mgmt_layout.addWidget(self.manage_btn, stretch=1)
        mgmt_layout.addWidget(self.combat_settings_btn, stretch=1)
        layout.addLayout(mgmt_layout)

        layout.addWidget(self._create_separator())

        # System Controls Section
        sys_layout = QHBoxLayout()
        sys_layout.setSpacing(8)

        self.theme_btn = QPushButton("Switch to Light Mode")
        self.theme_btn.clicked.connect(self._toggle_theme)

        self.shutdown_btn = QPushButton("Shutdown")
        self.shutdown_btn.setObjectName("DangerBtn")
        self.shutdown_btn.setToolTip("Completely quit PyToNingans")
        self.shutdown_btn.clicked.connect(QApplication.quit)

        sys_layout.addWidget(self.theme_btn, stretch=1)
        sys_layout.addWidget(self.shutdown_btn, stretch=1)
        layout.addLayout(sys_layout)

    def _toggle_theme(self) -> None:
        self._is_dark_mode = not self._is_dark_mode
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return

        if self._is_dark_mode:
            app.setStyleSheet(DARK_THEME)
            self.theme_btn.setText("Switch to Light Mode")
        else:
            app.setStyleSheet(LIGHT_THEME)
            self.theme_btn.setText("Switch to Dark Mode")


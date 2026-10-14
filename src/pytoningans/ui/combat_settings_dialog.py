from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QSpinBox, QPushButton, QFrame, QWidget
)
from PySide6.QtCore import Qt

from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.core.settings import SettingsManager, HealthBarMode


class CombatSettingsDialog(QDialog):
    """
    Settings dialog allowing users to customize combat visual indicators:
    - Health bar display mode (on damage only, always, hidden)
    - Auto-hide delay
    - Floating damage numbers
    - Damage impact shake
    - Numerical HP display
    """
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.settings_mgr = SettingsManager.get()
        self._is_loading: bool = True
        self._setup_ui()
        self._load_current_values()
        self._is_loading = False

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("MenuSeparator")
        return sep

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(380, 440)
        self.setMinimumSize(340, 400)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(
            self, "Combat Visuals Settings", can_minimize=False, can_maximize=False
        )
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header description
        info_label = QLabel("Configure real-time combat indicators and visual feedback.")
        info_label.setObjectName("HelperText")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addWidget(self._create_separator())

        # Section 1: Health Bar Behavior
        hb_header = QLabel("Health Bar Display:")
        hb_header.setObjectName("SectionHeader")
        layout.addWidget(hb_header)

        # Mode dropdown
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Display Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Show On Damage Only (Default)", HealthBarMode.ON_DAMAGE.value)
        self.mode_combo.addItem("Always Visible", HealthBarMode.ALWAYS.value)
        self.mode_combo.addItem("Hidden / Disabled", HealthBarMode.HIDDEN.value)
        self.mode_combo.currentIndexChanged.connect(self._on_values_changed)
        mode_layout.addWidget(self.mode_combo, stretch=1)
        layout.addLayout(mode_layout)

        # Auto-hide duration
        self.hide_delay_layout = QHBoxLayout()
        self.hide_delay_label = QLabel("Auto-Hide Delay:")
        self.hide_delay_spin = QSpinBox()
        self.hide_delay_spin.setRange(1, 15)
        self.hide_delay_spin.setSuffix(" sec")
        self.hide_delay_spin.setValue(3)
        self.hide_delay_spin.setToolTip("How long the health bar remains visible after taking damage")
        self.hide_delay_spin.valueChanged.connect(self._on_values_changed)
        self.hide_delay_layout.addWidget(self.hide_delay_label)
        self.hide_delay_layout.addWidget(self.hide_delay_spin, stretch=1)
        layout.addLayout(self.hide_delay_layout)

        layout.addWidget(self._create_separator())

        # Section 2: Visual Feedback Features
        feedback_header = QLabel("Visual Feedback:")
        feedback_header.setObjectName("SectionHeader")
        layout.addWidget(feedback_header)

        self.damage_numbers_cb = QCheckBox("Show Floating Damage Numbers")
        self.damage_numbers_cb.setToolTip("Displays animated pop-up damage text when attacks hit.")
        self.damage_numbers_cb.toggled.connect(self._on_values_changed)
        layout.addWidget(self.damage_numbers_cb)

        self.health_shake_cb = QCheckBox("Enable Damage Impact Shake")
        self.health_shake_cb.setToolTip("Shakes the health bar proportionally based on damage dealt relative to max health.")
        self.health_shake_cb.toggled.connect(self._on_values_changed)
        layout.addWidget(self.health_shake_cb)

        self.health_numbers_cb = QCheckBox("Show HP Values Inside Bar")
        self.health_numbers_cb.setToolTip("Displays numerical current and max health (e.g. 85 / 100) inside the bar.")
        self.health_numbers_cb.toggled.connect(self._on_values_changed)
        layout.addWidget(self.health_numbers_cb)

        layout.addStretch()
        layout.addWidget(self._create_separator())

        # Bottom Buttons: Reset Defaults & Close
        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Reset Defaults")
        self.reset_btn.setToolTip("Restore default visual combat preferences")
        self.reset_btn.clicked.connect(self._on_reset_defaults)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        main_layout.addWidget(content)

    def _load_current_values(self) -> None:
        settings = self.settings_mgr.settings

        # Mode
        idx: int = self.mode_combo.findData(settings.health_bar_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)

        # Delay
        self.hide_delay_spin.setValue(max(1, settings.auto_hide_delay_ms // 1000))
        self.hide_delay_spin.setEnabled(settings.health_bar_mode == HealthBarMode.ON_DAMAGE.value)

        # Checkboxes
        self.damage_numbers_cb.setChecked(settings.show_damage_numbers)
        self.health_shake_cb.setChecked(settings.enable_health_shake)
        self.health_numbers_cb.setChecked(settings.show_health_numbers)

    def _on_values_changed(self) -> None:
        if self._is_loading: return

        selected_mode: str = self.mode_combo.currentData()
        self.hide_delay_spin.setEnabled(selected_mode == HealthBarMode.ON_DAMAGE.value)

        self.settings_mgr.update_settings(
            health_bar_mode=selected_mode,
            show_damage_numbers=self.damage_numbers_cb.isChecked(),
            show_health_numbers=self.health_numbers_cb.isChecked(),
            enable_health_shake=self.health_shake_cb.isChecked(),
            auto_hide_delay_ms=self.hide_delay_spin.value() * 1000,
        )

    def _on_reset_defaults(self) -> None:
        self._is_loading = True
        self.settings_mgr.reset_to_defaults()
        self._load_current_values()
        self._is_loading = False

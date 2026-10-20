"""
PyToNingans - Application Settings Dialog
=========================================
Generic, multi-category application settings dialog featuring:
- Combat and Visuals (Health bars, floating numbers, damage shake, window physics)
- Spawning and Environment (Spawn area bounds, window avoidance)
- Developer Mode (Debug tools, test catalog seeding, cache wiping, directory links)
Includes automatic content-based resizing, responsive scrolling, and a custom resize grip.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QLayoutItem, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QSpinBox, QPushButton, QFrame, QWidget, QTabWidget, QMessageBox,
    QScrollArea, QLineEdit, QFormLayout, QMenu, QFileDialog
)
from PySide6.QtCore import Qt, QUrl, QRect, QSize
from PySide6.QtGui import QDesktopServices, QResizeEvent, QGuiApplication, QScreen, QAction

from pytoningans.core.settings import SettingsManager, HealthBarMode
from pytoningans.utils.paths import get_settings_path, get_base_path
from pytoningans.utils.assets import get_google_icon, get_github_icon
from pytoningans.utils.avatar import AvatarLabel, get_avatar_cache_dir
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.mod_editor.components import CustomSizeGrip
from pytoningans.ui.mod_browser.client import ModBrowserClient
from pytoningans.ui.mod_browser.auth import AuthManager
from pytoningans.ui.mod_browser.components.auth_dialog import AuthDialog

if TYPE_CHECKING:
    from pytoningans.ui.mod_browser.auth import UserProfile


class SettingsDialog(QDialog):
    """
    Central settings dialog allowing users to customize:
    - Real-time combat visual feedback and indicators
    - Spawning behaviors and desktop environment boundaries
    - Developer / debug mode and offline catalog fixtures
    Dynamically auto-resizes to fit content with a custom resize grip.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.settings_manager: SettingsManager = SettingsManager.get()
        self._is_loading: bool = True
        self._setup_ui()
        self._load_current_values()
        self._adjust_size_for_content()
        self._center_window()
        self._is_loading = False

        from pytoningans.ui.mod_browser.auth import AuthManager
        AuthManager.get().auth_state_changed.connect(lambda _: self._update_profile_status_ui())

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine); sep.setObjectName("MenuSeparator")
        return sep

    def _wrap_tab_in_scroll(self, widget: QWidget) -> QScrollArea:
        """Wraps tab content in a borderless scroll area so contents never get clipped on small screens or high DPI."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setAutoFillBackground(False)
        widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        scroll.setWidget(widget)
        return scroll

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumSize(400, 440)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(
            self, "Application Settings", can_minimize=False, can_maximize=True
        )
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 14, 16, 14); content_layout.setSpacing(10)

        # Tab Widget for generic category organization
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(lambda _: self._adjust_size_for_content())

        # -------------------------------------------------------------
        # Tab 1: Creator Profile
        # -------------------------------------------------------------
        profile_tab = QWidget()
        profile_layout = QVBoxLayout(profile_tab)
        profile_layout.setContentsMargins(12, 12, 12, 12); profile_layout.setSpacing(10)

        profile_info = QLabel(
            "Manage your creator handle and community account.\n"
            "Your creator name is automatically assigned when authoring or publishing mods."
        )
        profile_info.setObjectName("HelperText"); profile_info.setWordWrap(True)
        profile_layout.addWidget(profile_info)
        profile_layout.addWidget(self._create_separator())

        # Account Status Badge Card with Circular Avatar
        self.profile_status_card = QFrame()
        self.profile_status_card.setFrameShape(QFrame.Shape.StyledPanel)
        self.profile_status_card.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 46, 0.6);
                border: 1px solid #45475a;
                border-radius: 6px;
            }
        """)
        card_layout = QHBoxLayout(self.profile_status_card)
        card_layout.setContentsMargins(12, 10, 12, 10); card_layout.setSpacing(12)

        # Dynamic Circular Avatar Widget
        self.avatar_lbl = AvatarLabel(size=56, border_color="#89b4fa", border_width=2)
        card_layout.addWidget(self.avatar_lbl)

        # Status text, handle, badges, and avatar picture controls
        status_text_layout = QVBoxLayout()
        status_text_layout.setSpacing(3)

        name_badge_layout = QHBoxLayout()
        name_badge_layout.setSpacing(6)
        self.profile_name_title = QLabel("Creator: Modder")
        self.profile_name_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cdd6f4;")
        name_badge_layout.addWidget(self.profile_name_title)

        self.badges_layout = QHBoxLayout()
        self.badges_layout.setSpacing(4)
        name_badge_layout.addLayout(self.badges_layout)
        name_badge_layout.addStretch()
        status_text_layout.addLayout(name_badge_layout)

        self.profile_account_status = QLabel("Offline Local Profile (No Cloud Sync)")
        self.profile_account_status.setStyleSheet("font-size: 11px; color: #a6adc8;")
        status_text_layout.addWidget(self.profile_account_status)

        # Avatar picture action buttons
        avatar_btn_row = QHBoxLayout()
        avatar_btn_row.setSpacing(6)
        self.change_avatar_btn = QPushButton("Change Picture...")
        self.change_avatar_btn.setObjectName("SecondaryBtn")
        self.change_avatar_btn.setStyleSheet("padding: 2px 8px; font-size: 10px;")
        self.change_avatar_btn.clicked.connect(self._on_change_avatar_clicked)
        avatar_btn_row.addWidget(self.change_avatar_btn)

        self.reset_avatar_btn = QPushButton("Reset Picture")
        self.reset_avatar_btn.setStyleSheet("padding: 2px 8px; font-size: 10px; color: #a6adc8;")
        self.reset_avatar_btn.clicked.connect(self._on_reset_avatar_clicked)
        avatar_btn_row.addWidget(self.reset_avatar_btn)
        avatar_btn_row.addStretch()
        status_text_layout.addLayout(avatar_btn_row)

        card_layout.addLayout(status_text_layout, stretch=1)

        self.auth_action_btn = QPushButton("Connect Cloud")
        self.auth_action_btn.setObjectName("SecondaryBtn")
        self.auth_action_btn.clicked.connect(self._on_profile_auth_action)
        card_layout.addWidget(self.auth_action_btn)

        profile_layout.addWidget(self.profile_status_card)

        # Connected Services & Verification Card
        conn_header = QLabel("Connected Accounts & Verification:"); conn_header.setObjectName("SectionHeader")
        profile_layout.addWidget(conn_header)

        self.conn_card = QFrame()
        self.conn_card.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 37, 0.5);
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        conn_layout = QVBoxLayout(self.conn_card)
        conn_layout.setContentsMargins(10, 8, 10, 8); conn_layout.setSpacing(8)

        # GitHub row
        gh_row = QHBoxLayout(); gh_row.setSpacing(10)
        gh_icon_lbl = QLabel()
        gh_icon_lbl.setPixmap(get_github_icon().pixmap(18, 18))
        gh_row.addWidget(gh_icon_lbl)
        gh_title = QLabel("GitHub Account:")
        gh_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #cdd6f4; min-width: 105px;")
        gh_row.addWidget(gh_title)

        self.gh_status_lbl = QLabel("Not connected")
        self.gh_status_lbl.setStyleSheet("font-size: 11px; color: #a6adc8;")
        gh_row.addWidget(self.gh_status_lbl, stretch=1)

        self.gh_action_btn = QPushButton("Connect GitHub")
        self.gh_action_btn.setStyleSheet("padding: 3px 10px; font-size: 11px;")
        self.gh_action_btn.clicked.connect(self._on_github_action_clicked)
        gh_row.addWidget(self.gh_action_btn)
        conn_layout.addLayout(gh_row)

        line_sep = QFrame(); line_sep.setFrameShape(QFrame.Shape.HLine)
        line_sep.setStyleSheet("background-color: #313244; max-height: 1px;")
        conn_layout.addWidget(line_sep)

        # Google row
        google_row = QHBoxLayout(); google_row.setSpacing(10)
        google_icon_lbl = QLabel()
        google_icon_lbl.setPixmap(get_google_icon().pixmap(18, 18))
        google_row.addWidget(google_icon_lbl)
        google_title = QLabel("Google Account:")
        google_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #cdd6f4; min-width: 105px;")
        google_row.addWidget(google_title)

        self.google_status_lbl = QLabel("Not connected")
        self.google_status_lbl.setStyleSheet("font-size: 11px; color: #a6adc8;")
        google_row.addWidget(self.google_status_lbl, stretch=1)

        self.google_action_btn = QPushButton("Connect Google")
        self.google_action_btn.setStyleSheet("padding: 3px 10px; font-size: 11px;")
        self.google_action_btn.clicked.connect(self._on_google_action_clicked)
        google_row.addWidget(self.google_action_btn)
        conn_layout.addLayout(google_row)

        profile_layout.addWidget(self.conn_card)
        profile_layout.addWidget(self._create_separator())

        # Form: Creator Name / Handle & Bio
        name_form = QFormLayout()
        name_form.setSpacing(8)
        self.creator_name_input = QLineEdit()
        self.creator_name_input.setPlaceholderText("e.g. MetaDusk, RetroGamer...")
        name_form.addRow("Creator Handle:", self.creator_name_input)

        self.creator_bio_input = QLineEdit()
        self.creator_bio_input.setPlaceholderText("e.g. Pixel artist & idler sandbox modder")
        name_form.addRow("Bio / Tagline:", self.creator_bio_input)

        profile_layout.addLayout(name_form)

        # Save profile button
        btn_box = QHBoxLayout()
        self.save_profile_btn = QPushButton("Save Profile")
        self.save_profile_btn.setObjectName("SuccessBtn")
        self.save_profile_btn.setToolTip("Persist your creator handle across all mod editor tools")
        self.save_profile_btn.clicked.connect(self._save_profile)
        btn_box.addWidget(self.save_profile_btn)
        btn_box.addStretch()
        profile_layout.addLayout(btn_box)

        # Helper note
        tip_lbl = QLabel(
            "💡 Tip: Setting your creator handle here ensures you won't need to retype it "
            "each time you create a mod, modpack, or release update."
        )
        tip_lbl.setStyleSheet("color: #89b4fa; font-size: 11px; font-style: italic;")
        tip_lbl.setWordWrap(True)
        profile_layout.addWidget(tip_lbl)

        profile_layout.addStretch()
        self.tabs.addTab(self._wrap_tab_in_scroll(profile_tab), "Profile")

        # -------------------------------------------------------------
        # Tab 2: Combat and Visuals
        # -------------------------------------------------------------
        combat_tab = QWidget()
        combat_layout = QVBoxLayout(combat_tab)
        combat_layout.setContentsMargins(12, 12, 12, 12); combat_layout.setSpacing(10)

        info_label = QLabel("Configure real-time combat indicators and visual feedback.")
        info_label.setObjectName("HelperText"); info_label.setWordWrap(True)
        combat_layout.addWidget(info_label)
        combat_layout.addWidget(self._create_separator())

        # Health Bar Behavior
        hb_header = QLabel("Health Bar Display:"); hb_header.setObjectName("SectionHeader")
        combat_layout.addWidget(hb_header)

        mode_layout = QHBoxLayout()
        mode_lbl = QLabel("Display Mode:")
        mode_lbl.setFixedWidth(140)
        mode_layout.addWidget(mode_lbl)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Show On Damage Only (Default)", HealthBarMode.ON_DAMAGE)
        self.mode_combo.addItem("Always Visible", HealthBarMode.ALWAYS)
        self.mode_combo.addItem("Hidden / Disabled", HealthBarMode.HIDDEN)
        self.mode_combo.currentIndexChanged.connect(self._on_values_changed)
        mode_layout.addWidget(self.mode_combo, stretch=1)
        combat_layout.addLayout(mode_layout)

        self.hide_delay_layout = QHBoxLayout()
        self.hide_delay_label = QLabel("Auto-Hide Delay:")
        self.hide_delay_label.setFixedWidth(140)
        self.hide_delay_spin = QSpinBox()
        self.hide_delay_spin.setRange(1, 15); self.hide_delay_spin.setSuffix(" sec"); self.hide_delay_spin.setValue(3)
        self.hide_delay_spin.setToolTip("How long the health bar remains visible after taking damage")
        self.hide_delay_spin.valueChanged.connect(self._on_values_changed)
        self.hide_delay_layout.addWidget(self.hide_delay_label)
        self.hide_delay_layout.addWidget(self.hide_delay_spin, stretch=1)
        combat_layout.addLayout(self.hide_delay_layout)

        combat_layout.addWidget(self._create_separator())

        # Visual Feedback Features
        feedback_header = QLabel("Visual Feedback:"); feedback_header.setObjectName("SectionHeader")
        combat_layout.addWidget(feedback_header)

        self.damage_numbers_cb = QCheckBox("Show Floating Damage Numbers")
        self.damage_numbers_cb.setToolTip("Displays animated pop-up damage text when attacks hit.")
        self.damage_numbers_cb.toggled.connect(self._on_values_changed)
        combat_layout.addWidget(self.damage_numbers_cb)

        self.health_shake_cb = QCheckBox("Enable Damage Impact Shake")
        self.health_shake_cb.setToolTip(
            "Shakes the health bar proportionally based on damage dealt relative to max health."
        )
        self.health_shake_cb.toggled.connect(self._on_values_changed)
        combat_layout.addWidget(self.health_shake_cb)

        self.health_numbers_cb = QCheckBox("Show HP Values Inside Bar")
        self.health_numbers_cb.setToolTip(
            "Displays numerical current and max health (e.g. 85 / 100) inside the bar."
        )
        self.health_numbers_cb.toggled.connect(self._on_values_changed)
        combat_layout.addWidget(self.health_numbers_cb)

        combat_layout.addWidget(self._create_separator())

        # Desktop Window Physics
        env_header = QLabel("Desktop Environment Physics:"); env_header.setObjectName("SectionHeader")
        combat_layout.addWidget(env_header)

        self.window_physics_cb = QCheckBox("Enable Desktop Window Physics")
        self.window_physics_cb.setToolTip(
            "Allows entities and items to stand, walk, and land on non-maximized desktop application windows."
        )
        self.window_physics_cb.toggled.connect(self._on_values_changed)
        combat_layout.addWidget(self.window_physics_cb)

        combat_layout.addStretch()
        self.tabs.addTab(self._wrap_tab_in_scroll(combat_tab), "Combat and Visuals")

        # -------------------------------------------------------------
        # Tab 2: Spawning and Environment
        # -------------------------------------------------------------
        spawn_tab = QWidget()
        spawn_layout = QVBoxLayout(spawn_tab)
        spawn_layout.setContentsMargins(12, 12, 12, 12); spawn_layout.setSpacing(10)

        spawn_info = QLabel("Configure where and how entities spawn on your desktop.")
        spawn_info.setObjectName("HelperText"); spawn_info.setWordWrap(True)
        spawn_layout.addWidget(spawn_info)
        spawn_layout.addWidget(self._create_separator())

        sp_header = QLabel("Desktop Placement Behavior:"); sp_header.setObjectName("SectionHeader")
        spawn_layout.addWidget(sp_header)

        self.avoid_window_cb = QCheckBox("Avoid Spawning Over Open Windows")
        self.avoid_window_cb.setToolTip(
            "Attempts to find empty screen desktop areas away from foreground windows when spawning."
        )
        self.avoid_window_cb.toggled.connect(self._on_values_changed)
        spawn_layout.addWidget(self.avoid_window_cb)

        area_layout = QHBoxLayout()
        area_lbl = QLabel("Spawn Boundary Area:")
        area_lbl.setFixedWidth(180)
        area_layout.addWidget(area_lbl)
        self.spawn_area_combo = QComboBox()
        self.spawn_area_combo.addItem("Full Primary Screen", "screen")
        self.spawn_area_combo.addItem("Active Desktop Bounds", "desktop")
        self.spawn_area_combo.currentIndexChanged.connect(self._on_values_changed)
        area_layout.addWidget(self.spawn_area_combo, stretch=1)
        spawn_layout.addLayout(area_layout)

        spawn_layout.addStretch()
        self.tabs.addTab(self._wrap_tab_in_scroll(spawn_tab), "Spawning")

        # -------------------------------------------------------------
        # Tab 3: Developer and Debugging
        # -------------------------------------------------------------
        dev_tab = QWidget()
        dev_layout = QVBoxLayout(dev_tab)
        dev_layout.setContentsMargins(12, 12, 12, 12); dev_layout.setSpacing(10)

        dev_info = QLabel(
            "Developer tools, diagnostic overlays, and testing catalog controls.\n"
            "Enable to unlock debug menus across the application."
        )
        dev_info.setObjectName("HelperText"); dev_info.setWordWrap(True)
        dev_layout.addWidget(dev_info)
        dev_layout.addWidget(self._create_separator())

        self.debug_mode_cb = QCheckBox("Enable Developer Mode")
        self.debug_mode_cb.setToolTip(
            "Displays the Debug menu in the Mod Browser and unlocks diagnostic testing tools."
        )
        self.debug_mode_cb.toggled.connect(self._on_values_changed)
        self.debug_mode_cb.toggled.connect(self._on_debug_mode_toggled)
        dev_layout.addWidget(self.debug_mode_cb)

        # Developer Quick Actions Box
        self.dev_actions_box = QWidget()
        actions_layout = QVBoxLayout(self.dev_actions_box)
        actions_layout.setContentsMargins(0, 8, 0, 0); actions_layout.setSpacing(8)

        act_label = QLabel("Catalog Testing Tools:"); act_label.setObjectName("SectionHeader")
        actions_layout.addWidget(act_label)

        btn_row_1 = QHBoxLayout(); btn_row_1.setSpacing(8)
        self.seed_catalog_btn = QPushButton("Load Demo / Seed Catalog")
        self.seed_catalog_btn.setToolTip("Inject built-in demo items into the local catalog cache for testing")
        self.seed_catalog_btn.clicked.connect(self._on_load_seed_catalog)
        btn_row_1.addWidget(self.seed_catalog_btn)

        self.clear_cache_btn = QPushButton("Clear Catalog Cache")
        self.clear_cache_btn.setToolTip("Wipe cached community items to test empty catalog state")
        self.clear_cache_btn.clicked.connect(self._on_clear_catalog_cache)
        btn_row_1.addWidget(self.clear_cache_btn)
        actions_layout.addLayout(btn_row_1)

        actions_layout.addWidget(self._create_separator())

        dir_label = QLabel("Quick Folder Access:"); dir_label.setObjectName("SectionHeader")
        actions_layout.addWidget(dir_label)

        btn_row_2 = QHBoxLayout(); btn_row_2.setSpacing(8)
        self.open_data_btn = QPushButton("Open App Data Folder")
        self.open_data_btn.clicked.connect(self._open_app_data_dir)
        btn_row_2.addWidget(self.open_data_btn)

        self.open_mods_btn = QPushButton("Open Local Mods Folder")
        self.open_mods_btn.clicked.connect(self._open_mods_dir)
        btn_row_2.addWidget(self.open_mods_btn)
        actions_layout.addLayout(btn_row_2)

        dev_layout.addWidget(self.dev_actions_box)
        dev_layout.addStretch()
        self.tabs.addTab(self._wrap_tab_in_scroll(dev_tab), "Developer")

        content_layout.addWidget(self.tabs)

        # -------------------------------------------------------------
        # Bottom Buttons: Reset Defaults and Close
        # -------------------------------------------------------------
        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Reset Defaults")
        self.reset_btn.setToolTip("Restore all settings back to original defaults")
        self.reset_btn.clicked.connect(self._on_reset_defaults)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        content_layout.addLayout(btn_layout)

        main_layout.addWidget(content)

        # Resize grip at the bottom-right corner
        self.grip = CustomSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        self.grip.move(
            self.width() - self.grip.width(),
            self.height() - self.grip.height(),
        )

    def _adjust_size_for_content(self) -> None:
        """Dynamically computes required dimensions to display all content comfortably without clipping."""
        max_tab_w: int = 0
        max_tab_h: int = 0
        for i in range(self.tabs.count()):
            tab_widget: Optional[QWidget] = self.tabs.widget(i)
            if tab_widget is None: continue
            tab: QWidget = tab_widget
            inner: Optional[QWidget] = tab.widget() if isinstance(tab, QScrollArea) else tab
            
            if inner is None: continue
            hint: QSize = inner.sizeHint()
            max_tab_w = max(max_tab_w, hint.width())
            max_tab_h = max(max_tab_h, hint.height())

        #? Title bar (32) + Tabs header (~38) + Padding/Margins (~32) +
        #? Bottom buttons (~48) + Extra breathing room
        target_w: int = max(self.width(), 460, max_tab_w + 48)
        target_h: int = max(self.height(), 520, max_tab_h + 170)

        screen: Optional[QScreen] = QGuiApplication.primaryScreen()
        if screen is not None:
            avail_geom: QRect = screen.availableGeometry()
            target_w = min(target_w, int(avail_geom.width() * 0.9))
            target_h = min(target_h, int(avail_geom.height() * 0.9))

        if target_w != self.width() or target_h != self.height():
            self.resize(target_w, target_h)

        if hasattr(self, "grip"):
            self.grip.move(
                self.width() - self.grip.width(),
                self.height() - self.grip.height(),
            )

    def _center_window(self) -> None:
        """Centers the dialog window on the primary screen."""
        screen: Optional[QScreen] = QGuiApplication.primaryScreen()
        if screen is None: return
        screen_geom: QRect = screen.availableGeometry()
        window_geom: QRect = self.frameGeometry()
        window_geom.moveCenter(screen_geom.center())
        self.move(window_geom.topLeft())

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.grip.move(
            self.width() - self.grip.width(),
            self.height() - self.grip.height(),
        )

    def open_profile_tab(self) -> None:
        """Switches directly to the Creator Profile tab."""
        self.tabs.setCurrentIndex(0)

    def _update_profile_status_ui(self) -> None:
        auth: AuthManager = AuthManager.get()
        user: Optional[UserProfile] = auth.current_user
        name: str = auth.get_creator_name()
        initial: str = name[0].upper() if name else "M"

        # Update dynamic avatar
        avatar_source: Optional[str] = auth.get_creator_avatar()
        self.avatar_lbl.set_avatar(avatar_source, initial=initial)

        # Clear existing badges
        while self.badges_layout.count():
            item: Optional[QLayoutItem] = self.badges_layout.takeAt(0)
            if item is None: continue
            w: Optional[QWidget] = item.widget()
            if w is None: continue
            w.deleteLater()

        self.profile_name_title.setText(f"Creator: {name}")

        badges: list[str] = user.badges if user is not None else []
        is_dev: bool = user.is_developer if user is not None else False

        if is_dev:
            self.avatar_lbl.set_border_color("#cba6f7")
            dev_badge = QLabel("★ Developer")
            dev_badge.setToolTip("Recognized PyToNingans Core Developer & Maintainer")
            dev_badge.setStyleSheet("""
                background-color: rgba(203, 166, 247, 0.25);
                color: #cba6f7;
                border: 1px solid #cba6f7;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            """)
            self.badges_layout.addWidget(dev_badge)

        if "Verified Creator" in badges:
            verified_badge = QLabel("✓ Verified Creator")
            verified_badge.setToolTip("Authenticated community mod creator via OAuth")
            verified_badge.setStyleSheet("""
                background-color: rgba(137, 220, 235, 0.2);
                color: #89dceb;
                border: 1px solid #89dceb;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            """)
            self.badges_layout.addWidget(verified_badge)
        elif "Offline Creator" in badges or not auth.is_authenticated:
            self.avatar_lbl.set_border_color("#89b4fa")
            off_badge = QLabel("● Offline Creator")
            off_badge.setStyleSheet("""
                background-color: rgba(108, 112, 134, 0.2);
                color: #a6adc8;
                border: 1px solid #6c7086;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
            """)
            self.badges_layout.addWidget(off_badge)
        self.badges_layout.addStretch()

        # Update account status card
        if (
            auth.is_authenticated and
            auth.is_cloud_configured and
            user is not None and
            not user.id.startswith("local_")
        ):
            self.profile_account_status.setText(
                f"Cloud Account: {user.email} (via {user.display_provider})"
            )
            self.profile_account_status.setStyleSheet("font-size: 11px; color: #a6e3a1;")
            self.auth_action_btn.setText("Account Options")
        elif auth.is_authenticated and user is not None:
            self.profile_account_status.setText(f"Offline Profile: {user.username} (Local)")
            self.profile_account_status.setStyleSheet("font-size: 11px; color: #cba6f7;")
            self.auth_action_btn.setText("Connect Cloud")
        else:
            self.profile_account_status.setText("Offline Local Profile (No Cloud Sync)")
            self.profile_account_status.setStyleSheet("font-size: 11px; color: #a6adc8;")
            self.auth_action_btn.setText("Connect Cloud")

        # Update Connected Services Card
        providers: list[str] = user.providers if user else []
        gh_user: Optional[str] = user.github_username if user else None
        goog_email: Optional[str] = user.google_email if user else None

        # GitHub row
        has_github: bool = (
            ("github" in providers) or
            (user is not None and user.primary_provider == "github") or
            bool(gh_user)
        )
        if has_github:
            gh_display: str = f"@{gh_user}" if gh_user else "Linked"
            self.gh_status_lbl.setText(
                f"Connected as <b>{gh_display}</b> <span style='color: #a6e3a1;'>[Verified ✓]</span>"
            )
            self.gh_status_lbl.setStyleSheet("font-size: 11px; color: #cdd6f4;")
            self.gh_action_btn.setText("View GitHub Profile ↗")
            self.gh_action_btn.setToolTip(f"Open https://github.com/{gh_user or ''} in default browser")
            self.gh_action_btn.setEnabled(bool(gh_user))
        else:
            self.gh_status_lbl.setText("Not connected")
            self.gh_status_lbl.setStyleSheet("font-size: 11px; color: #6c7086;")
            self.gh_action_btn.setText("Connect GitHub")
            self.gh_action_btn.setToolTip("Sign in / link your GitHub account")
            self.gh_action_btn.setEnabled(True)

        # Google row
        has_google: bool = (
            ("google" in providers) or
            (user is not None and user.primary_provider == "google")
        )
        if has_google:
            g_disp: str = goog_email or (user.email if user else "Linked")
            self.google_status_lbl.setText(
                f"Connected ({g_disp}) <span style='color: #a6e3a1;'>[Google Verified ✓]</span>"
            )
            self.google_status_lbl.setStyleSheet("font-size: 11px; color: #cdd6f4;")
            self.google_action_btn.setText("Connected ✓")
            self.google_action_btn.setEnabled(False)
        else:
            self.google_status_lbl.setText("Not connected")
            self.google_status_lbl.setStyleSheet("font-size: 11px; color: #6c7086;")
            self.google_action_btn.setText("Connect Google")
            self.google_action_btn.setToolTip("Sign in / link your Google account")
            self.google_action_btn.setEnabled(True)

    def _on_change_avatar_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Picture",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)",
        )
        if not file_path:
            return

        import shutil
        src = Path(file_path)
        if not src.is_file():
            return

        dest_dir: Path = get_avatar_cache_dir()
        dest_file: Path = dest_dir / f"custom_{src.stem}{src.suffix}"
        try:
            shutil.copyfile(src, dest_file)
            auth: AuthManager = AuthManager.get()
            auth.update_profile(
                new_username=self.creator_name_input.text().strip() or auth.get_creator_name(),
                bio=self.creator_bio_input.text().strip(),
                custom_avatar_path=str(dest_file),
            )
            self._update_profile_status_ui()
            QMessageBox.information(self, "Avatar Updated", "Custom profile picture saved and applied!")
        except Exception as e:
            QMessageBox.warning(self, "Avatar Error", f"Failed to save profile picture: {e}")

    def _on_reset_avatar_clicked(self) -> None:
        auth: AuthManager = AuthManager.get()
        auth.update_profile(
            new_username=self.creator_name_input.text().strip() or auth.get_creator_name(),
            bio=self.creator_bio_input.text().strip(),
            custom_avatar_path="",
        )
        self._update_profile_status_ui()
        QMessageBox.information(
            self, "Avatar Reset", "Custom picture removed. Restored account provider avatar / default badge."
        )

    def _on_github_action_clicked(self) -> None:
        auth: AuthManager = AuthManager.get()
        user: Optional[UserProfile] = auth.current_user
        gh_user = user.github_username if user else None
        if user and ("github" in user.providers or gh_user):
            if gh_user:
                QDesktopServices.openUrl(QUrl(f"https://github.com/{gh_user}"))
        else:
            success, msg = auth.start_github_oauth()
            if success:
                QMessageBox.information(self, "GitHub Sign-In", msg)
            else:
                QMessageBox.warning(self, "OAuth Error", msg)

    def _on_google_action_clicked(self) -> None:
        auth: AuthManager = AuthManager.get()
        user: Optional[UserProfile] = auth.current_user
        if not user or ("google" not in user.providers and not user.google_email):
            success, msg = auth.start_google_oauth()
            if success:
                QMessageBox.information(self, "Google Sign-In", msg)
            else:
                QMessageBox.warning(self, "OAuth Error", msg)

    def _save_profile(self) -> None:
        auth: AuthManager = AuthManager.get()
        new_name: str = self.creator_name_input.text().strip() or "Modder"
        bio: str = self.creator_bio_input.text().strip()
        ok, msg = auth.update_profile(new_name, bio=bio)
        self._update_profile_status_ui()
        if ok:
            QMessageBox.information(self, "Profile Saved", msg)
        else:
            QMessageBox.warning(self, "Profile", msg)

    def _on_profile_auth_action(self) -> None:
        auth: AuthManager = AuthManager.get()
        if (
            auth.is_authenticated
            and auth.current_user is not None and
            not auth.current_user.id.startswith("local_")
        ):
            menu = QMenu(self)
            info_act: QAction = menu.addAction(f"Signed in as {auth.current_user.email}")
            info_act.setEnabled(False)
            menu.addSeparator()
            settings_act: QAction = menu.addAction("Cloud Server Settings")
            sign_out_act: QAction = menu.addAction("Sign Out")
            action: QAction = menu.exec(
                self.auth_action_btn.mapToGlobal(self.auth_action_btn.rect().bottomLeft())
            )
            if action == settings_act:
                dlg = AuthDialog(self)
                dlg.show_server_settings()
                dlg.exec()
            elif action == sign_out_act:
                auth.sign_out()
                self._update_profile_status_ui()
                QMessageBox.information(
                    self, "Signed Out", "You have signed out of your cloud account."
                )
        else:
            dlg = AuthDialog(self)
            dlg.exec()
            self._update_profile_status_ui()

    def _load_current_values(self) -> None:
        settings = self.settings_manager.settings

        # Profile tab
        auth: AuthManager = AuthManager.get()
        self.creator_name_input.setText(auth.get_creator_name())
        self.creator_bio_input.setText(auth.get_creator_bio())
        self._update_profile_status_ui()

        # Combat tab
        idx: int = self.mode_combo.findData(settings.health_bar_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)

        self.hide_delay_spin.setValue(max(1, settings.auto_hide_delay_ms // 1000))
        self.hide_delay_spin.setEnabled(settings.health_bar_mode == HealthBarMode.ON_DAMAGE)

        self.damage_numbers_cb.setChecked(settings.show_damage_numbers)
        self.health_shake_cb.setChecked(settings.enable_health_shake)
        self.health_numbers_cb.setChecked(settings.show_health_numbers)
        self.window_physics_cb.setChecked(settings.enable_window_physics)

        # Spawning tab
        self.avoid_window_cb.setChecked(settings.avoid_window_spawn)
        area_idx: int = self.spawn_area_combo.findData(settings.spawn_area_mode)
        if area_idx >= 0:
            self.spawn_area_combo.setCurrentIndex(area_idx)

        # Developer tab
        self.debug_mode_cb.setChecked(settings.enable_debug_mode)
        self.dev_actions_box.setEnabled(settings.enable_debug_mode)

    def _on_debug_mode_toggled(self, checked: bool) -> None:
        self.dev_actions_box.setEnabled(checked)

    def _on_values_changed(self) -> None:
        if self._is_loading:
            return

        selected_mode: str = self.mode_combo.currentData()
        self.hide_delay_spin.setEnabled(selected_mode == HealthBarMode.ON_DAMAGE)

        self.settings_manager.update_settings(
            health_bar_mode=selected_mode,
            show_damage_numbers=self.damage_numbers_cb.isChecked(),
            show_health_numbers=self.health_numbers_cb.isChecked(),
            enable_health_shake=self.health_shake_cb.isChecked(),
            auto_hide_delay_ms=self.hide_delay_spin.value() * 1000,
            enable_window_physics=self.window_physics_cb.isChecked(),
            avoid_window_spawn=self.avoid_window_cb.isChecked(),
            spawn_area_mode=self.spawn_area_combo.currentData() or "screen",
            enable_debug_mode=self.debug_mode_cb.isChecked(),
        )

    def _on_reset_defaults(self) -> None:
        self._is_loading = True
        self.settings_manager.reset_to_defaults()
        self._load_current_values()
        self._is_loading = False
        QMessageBox.information(self, "Settings Reset", "All application settings restored to defaults.")

    def _on_load_seed_catalog(self) -> None:
        client = ModBrowserClient(get_base_path() / "mods")
        added: int = client.load_seed_catalog()
        QMessageBox.information(
            self, "Demo Catalog Loaded",
            f"Successfully injected {added} demo/seed mods into your local catalog cache.",
        )

    def _on_clear_catalog_cache(self) -> None:
        client = ModBrowserClient(get_base_path() / "mods")
        client.clear_catalog_cache()
        QMessageBox.information(
            self, "Cache Reset",
            "Local community catalog cache has been cleared.",
        )

    def _open_app_data_dir(self) -> None:
        data_dir: Path = get_settings_path().parent
        data_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir)))

    def _open_mods_dir(self) -> None:
        mods_dir: Path = get_base_path() / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(mods_dir)))

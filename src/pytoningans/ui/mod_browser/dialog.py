"""
PyToNingans Mod Browser - Main Dialog Window
============================================
The core in-app interface for discovering, searching, inspecting, installing,
updating, rating, and publishing community mods and modpacks.
Integrates user accounts, offline fallback, and git-like release version management.
"""
from __future__ import annotations

import json, tempfile
from pathlib import Path
from typing import Optional, Any

from PySide6.QtCore import Qt, Signal, QRect, QThread
from PySide6.QtGui import QAction, QGuiApplication, QScreen, QResizeEvent, QCloseEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QWidget, QMessageBox, QFrame, QMenu, QProgressBar
)

from pytoningans.core.mod_manager import ModManager
from pytoningans.core.config_schema import CURRENT_CONFIG_VERSION
from pytoningans.core.constants import EntityType
from pytoningans.core.settings import SettingsManager
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.mod_editor.components import CustomSizeGrip
from pytoningans.ui.mod_inspector import ModInspectorDialog
from pytoningans.ui.settings_dialog import SettingsDialog, SettingsTab
from pytoningans.utils.assets import get_main_icon

from .auth import AuthManager, UserProfile
from .client import ModBrowserClient
from .models import CommunityModItem
from .async_workers import CatalogSyncWorker, ModInstallWorker
from .components.auth_dialog import AuthDialog
from .components.mod_card import ModCardWidget
from .components.filter_bar import FilterBarWidget
from .components.rating_dialog import RatingDialog
from .components.publish_dialog import PublishModDialog


class ModBrowserDialog(QDialog):
    """Full-featured community mod browser dialog window."""

    mods_updated = Signal()

    def __init__(self, mod_manager: ModManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.mod_manager: ModManager = mod_manager
        self.client: ModBrowserClient = ModBrowserClient(self.mod_manager.mods_dir)
        self.auth: AuthManager = AuthManager.get()
        self.settings_mgr: SettingsManager = SettingsManager.get()
        self._active_workers: list[Any] = []

        self.setWindowTitle("Community Mod Browser")
        self.setWindowIcon(get_main_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(940, 700); self.setMinimumSize(800, 540)

        self._cards: list[ModCardWidget] = []
        self._setup_ui()
        self.auth.auth_state_changed.connect(self._update_auth_ui)
        self._update_auth_ui(self.auth.current_user)
        self.settings_mgr.settings_changed.connect(self._update_debug_visibility)
        self._update_debug_visibility()
        self._update_status_indicator()
        self._apply_filters()
        self._center_window()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        # Title bar with window controls
        self.title_bar = CustomTitleBar(self, "Community Mod Browser")
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 14, 16, 12); content_layout.setSpacing(12)

        # --- Top Header and Actions Bar ---
        top_bar = QHBoxLayout(); top_bar.setSpacing(10)

        # Online Status Indicator and Cloud Connect Toggle
        self.status_badge = QLabel("● Offline Catalog")
        self.status_badge.setObjectName("StatusBadgeOffline")
        top_bar.addWidget(self.status_badge)

        self.cloud_btn = QPushButton("Connect to Cloud")
        self.cloud_btn.setObjectName("PrimaryBtn")
        self.cloud_btn.setToolTip("Connect to Supabase Cloud to view live community catalog")
        self.cloud_btn.clicked.connect(self._on_cloud_toggle_clicked)
        top_bar.addWidget(self.cloud_btn)

        top_bar.addStretch()

        # Creator Account / Sign-in Pill Button
        self.auth_btn = QPushButton("Sign In / Register")
        self.auth_btn.setObjectName("SecondaryBtn")
        self.auth_btn.clicked.connect(self._on_auth_btn_clicked)
        top_bar.addWidget(self.auth_btn)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Reload community catalog")
        self.refresh_btn.clicked.connect(self._refresh_catalog)
        top_bar.addWidget(self.refresh_btn)

        # Debug Tools Menu Button (Visible only when Developer Mode is enabled in Settings)
        self.debug_btn = QPushButton("Debug ▾")
        self.debug_btn.setObjectName("SecondaryBtn")
        self.debug_btn.setToolTip("Developer and Testing Tools")
        self.debug_btn.clicked.connect(self._on_debug_btn_clicked)
        top_bar.addWidget(self.debug_btn)

        # Publish Mod button
        self.publish_btn = QPushButton("Publish Mod/Pack")
        self.publish_btn.setToolTip("Package and publish your local mod or pack to the community")
        self.publish_btn.setObjectName("PrimaryBtn")
        self.publish_btn.clicked.connect(self._on_publish_clicked)
        top_bar.addWidget(self.publish_btn)

        content_layout.addLayout(top_bar)

        # --- Search and Filter Bar ---
        self.filter_bar = FilterBarWidget(self)
        self.filter_bar.filters_changed.connect(self._apply_filters)
        content_layout.addWidget(self.filter_bar)

        # --- Async Loading Indicator Bar ---
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setContentsMargins(0, 2, 0, 2); loading_layout.setSpacing(4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("IndeterminateBar")
        self.progress_bar.setRange(0, 0); self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        loading_layout.addWidget(self.progress_bar)

        self.loading_status_lbl = QLabel("Connecting to community catalog...")
        self.loading_status_lbl.setStyleSheet("font-size: 11px; color: #89b4fa; font-style: italic;")
        loading_layout.addWidget(self.loading_status_lbl)

        self.loading_widget.setVisible(False)
        content_layout.addWidget(self.loading_widget)


        # --- Scrollable Mod Cards Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 4, 0, 4); self.cards_layout.setSpacing(10)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state label
        self.empty_label = QLabel("No mods found matching your search criteria.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(
            "color: #6c7086; font-size: 13px; font-style: italic; margin-top: 40px;"
        )
        self.empty_label.setVisible(False)
        self.cards_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.cards_container)
        content_layout.addWidget(self.scroll_area, stretch=1)

        # --- Footer Status Bar ---
        footer_layout = QHBoxLayout()
        self.count_label = QLabel("Loading community catalog...")
        self.count_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        footer_layout.addWidget(self.count_label)
        footer_layout.addStretch()

        close_btn = QPushButton("Close"); close_btn.clicked.connect(self.close)
        footer_layout.addWidget(close_btn)

        content_layout.addLayout(footer_layout)
        main_layout.addWidget(content)

        # Resize grip
        self.grip = CustomSizeGrip(self); self.grip.setFixedSize(16, 16)

    def _update_auth_ui(self, user: Optional[UserProfile]) -> None:
        """Updates the top bar account badge according to the current session."""
        creator: str = self.auth.get_creator_name()
        if user is not None and not user.id.startswith("local_"):
            if user.is_developer:
                self.auth_btn.setText(f"★ {user.username} (Dev)")
                self.auth_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(203, 166, 247, 0.2);
                        color: #cba6f7;
                        border: 1px solid #cba6f7;
                        border-radius: 4px;
                        padding: 4px 10px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: rgba(203, 166, 247, 0.35);
                    }
                """)
            else:
                prov_icon = "✓ " if ("github" in user.providers or "google" in user.providers) else ""
                self.auth_btn.setText(f"{prov_icon}{user.username}")
                self.auth_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(59, 130, 246, 0.2);
                        color: #93c5fd;
                        border: 1px solid #3b82f6;
                        border-radius: 4px;
                        padding: 4px 10px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: rgba(59, 130, 246, 0.35);
                    }
                """)
        else:
            self.auth_btn.setText(f"{creator} (Profile)")
            self.auth_btn.setStyleSheet("""
                QPushButton {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45475a;
                }
            """)

    def _on_auth_btn_clicked(self) -> None:
        """Opens user account options menu or launches Profile settings."""
        user: Optional[UserProfile] = self.auth.current_user
        menu = QMenu(self)

        profile_action: QAction = menu.addAction("Creator Profile")
        menu.addSeparator()

        sign_in_action: Optional[QAction] = None
        sign_out_action: Optional[QAction] = None

        if user is not None and not user.id.startswith("local_"):
            info_action: QAction = menu.addAction(f"Logged in with {user.display_provider}")
            info_action.setEnabled(False)
            email_action: QAction = menu.addAction(f"Account: {user.email}")
            email_action.setEnabled(False)
            if user.github_username:
                gh_action: QAction = menu.addAction(f"GitHub: {user.github_username}")
                gh_action.setEnabled(False)
            if user.is_developer:
                dev_action: QAction = menu.addAction("Role: Core Developer ★")
                dev_action.setEnabled(False)
            menu.addSeparator()
            settings_action: QAction = menu.addAction("☁ Cloud Connection Settings")
            sign_out_action = menu.addAction("Sign Out")
        else:
            settings_action = menu.addAction("☁ Cloud Connection Settings")
            sign_in_action = menu.addAction("Sign In / Register (Cloud)")

        action: QAction = menu.exec(self.auth_btn.mapToGlobal(self.auth_btn.rect().bottomLeft()))
        if action == profile_action:
            settings_dlg = SettingsDialog(self)
            settings_dlg.open_profile_tab()
            settings_dlg.exec()
            self._update_auth_ui(self.auth.current_user)
        elif action == settings_action:
            dlg = AuthDialog(self)
            dlg.show_server_settings()
            dlg.exec()
        elif sign_out_action is not None and action == sign_out_action:
            self.auth.sign_out()
            self._update_auth_ui(None)
            QMessageBox.information(
                self, "Signed Out", "You have signed out of your cloud creator account."
            )
        elif sign_in_action is not None and action == sign_in_action:
            dlg = AuthDialog(self)
            dlg.exec()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.grip.move(
            self.width() - self.grip.width(),
            self.height() - self.grip.height()
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensures all background workers terminate safely when dialog is closed."""
        for worker in list(self._active_workers):
            if worker.isRunning():
                worker.quit()
                worker.wait(500)
        self._active_workers.clear()
        super().closeEvent(event)

    def _center_window(self) -> None:
        screen: QScreen = QGuiApplication.primaryScreen()
        if not screen: return
        screen_geom: QRect = screen.availableGeometry()
        window_geom: QRect = self.frameGeometry()
        window_geom.moveCenter(screen_geom.center())
        self.move(window_geom.topLeft())

    def _show_loading(self, text: str = "Loading...") -> None:
        """Displays the indeterminate loading progress bar and disables action buttons."""
        self.loading_status_lbl.setText(text)
        self.loading_widget.setVisible(True)
        self.refresh_btn.setEnabled(False)
        self.cloud_btn.setEnabled(False)

    def _hide_loading(self) -> None:
        """Hides the loading progress bar and re-enables action buttons."""
        self.loading_widget.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.cloud_btn.setEnabled(True)

    def _cleanup_worker(self, worker: QThread) -> None:
        """Safely removes finished worker from active workers registry."""
        if worker in self._active_workers:
            self._active_workers.remove(worker)

    def _update_status_indicator(self) -> None:
        """Updates the status badge and cloud toggle button to reflect online/offline mode."""
        if self.client.is_online and self.client.cloud.is_configured:
            self.status_badge.setText("● Cloud Sync Active")
            self.status_badge.setObjectName("StatusBadgeOnline")
            self.cloud_btn.setText("Work Offline"); self.cloud_btn.setObjectName("SecondaryBtn")
            self.cloud_btn.setToolTip("Disconnect from cloud and switch to local offline catalog")
        else:
            self.status_badge.setText("● Offline Catalog")
            self.status_badge.setObjectName("StatusBadgeOffline")
            self.cloud_btn.setText("Connect to Cloud"); self.cloud_btn.setObjectName("PrimaryBtn")
            self.cloud_btn.setToolTip("Connect to Supabase Cloud to view live community catalog")

        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.cloud_btn.style().unpolish(self.cloud_btn)
        self.cloud_btn.style().polish(self.cloud_btn)

    def _on_cloud_toggle_clicked(self) -> None:
        """Toggles between Supabase Cloud live catalog and local offline catalog mode."""
        if self.client.is_online:
            self.client.go_offline()
            self._update_status_indicator()
            self._apply_filters()
        else:
            if not self.client.cloud.is_configured:
                dlg = AuthDialog(self)
                dlg.show_server_settings()
                dlg.exec()
                if not self.client.cloud.is_configured:
                    return
            self._start_cloud_sync()

    def _start_cloud_sync(self) -> None:
        """Asynchronously syncs community catalog from Supabase via background worker."""
        self._show_loading("Connecting to Supabase Cloud and syncing catalog...")
        worker = CatalogSyncWorker(self.client, self)
        self._active_workers.append(worker)
        worker.sync_completed.connect(self._on_sync_completed)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.start()

    def _on_sync_completed(self, success: bool, message: str, count: int) -> None:
        """Callback invoked when catalog synchronization completes."""
        self._hide_loading()
        self._update_status_indicator()
        self._apply_filters()
        if not success:
            QMessageBox.warning(
                self,
                "Cloud Connection",
                f"Could not connect to Supabase Cloud:\n{message}\n\nRunning in offline catalog mode.",
            )

    def _refresh_catalog(self) -> None:
        """Refreshes catalog entries either from live cloud or local offline storage."""
        if self.client.is_online and self.client.cloud.is_configured:
            self._start_cloud_sync()
        else:
            self.client.go_offline()
            self._update_status_indicator()
            self._apply_filters()

    def _apply_filters(self) -> None:
        """Re-queries the client and updates the rendered card widgets."""
        query: str = self.filter_bar.query
        category: str = self.filter_bar.category
        sort_by: str = self.filter_bar.sort_by
        installed_only: bool = self.filter_bar.installed_only

        items: list[CommunityModItem] = self.client.fetch_mods(
            query=query,
            category=category,
            sort_by=sort_by,
            installed_only=installed_only,
        )

        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

        if not items:
            if self.settings_mgr.settings.enable_debug_mode:
                self.empty_label.setText(
                    "No mods found matching your search criteria.\n"
                    "(Developer Mode Active: Use 'Debug ▾' above to load sample mods)"
                )
            else:
                self.empty_label.setText("No mods found matching your search criteria.")
            self.empty_label.setVisible(True)
            self.count_label.setText("0 mods found")
            return

        self.empty_label.setVisible(False)
        for item in items:
            card = ModCardWidget(item)
            card.install_requested.connect(self._on_install_requested)
            card.uninstall_requested.connect(self._on_uninstall_requested)
            card.update_requested.connect(self._on_update_requested)
            card.inspect_requested.connect(self._on_inspect_requested)
            card.rate_requested.connect(self._on_rate_requested)
            card.publish_requested.connect(self._on_card_publish_requested)

            self.cards_layout.addWidget(card)
            self._cards.append(card)

        installed_count: int = sum(1 for item in items if item.is_installed)
        self.count_label.setText(f"Showing {len(items)} mods ({installed_count} installed)")

    def _on_card_publish_requested(self, item: CommunityModItem) -> None:
        """Opens publish dialog with this specific local mod/modpack preselected."""
        print(f"Attempting to publish mod: {item.id}")
        publish_dlg = PublishModDialog(self.mod_manager, self.client, self, selected_mod_id=item.id)
        if publish_dlg.exec() == QDialog.DialogCode.Accepted:
            self._apply_filters()

    def _on_install_requested(self, item: CommunityModItem) -> None:
        """Asynchronously installs a community mod or modpack package."""
        self._show_loading(f"Downloading and installing '{item.name}'...")
        worker = ModInstallWorker(self.client, item, action="install", parent=self)
        self._active_workers.append(worker)
        worker.install_completed.connect(self._on_install_completed)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.start()

    def _on_update_requested(self, item: CommunityModItem) -> None:
        """Asynchronously updates an installed mod or modpack to the latest catalog release."""
        self._show_loading(f"Updating '{item.name}' to version {item.version}...")
        worker = ModInstallWorker(self.client, item, action="update", parent=self)
        self._active_workers.append(worker)
        worker.install_completed.connect(self._on_install_completed)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.start()

    def _on_install_completed(self, success: bool, message: str, item: CommunityModItem) -> None:
        """Callback invoked when background download/install/update finishes."""
        self._hide_loading()
        if success:
            QMessageBox.information(self, "Installation Complete", message)
            self._apply_filters()
            self.mods_updated.emit()
        else:
            QMessageBox.critical(self, "Installation Error", message)

    def _on_uninstall_requested(self, item: CommunityModItem) -> None:
        """Prompts and removes an installed mod or modpack."""
        confirm: QMessageBox.StandardButton = QMessageBox.question(
            self,
            "Confirm Uninstall",
            (
                f"Are you sure you want to uninstall '{item.name}'?\n"
                "This will remove its local files from your mods directory."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        success, message = self.client.uninstall_mod(item)
        if success:
            QMessageBox.information(self, "Uninstalled", message)
            self._apply_filters()
            self.mods_updated.emit()
        else:
            QMessageBox.critical(self, "Uninstall Error", message)

    def _on_inspect_requested(self, item: CommunityModItem) -> None:
        """Inspects package file structure, source code, and AST safety audit."""
        target_dir: Path = self.mod_manager.mods_dir / item.id
        if target_dir.exists():
            dialog = ModInspectorDialog(target_dir, self)
            dialog.exec()
            return
        with tempfile.TemporaryDirectory() as temp_dir:
            preview_dir: Path = Path(temp_dir) / item.id
            preview_dir.mkdir(parents=True, exist_ok=True)

            if item.is_pack:
                (preview_dir / "pack.json").write_text(
                    json.dumps({
                        "id": item.id,
                        "name": item.name,
                        "version": item.version,
                        "author": item.author,
                        "description": item.description,
                    }, indent=2),
                    encoding="utf-8",
                )
                (preview_dir / "pack.py").write_text(
                    f'"""Shared controller for {item.name}."""\n'
                    "from pytoningans.core.api import BaseModPack, PackMenuAction\n\n"
                    "class PackController(BaseModPack):\n"
                    "    def on_pack_loaded(self) -> None:\n"
                    "        pass\n",
                    encoding="utf-8",
                )
                for entity_name in item.contained_entities:
                    slug: str = entity_name.lower().replace(" ", "_")
                    entity_path: Path = preview_dir / "entities" / slug
                    entity_path.mkdir(parents=True, exist_ok=True)
                    (entity_path / "config.json").write_text(
                        json.dumps({
                            "name": entity_name,
                            "entity_type": EntityType.ENTITY.value,
                            "version": CURRENT_CONFIG_VERSION,
                        }, indent=2),
                        encoding="utf-8",
                    )
                    self.client._create_placeholder_sprite(entity_path / "sprite_sheet.png")
            else:
                (preview_dir / "config.json").write_text(
                    json.dumps({
                        "name": item.name,
                        "entity_type": item.entity_type,
                        "version": CURRENT_CONFIG_VERSION,
                    }, indent=2),
                    encoding="utf-8",
                )
                self.client._create_placeholder_sprite(preview_dir / "sprite_sheet.png")

            dialog = ModInspectorDialog(preview_dir, self)
            dialog.exec()

    def _on_rate_requested(self, item: CommunityModItem) -> None:
        """Opens rating dialog to submit a score."""
        rating_dlg = RatingDialog(item, self)
        if rating_dlg.exec() == QDialog.DialogCode.Accepted:
            score = float(rating_dlg.selected_rating)
            success, msg = self.client.rate_mod(item.id, score)
            if success:
                QMessageBox.information(self, "Rating Submitted", msg)
                self._apply_filters()
            else:
                QMessageBox.warning(self, "Rating Failed", msg)

    def _on_publish_clicked(self) -> None:
        """Opens the publish mod dialog, requiring creator account authentication."""
        if not self.auth.is_authenticated:
            auth_dlg = AuthDialog(self)
            if auth_dlg.exec() != QDialog.DialogCode.Accepted:
                return

        publish_dlg = PublishModDialog(self.mod_manager, self.client, self)
        if publish_dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_catalog()
            self.mods_updated.emit()

    def _update_debug_visibility(self) -> None:
        """Toggles visibility of the debug tools menu based on developer settings."""
        self.debug_btn.setVisible(self.settings_mgr.settings.enable_debug_mode)
        if not self._cards:
            self._apply_filters()

    def _on_debug_btn_clicked(self) -> None:
        """Opens developer and testing tools popup menu."""
        menu = QMenu(self)
        title_action = menu.addAction("Developer and Testing Tools")
        title_action.setEnabled(False)
        menu.addSeparator()

        seed_action = menu.addAction("Load Demo / Seed Catalog")
        seed_action.setToolTip("Inject built-in demo mods into the catalog cache for offline testing")

        clear_cache_action = menu.addAction("Clear Local Catalog Cache")
        clear_cache_action.setToolTip("Wipe cached community items to test empty catalog state")

        menu.addSeparator()
        settings_action = menu.addAction("Configure Developer Settings...")

        action = menu.exec(self.debug_btn.mapToGlobal(self.debug_btn.rect().bottomLeft()))
        if action == seed_action:
            added = self.client.load_seed_catalog()
            self._apply_filters()
            QMessageBox.information(
                self, "Demo Catalog Loaded", f"Injected {added} demo mods into your local catalog."
            )
        elif action == clear_cache_action:
            self.client.clear_catalog_cache()
            self._apply_filters()
            QMessageBox.information(
                self, "Cache Cleared", "Local community catalog cache has been reset."
            )
        elif action == settings_action:
            dlg = SettingsDialog(self)
            dlg.tabs.setCurrentIndex(SettingsTab.DeveloperAndDebugging)
            dlg.exec()

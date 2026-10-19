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
from typing import Optional

from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QGuiApplication, QScreen, QResizeEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QWidget, QMessageBox, QFrame, QMenu
)

from pytoningans.core.mod_manager import ModManager
from pytoningans.core.config_schema import CURRENT_CONFIG_VERSION
from pytoningans.core.constants import EntityType
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.mod_editor.components import CustomSizeGrip
from pytoningans.ui.mod_inspector import ModInspectorDialog
from pytoningans.utils.assets import get_main_icon

from .auth import AuthManager, UserProfile
from .client import ModBrowserClient
from .models import CommunityModItem
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

        self.setWindowTitle("Community Mod Browser")
        self.setWindowIcon(get_main_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(940, 700); self.setMinimumSize(800, 540)

        self._cards: list[ModCardWidget] = []
        self._setup_ui()
        self.auth.auth_state_changed.connect(self._update_auth_ui)
        self._update_auth_ui(self.auth.current_user)
        self._refresh_catalog()
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

        # Online Status Indicator
        if self.auth.is_cloud_configured:
            self.status_badge = QLabel("● Cloud Sync Active")
            self.status_badge.setStyleSheet(
                "color: #10b981; font-weight: bold; font-size: 11px; "
                "background-color: rgba(16, 185, 129, 0.15); border-radius: 4px; padding: 4px 8px;"
            )
        else:
            self.status_badge = QLabel("● Offline Catalog")
            self.status_badge.setStyleSheet(
                "color: #38bdf8; font-weight: bold; font-size: 11px; "
                "background-color: rgba(56, 189, 248, 0.15); border-radius: 4px; padding: 4px 8px;"
            )
        top_bar.addWidget(self.status_badge)

        top_bar.addStretch()

        # Creator Account / Sign-in Pill Button
        self.auth_btn = QPushButton("Sign In / Register")
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
        self.auth_btn.clicked.connect(self._on_auth_btn_clicked)
        top_bar.addWidget(self.auth_btn)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Reload community catalog")
        self.refresh_btn.clicked.connect(self._refresh_catalog)
        top_bar.addWidget(self.refresh_btn)

        # Publish Mod button
        self.publish_btn = QPushButton("Publish Mod/Pack")
        self.publish_btn.setToolTip("Package and publish your local mod or pack to the community")
        self.publish_btn.setStyleSheet(
            "background-color: #3b82f6; color: white; font-weight: bold; padding: 4px 12px;"
        )
        self.publish_btn.clicked.connect(self._on_publish_clicked)
        top_bar.addWidget(self.publish_btn)

        content_layout.addLayout(top_bar)

        # --- Search and Filter Bar ---
        self.filter_bar = FilterBarWidget(self)
        self.filter_bar.filters_changed.connect(self._apply_filters)
        content_layout.addWidget(self.filter_bar)

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
        self.empty_label.setStyleSheet("color: #6c7086; font-size: 13px; font-style: italic; margin-top: 40px;")
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
        if user is not None:
            self.auth_btn.setText(f"@{user.username}")
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
            self.auth_btn.setText("Sign In / Register")
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
        """Opens user account options menu or launches AuthDialog."""
        user = self.auth.current_user
        if user is not None:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #1e1e2e;
                    color: #cdd6f4;
                    border: 1px solid #313244;
                    border-radius: 6px;
                    padding: 4px;
                }
                QMenu::item:selected {
                    background-color: #313244;
                }
            """)
            info_action = menu.addAction(f"Signed in as @{user.username} ({user.email})")
            info_action.setEnabled(False)
            menu.addSeparator()

            settings_action = menu.addAction("Cloud Connection Settings")
            sign_out_action = menu.addAction("Sign Out")

            action = menu.exec(self.auth_btn.mapToGlobal(self.auth_btn.rect().bottomLeft()))
            if action == settings_action:
                dlg = AuthDialog(self)
                dlg.tabs.setCurrentIndex(2)  # Open Cloud Settings tab
                dlg.exec()
            elif action == sign_out_action:
                self.auth.sign_out()
                QMessageBox.information(
                    self, "Signed Out", "You have signed out of your creator account."
                )
        else:
            dlg = AuthDialog(self)
            dlg.exec()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.grip.move(
            self.width() - self.grip.width(),
            self.height() - self.grip.height()
        )

    def _center_window(self) -> None:
        screen: QScreen = QGuiApplication.primaryScreen()
        if not screen: return
        screen_geom: QRect = screen.availableGeometry()
        window_geom: QRect = self.frameGeometry()
        window_geom.moveCenter(screen_geom.center())
        self.move(window_geom.topLeft())

    def _refresh_catalog(self) -> None:
        """Fetches items and refreshes the card list according to active filters."""
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

            self.cards_layout.addWidget(card)
            self._cards.append(card)

        installed_count: int = sum(1 for item in items if item.is_installed)
        self.count_label.setText(f"Showing {len(items)} mods ({installed_count} installed)")

    def _on_install_requested(self, item: CommunityModItem) -> None:
        """Installs a community mod or modpack package."""
        success, message = self.client.install_mod(item)
        if success:
            QMessageBox.information(self, "Installation Complete", message)
            self._apply_filters()
            self.mods_updated.emit()
        else:
            QMessageBox.critical(self, "Installation Error", message)

    def _on_update_requested(self, item: CommunityModItem) -> None:
        """Updates an installed mod or modpack to the latest catalog release."""
        success, message = self.client.update_mod(item)
        if success:
            QMessageBox.information(self, "Update Complete", message)
            self._apply_filters()
            self.mods_updated.emit()
        else:
            QMessageBox.critical(self, "Update Error", message)

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
        else:
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

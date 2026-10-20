"""
PyToNingans Mod Browser - Publish Modpack Dialog
================================================
Guides modders through publishing their locally created mods and modpacks,
including automatic AST security verification, manifest packaging, version bumping,
release notes (git-like releases), and authenticated cloud staging.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Any, TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QTextEdit, QPushButton, QMessageBox, QWidget, QFrame
)

from pytoningans.core.constants import EntityType
from pytoningans.core.mod_manager import (
    ModManager, resolve_mod_path, export_mod_or_pack_to_zip, scan_mod_or_pack,
    SecurityRiskLevel, SecurityReport,
)
from pytoningans.core.mod_manager.modpack import ModPack
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.utils.assets import get_main_icon
from ..auth import AuthManager
from ..models import CommunityModItem, parse_semver
from .auth_dialog import AuthDialog

if TYPE_CHECKING:
    from pytoningans.ui.mod_browser.auth import UserProfile


class PublishModDialog(QDialog):
    """Modal dialog allowing users to package and publish a local mod/pack to the community."""

    def __init__(
        self,
        mod_manager: ModManager,
        client: Optional[Any] = None,
        parent: Optional[QWidget] = None,
        selected_mod_id: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self.mod_manager: ModManager = mod_manager
        self.client: Optional[Any] = client
        self.auth: AuthManager = AuthManager.get()
        self.published_package_path: Optional[Path] = None
        self.selected_mod_id: Optional[str] = selected_mod_id

        self.setWindowTitle("Publish Mod or Modpack")
        self.setWindowIcon(get_main_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(540, 560)

        # Check authentication first
        if not self.auth.is_authenticated:
            auth_dlg = AuthDialog(self)
            auth_dlg.exec()

        self._setup_ui()
        self._populate_mods_dropdown()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, "Publish to Community Mod Browser")
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(10)

        # Creator Account Banner
        author_name: str = self.auth.get_creator_name()
        if self.auth.is_authenticated:
            user_banner = QLabel(f"Publishing as verified creator: <b>{author_name}</b>")
        else:
            user_banner = QLabel(f"Publishing as creator: <b>{author_name}</b> (Offline / Local Mode)")
        user_banner.setObjectName("UserBanner")
        layout.addWidget(user_banner)

        # Mode Indicator Banner (New vs Update)
        self.mode_banner = QLabel("Publishing Mode: New Mod")
        self.mode_banner.setObjectName("ModeBanner")
        layout.addWidget(self.mode_banner)

        # Target Mod Selector
        layout.addWidget(QLabel("Select Local Mod or Pack to Publish:"))
        self.mod_combo = QComboBox()
        self.mod_combo.currentIndexChanged.connect(self._on_target_changed)
        layout.addWidget(self.mod_combo)

        # Creator Handle (Read-only bound to account)
        layout.addWidget(QLabel("Creator Handle:"))
        self.author_input = QLineEdit(author_name)
        self.author_input.setReadOnly(True)
        self.author_input.setStyleSheet("background-color: #2b2b3b; color: #a6adc8;")
        layout.addWidget(self.author_input)

        # Version
        ver_layout = QHBoxLayout()
        ver_layout.addWidget(QLabel("Release Version:"))
        self.ver_hint_label = QLabel("(Must be higher than current)")
        self.ver_hint_label.setStyleSheet("color: #a6adc8; font-size: 10px; font-style: italic;")
        ver_layout.addWidget(self.ver_hint_label)
        ver_layout.addStretch()
        layout.addLayout(ver_layout)

        self.version_input = QLineEdit("1.0.0")
        layout.addWidget(self.version_input)

        # Changelog / Release Notes
        layout.addWidget(QLabel("Release Notes / Changelog:"))
        self.changelog_input = QTextEdit()
        self.changelog_input.setPlaceholderText(
            "What's new in this release? (e.g. Added idle dance animation, fixed collision hitbox)..."
        )
        self.changelog_input.setMaximumHeight(65)
        layout.addWidget(self.changelog_input)

        # Short Description
        layout.addWidget(QLabel("Description and Highlights:"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText(
            "Describe your entity behavior, items, and animations..."
        )
        self.desc_input.setMaximumHeight(65)
        layout.addWidget(self.desc_input)

        # Security Pre-flight Status Frame
        self.security_frame = QFrame()
        self.security_frame.setFrameShape(QFrame.Shape.StyledPanel)
        sec_layout = QVBoxLayout(self.security_frame)
        sec_layout.setContentsMargins(10, 8, 10, 8)

        self.security_status_label = QLabel("Security Status: Ready to audit.")
        self.security_status_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        sec_layout.addWidget(self.security_status_label)
        layout.addWidget(self.security_frame)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.publish_btn = QPushButton("Package and Publish")
        self.publish_btn.setObjectName("SuccessBtn")
        self.publish_btn.clicked.connect(self._on_publish_clicked)
        btn_layout.addWidget(self.publish_btn)


        layout.addLayout(btn_layout)
        main_layout.addWidget(content)

    def _populate_mods_dropdown(self) -> None:
        self.mod_combo.clear()
        mods: dict[str, tuple[str, str]] = self.mod_manager.get_available_mods_with_type()
        packs: dict[str, ModPack] = self.mod_manager.get_available_packs()

        # First add packs
        for pack_id, pack in packs.items():
            self.mod_combo.addItem(f"[PACK] {pack.name}", userData=pack_id)

        # Then standalone mods
        for mod_id, (name, ent_type) in mods.items():
            if ":" not in mod_id:
                self.mod_combo.addItem(f"[{ent_type.capitalize()}] {name}", userData=mod_id)

        if self.mod_combo.count() == 0:
            self.mod_combo.addItem("No local mods found in mods folder", userData=None)
            self.publish_btn.setEnabled(False)
        else:
            if self.selected_mod_id is not None:
                for idx in range(self.mod_combo.count()):
                    if self.mod_combo.itemData(idx) == self.selected_mod_id:
                        self.mod_combo.setCurrentIndex(idx)
                        break
            self._on_target_changed()

    def _on_target_changed(self) -> None:
        target_id: Optional[str] = self.mod_combo.currentData()
        if not target_id:
            return

        resolved, pack_id, _ = resolve_mod_path(self.mod_manager.mods_dir, target_id)
        target_dir: Optional[Path] = (self.mod_manager.mods_dir / pack_id) if pack_id else resolved

        # Check if already published in catalog
        existing_item: Optional[CommunityModItem] = None
        if self.client is not None:
            existing_item = self.client.get_mod_by_id(target_id)

        if existing_item is not None:
            self.mode_banner.setText(
                f"Release Update Mode: Publishing new release for existing catalog item '{existing_item.name}'"
            )
            self.mode_banner.setObjectName("ModeBannerActive")
            self.desc_input.setPlainText(existing_item.description)

            # Suggest version bump (e.g. 1.0.0 -> 1.0.1)
            old_semver = parse_semver(existing_item.version)
            suggested_ver = f"{old_semver[0]}.{old_semver[1]}.{old_semver[2] + 1}"
            self.version_input.setText(suggested_ver)
            self.ver_hint_label.setText(f"(Current catalog version: v{existing_item.version})")
            self.publish_btn.setText(f"Publish Release Update (v{suggested_ver})")
            self.publish_btn.setObjectName("InfoBtn")
        else:
            self.mode_banner.setText("Publishing Mode: New Mod Listing")
            self.mode_banner.setObjectName("ModeBanner")
            self.version_input.setText("1.0.0")
            self.ver_hint_label.setText("(Initial release)")
            self.publish_btn.setText("Package and Publish")
            self.publish_btn.setObjectName("SuccessBtn")

        self.mode_banner.style().unpolish(self.mode_banner)
        self.mode_banner.style().polish(self.mode_banner)
        self.publish_btn.style().unpolish(self.publish_btn)
        self.publish_btn.style().polish(self.publish_btn)

        if target_dir and target_dir.exists():
            report: SecurityReport = scan_mod_or_pack(target_dir)
            if report.risk_level == SecurityRiskLevel.DANGEROUS:
                self.security_frame.setObjectName("SecurityDangerous")
                self.security_status_label.setText(
                    "Prohibited: Dangerous operations detected (network or process execution). Cannot publish."
                )
                self.security_status_label.setObjectName("BadgeDanger")
                self.publish_btn.setEnabled(False)
            elif report.risk_level == SecurityRiskLevel.MEDIUM:
                self.security_frame.setObjectName("SecurityWarning")
                self.security_status_label.setText(
                    "Warning: File write operations detected. Proceed with caution."
                )
                self.security_status_label.setObjectName("BadgeWarning")
                self.publish_btn.setEnabled(True)
            else:
                self.security_frame.setObjectName("SecurityClean")
                self.security_status_label.setText(
                    "Security Verified: Clean AST scan. Approved for community publication."
                )
                self.security_status_label.setObjectName("BadgeSuccess")
                self.publish_btn.setEnabled(True)

            self.security_frame.style().unpolish(self.security_frame)
            self.security_frame.style().polish(self.security_frame)
            self.security_status_label.style().unpolish(self.security_status_label)
            self.security_status_label.style().polish(self.security_status_label)


    def _on_publish_clicked(self) -> None:
        target_id: Optional[str] = self.mod_combo.currentData()
        if target_id is None or not target_id:
            return

        author: str = self.author_input.text().strip() or "Modder"
        version_str: str = self.version_input.text().strip() or "1.0.0"
        desc: str = self.desc_input.toPlainText().strip()
        changelog: str = self.changelog_input.toPlainText().strip()

        resolved, pack_id, _ = resolve_mod_path(self.mod_manager.mods_dir, target_id)
        target_dir: Optional[Path] = (self.mod_manager.mods_dir / pack_id) if pack_id else resolved
        if not target_dir or not target_dir.exists():
            QMessageBox.critical(self, "Error", "Target directory does not exist.")
            return

        is_pack: bool = (target_dir / "pack.json").exists()
        entity_name: str = target_dir.name
        entity_type: str = "pack" if is_pack else EntityType.ENTITY
        contained_entities: list[str] = []

        if is_pack:
            try:
                p_data = json.loads((target_dir / "pack.json").read_text(encoding="utf-8"))
                entity_name = p_data.get("name", entity_name)
                for sub in p_data.get("sub_mods", []):
                    sub_cfg = target_dir / sub / "config.json"
                    if sub_cfg.exists():
                        sub_data = json.loads(sub_cfg.read_text(encoding="utf-8"))
                        contained_entities.append(sub_data.get("name", Path(sub).name))
            except Exception:
                pass
        else:
            cfg_path = target_dir / "config.json"
            if cfg_path.exists():
                try:
                    c_data = json.loads(cfg_path.read_text(encoding="utf-8"))
                    entity_name = c_data.get("name", entity_name)
                    entity_type = c_data.get("entity_type", EntityType.ENTITY)
                except Exception:
                    pass

        import tempfile
        staging_dir: Path = Path(tempfile.gettempdir()) / "pytoningans_publish"
        staging_dir.mkdir(parents=True, exist_ok=True)
        zip_path: Path = staging_dir / f"{target_dir.name}_v{version_str}.zip"

        success, msg, out_path = export_mod_or_pack_to_zip(target_dir, zip_path)
        if not success or out_path is None:
            QMessageBox.critical(self, "Export Failed", f"Failed to prepare package: {msg}")
            return

        self.published_package_path = out_path
        size_bytes: int = out_path.stat().st_size

        if self.client is not None:
            pub_ok, pub_msg, _ = self.client.publish_or_update(
                mod_id=target_id,
                name=entity_name,
                author=author,
                version=version_str,
                description=desc or f"{entity_name} created by {author}",
                entity_type=entity_type,
                is_pack=is_pack,
                tags=["pack", "community"] if is_pack else ["custom", entity_type],
                changelog=changelog,
                contained_entities=contained_entities,
                size_bytes=size_bytes,
                zip_path=out_path,
            )
            if not pub_ok:
                QMessageBox.warning(self, "Publication Conflict", pub_msg)
                return

            QMessageBox.information(
                self,
                "Publication Success",
                f"{pub_msg}\n\nPackage archive prepared ({size_bytes} bytes)."
            )
        else:
            QMessageBox.information(
                self,
                "Package Prepared",
                f"Successfully prepared package archive for '{entity_name}' ({size_bytes} bytes)."
            )

        self.accept()

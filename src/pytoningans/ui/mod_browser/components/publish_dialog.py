"""
PyToNingans Mod Browser - Publish Modpack Dialog
================================================
Guides modders through publishing their locally created mods and modpacks,
including automatic AST security verification, manifest packaging, and cloud staging.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QTextEdit, QPushButton, QMessageBox, QWidget, QFrame
)

from pytoningans.core.mod_manager import (
    ModManager, resolve_mod_path, export_mod_or_pack_to_zip, scan_mod_or_pack,
    SecurityRiskLevel, SecurityReport,
)
from pytoningans.core.mod_manager.modpack import ModPack
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.utils.assets import get_main_icon


class PublishModDialog(QDialog):
    """Modal dialog allowing users to package and publish a local mod/pack to the community."""

    def __init__(self, mod_manager: ModManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.mod_manager: ModManager = mod_manager
        self.published_package_path: Optional[Path] = None

        self.setWindowTitle("Publish Mod or Modpack")
        self.setWindowIcon(get_main_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(540, 480)

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

        # Target Mod Selector
        layout.addWidget(QLabel("Select Local Mod or Pack to Publish:"))
        self.mod_combo = QComboBox()
        self.mod_combo.currentIndexChanged.connect(self._on_target_changed)
        layout.addWidget(self.mod_combo)

        # Author Handle
        layout.addWidget(QLabel("Author / Creator Handle:"))
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("e.g. YourUsername")
        layout.addWidget(self.author_input)

        # Version
        layout.addWidget(QLabel("Release Version:"))
        self.version_input = QLineEdit("1.0.0")
        layout.addWidget(self.version_input)

        # Short Description
        layout.addWidget(QLabel("Description and Highlights:"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText(
            "Describe your entity behavior, items, and animations..."
        )
        self.desc_input.setMaximumHeight(80)
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
        self.publish_btn.setStyleSheet(
            "background-color: #10b981; color: white; font-weight: bold; padding: 6px 14px;"
        )
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
            self._on_target_changed()

    def _on_target_changed(self) -> None:
        target_id: Optional[str] = self.mod_combo.currentData()
        if not target_id:
            return

        resolved, pack_id, _ = resolve_mod_path(self.mod_manager.mods_dir, target_id)
        target_dir: Optional[Path] = (self.mod_manager.mods_dir / pack_id) if pack_id else resolved

        if target_dir and target_dir.exists():
            report: SecurityReport = scan_mod_or_pack(target_dir)
            if report.risk_level == SecurityRiskLevel.DANGEROUS:
                self.security_frame.setStyleSheet(
                    "background-color: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; border-radius: 4px;"
                )
                self.security_status_label.setText(
                    "Prohibited: Dangerous operations detected (network or process execution). Cannot publish."
                )
                self.security_status_label.setStyleSheet("color: #f87171; font-weight: bold;")
                self.publish_btn.setEnabled(False)
            elif report.risk_level == SecurityRiskLevel.MEDIUM:
                self.security_frame.setStyleSheet(
                    "background-color: rgba(245, 158, 11, 0.2); border: 1px solid #f59e0b; border-radius: 4px;"
                )
                self.security_status_label.setText(
                    "Warning: File write operations detected. Proceed with caution."
                )
                self.security_status_label.setStyleSheet("color: #fbbf24; font-weight: bold;")
                self.publish_btn.setEnabled(True)
            else:
                self.security_frame.setStyleSheet(
                    "background-color: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; border-radius: 4px;"
                )
                self.security_status_label.setText(
                    "Security Verified: Clean AST scan. Approved for community publication."
                )
                self.security_status_label.setStyleSheet("color: #34d399; font-weight: bold;")
                self.publish_btn.setEnabled(True)

    def _on_publish_clicked(self) -> None:
        target_id: Optional[str] = self.mod_combo.currentData()
        if target_id is None or not target_id:
            return

        author: str = self.author_input.text().strip()
        if not author:
            QMessageBox.warning(self, "Author Required", "Please enter your creator username/handle.")
            return

        resolved, pack_id, _ = resolve_mod_path(self.mod_manager.mods_dir, target_id)
        target_dir: Optional[Path] = (self.mod_manager.mods_dir / pack_id) if pack_id else resolved
        if not target_dir or not target_dir.exists():
            QMessageBox.critical(self, "Error", "Target directory does not exist.")
            return

        import tempfile
        staging_dir: Path = Path(tempfile.gettempdir()) / "pytoningans_publish"
        staging_dir.mkdir(parents=True, exist_ok=True)
        zip_path: Path = staging_dir / f"{target_dir.name}_v{self.version_input.text().strip() or '1.0.0'}.zip"

        success, msg, out_path = export_mod_or_pack_to_zip(target_dir, zip_path)
        if success:
            self.published_package_path = out_path
            QMessageBox.information(
                self,
                "Package Prepared",
                f"Successfully validated and packaged '{target_dir.name}' ({zip_path.stat().st_size} bytes).\n\n"
                "Package is ready for cloud upload!"
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Export Failed", f"Failed to prepare package: {msg}")


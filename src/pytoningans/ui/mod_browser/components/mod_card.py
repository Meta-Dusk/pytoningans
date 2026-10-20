"""
PyToNingans Mod Browser - Mod Card Component
============================================
Visual card widget rendering community mod details, ratings, download stats,
tags, outdated badges, update buttons, and one-click actions.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QMessageBox
)

from pytoningans.core.constants import EntityType
from ..models import CommunityModItem


class ModCardWidget(QFrame):
    """Card widget representing an individual community mod or modpack listing."""

    install_requested = Signal(object)    # CommunityModItem
    uninstall_requested = Signal(object)  # CommunityModItem
    update_requested = Signal(object)     # CommunityModItem
    inspect_requested = Signal(object)    # CommunityModItem
    rate_requested = Signal(object)       # CommunityModItem

    def __init__(self, item: CommunityModItem, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.item: CommunityModItem = item
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("ModCardWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(8)

        # --- Top Header: Type Badge, Name, Outdated Indicator, Installed status ---
        header_layout = QHBoxLayout(); header_layout.setSpacing(8)

        # Type badge
        type_text: str = "PACK" if self.item.is_pack else self.item.entity_type.upper()
        type_badge = QLabel(f" {type_text} ")
        if self.item.is_pack:
            type_badge.setObjectName("BadgePack")
        elif self.item.entity_type == EntityType.STRUCTURE:
            type_badge.setObjectName("BadgeStructure")
        elif self.item.entity_type == EntityType.ITEM:
            type_badge.setObjectName("BadgeItem")
        else:
            type_badge.setObjectName("BadgeEntity")
        header_layout.addWidget(type_badge)

        # Mod Name
        name_label = QLabel(self.item.name)
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #cdd6f4;")
        header_layout.addWidget(name_label, stretch=1)

        # Outdated warning badge
        if self.item.is_outdated:
            reasons_text = "\n• ".join(self.item.outdated_reasons)
            outdated_badge = QLabel("Outdated")
            outdated_badge.setToolTip(f"Outdated Compatibility Warning:\n• {reasons_text}")
            outdated_badge.setObjectName("BadgeWarning")
            header_layout.addWidget(outdated_badge)

        # Installation / Update Status Badges
        if self.item.is_installed:
            if self.item.has_update:
                update_badge = QLabel(f"↑ Update Available (v{self.item.version})")
                update_badge.setToolTip(
                    f"Installed: v{self.item.installed_version} → Latest: v{self.item.version}"
                )
                update_badge.setObjectName("BadgeInfo")
                header_layout.addWidget(update_badge)
            else:
                ver_display = self.item.installed_version or self.item.version
                installed_badge = QLabel(f"✓ Installed (v{ver_display})")
                installed_badge.setObjectName("BadgeSuccess")
                header_layout.addWidget(installed_badge)

        layout.addLayout(header_layout)

        # --- Sub-Header: Author and Version ---
        meta_label = QLabel(
            f"by {self.item.author} • v{self.item.version} • {self.item.formatted_size}"
        )
        meta_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(meta_label)

        # --- Description ---
        desc_label = QLabel(self.item.description); desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #bac2de; font-size: 12px; margin-top: 2px; margin-bottom: 2px;")
        layout.addWidget(desc_label)

        # If modpack, display contained entities pill list
        if self.item.is_pack and self.item.contained_entities:
            pack_contents_lbl = QLabel(f"Includes: {', '.join(self.item.contained_entities)}")
            pack_contents_lbl.setStyleSheet("color: #89dceb; font-size: 11px; font-style: italic;")
            layout.addWidget(pack_contents_lbl)

        # --- Tags row ---
        if self.item.tags:
            tags_layout = QHBoxLayout(); tags_layout.setSpacing(4)
            for tag in self.item.tags[:4]:
                chip = QLabel(f"#{tag}")
                chip.setStyleSheet("color: #6c7086; font-size: 11px;")
                tags_layout.addWidget(chip)
            tags_layout.addStretch()
            layout.addLayout(tags_layout)

        # --- Stats and Actions Footer ---
        footer_layout = QHBoxLayout(); footer_layout.setSpacing(10)

        # Rating display
        rating_lbl = QLabel(self.item.formatted_rating)
        rating_lbl.setStyleSheet("color: #f9e2af; font-weight: bold; font-size: 12px;")
        footer_layout.addWidget(rating_lbl)

        # Downloads display
        dl_lbl = QLabel(f"↓ {self.item.downloads}")
        dl_lbl.setStyleSheet("color: #a6adc8; font-size: 12px;")
        footer_layout.addWidget(dl_lbl)

        footer_layout.addStretch()

        # Action: Changelog button if multiple releases or changelog available
        if self.item.releases:
            changelog_btn = QPushButton("Changelog")
            changelog_btn.setToolTip("View version history and release notes")
            changelog_btn.setStyleSheet("padding: 4px 8px; font-size: 11px; color: #a6adc8;")
            changelog_btn.clicked.connect(self._show_changelog)
            footer_layout.addWidget(changelog_btn)

        # Action 1: Rate button
        rate_btn = QPushButton("Rate")
        rate_btn.setToolTip(f"Submit a rating (1-10) for {self.item.name}")
        rate_btn.setStyleSheet("padding: 4px 8px; font-size: 11px;")
        rate_btn.clicked.connect(lambda: self.rate_requested.emit(self.item))
        footer_layout.addWidget(rate_btn)

        # Action 2: Inspect and Safety button
        inspect_btn = QPushButton("Inspect")
        inspect_btn.setToolTip("View files, source code, and run AST security audit")
        inspect_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        inspect_btn.clicked.connect(lambda: self.inspect_requested.emit(self.item))
        footer_layout.addWidget(inspect_btn)

        # Action 3: Install / Update / Uninstall buttons
        if self.item.is_installed:
            if self.item.has_update:
                update_btn = QPushButton(f"Update (v{self.item.version})")
                update_btn.setToolTip(f"Upgrade to version {self.item.version}")
                update_btn.setObjectName("InfoBtn")
                update_btn.clicked.connect(lambda: self.update_requested.emit(self.item))
                footer_layout.addWidget(update_btn)

            uninstall_btn = QPushButton("Uninstall")
            uninstall_btn.setObjectName("DangerBtn")
            uninstall_btn.clicked.connect(lambda: self.uninstall_requested.emit(self.item))
            footer_layout.addWidget(uninstall_btn)
        else:
            install_btn = QPushButton("Install")
            install_btn.setObjectName("SuccessBtn")
            install_btn.clicked.connect(lambda: self.install_requested.emit(self.item))
            footer_layout.addWidget(install_btn)


        layout.addLayout(footer_layout)

    def _show_changelog(self) -> None:
        """Displays release notes in an information dialog."""
        lines: list[str] = [f"<b>Release History for {self.item.name}</b><br>"]
        for r in self.item.releases:
            lines.append(f"<b>Version {r.version}</b> ({r.created_at}):<br>• {r.changelog}<br>")
        QMessageBox.information(self, f"{self.item.name} - Changelog", "<br>".join(lines))

"""
PyToNingans Mod Browser - Mod Card Component
============================================
Visual card widget rendering community mod details, ratings, download stats,
tags, and one-click actions (Inspect, Install/Uninstall, Rate).
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)

from pytoningans.core.constants import EntityType
from ..models import CommunityModItem


class ModCardWidget(QFrame):
    """Card widget representing an individual community mod or modpack listing."""

    install_requested = Signal(object)    # CommunityModItem
    uninstall_requested = Signal(object)  # CommunityModItem
    inspect_requested = Signal(object)    # CommunityModItem
    rate_requested = Signal(object)       # CommunityModItem

    def __init__(self, item: CommunityModItem, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.item: CommunityModItem = item
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            ModCardWidget {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 4px;
            }
            ModCardWidget:hover {
                border: 1px solid #585b70;
                background-color: #24253a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # --- Top Header: Type Badge, Name, Installed indicator ---
        header_layout = QHBoxLayout(); header_layout.setSpacing(8)

        # Type badge
        type_text: str = "PACK" if self.item.is_pack else self.item.entity_type.upper()
        type_badge = QLabel(f" {type_text} ")
        if self.item.is_pack:
            type_badge.setStyleSheet(
                "background-color: #0891b2; color: white; font-weight: bold; "
                "font-size: 11px; border-radius: 4px; padding: 2px 4px;"
            )
        elif self.item.entity_type == EntityType.STRUCTURE:
            type_badge.setStyleSheet(
                "background-color: #7c3aed; color: white; font-weight: bold; "
                "font-size: 11px; border-radius: 4px; padding: 2px 4px;"
            )
        elif self.item.entity_type == EntityType.ITEM:
            type_badge.setStyleSheet(
                "background-color: #d97706; color: white; font-weight: bold; "
                "font-size: 11px; border-radius: 4px; padding: 2px 4px;"
            )
        else:
            type_badge.setStyleSheet(
                "background-color: #2563eb; color: white; font-weight: bold; "
                "font-size: 11px; border-radius: 4px; padding: 2px 4px;"
            )
        header_layout.addWidget(type_badge)

        # Mod Name
        name_label = QLabel(self.item.name)
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #cdd6f4;")
        header_layout.addWidget(name_label, stretch=1)

        # Installed badge
        if self.item.is_installed:
            installed_badge = QLabel("✓ Installed")
            installed_badge.setStyleSheet(
                "color: #10b981; font-weight: bold; font-size: 11px; "
                "background-color: rgba(16, 185, 129, 0.15); "
                "border-radius: 4px; padding: 2px 6px;"
            )
            header_layout.addWidget(installed_badge)

        layout.addLayout(header_layout)

        # --- Sub-Header: Author and Version ---
        meta_label = QLabel(
            f"by @{self.item.author} • v{self.item.version} • {self.item.formatted_size}"
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

        # Action 3: Install / Uninstall button
        if self.item.is_installed:
            action_btn = QPushButton("Uninstall"); action_btn.setObjectName("DangerBtn")
            action_btn.setStyleSheet(
                "background-color: #ef4444; color: white; padding: 4px 12px; "
                "font-size: 11px; font-weight: bold; border-radius: 4px;"
            )
            action_btn.clicked.connect(lambda: self.uninstall_requested.emit(self.item))
        else:
            action_btn = QPushButton("Install")
            action_btn.setStyleSheet(
                "background-color: #10b981; color: white; padding: 4px 14px; "
                "font-size: 11px; font-weight: bold; border-radius: 4px;"
            )
            action_btn.clicked.connect(lambda: self.install_requested.emit(self.item))

        footer_layout.addWidget(action_btn)
        layout.addLayout(footer_layout)


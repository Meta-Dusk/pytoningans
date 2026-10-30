"""
PyToNingans Mod Browser - Mod Card Component
===========================================
Visual card widget rendering community mod details, ratings, download stats,
tags, outdated badges, update buttons, and one-click actions.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QMessageBox
)

from pytoningans.core.constants import EntityType, VerificationStatus
from ...mod_browser.auth import AuthManager

if TYPE_CHECKING:
    from ..models import CommunityModItem
    from ...mod_browser.auth import UserProfile


class ModCardWidget(QFrame):
    """Card widget representing an individual community mod or modpack listing."""

    install_requested = Signal(object)
    """Passes object of type `CommunityModItem`."""
    
    uninstall_requested = Signal(object)
    """Passes object of type `CommunityModItem`."""
    
    update_requested = Signal(object)
    """Passes object of type `CommunityModItem`."""
    
    inspect_requested = Signal(object)
    """Passes object of type `CommunityModItem`."""
    
    rate_requested = Signal(object)
    """Passes object of type `CommunityModItem`."""
    
    publish_requested = Signal(object)
    """Passes object of type `CommunityModItem`."""
    
    unpublish_requested = Signal(object)
    """Passes object of type `CommunityModItem`."""

    def __init__(self, mod_item: CommunityModItem, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.mod_item: CommunityModItem = mod_item
        self._setup_ui()

    def _is_owner(self) -> bool:
        """Determines if the currently logged-in user owns this mod/modpack."""
        user: Optional[UserProfile] = AuthManager.get().current_user
        if user is None or not user.id or user.id.startswith("local_"):
            return False
        return self.mod_item.author_id == user.id

    def _get_verification_badge(self) -> Optional[QLabel]:
        """Returns a verification status badge widget if applicable."""
        badge: Optional[QLabel] = None
        match self.mod_item.verification_status:
            case VerificationStatus.APPROVED:
                badge = QLabel("✓ Verified")
                badge.setObjectName("BadgeSuccess")
                verified_at: str = (
                    self.mod_item.verified_at[:10]
                    if self.mod_item.verified_at is not None
                    else 'Unknown'
                )
                badge.setToolTip(
                    f"Verified by: {self._get_verifier_name()}\n"
                    f"Verified at: {verified_at}"
                )
            case VerificationStatus.REJECTED:
                badge = QLabel("✗ Rejected")
                badge.setObjectName("BadgeWarning")
                badge.setToolTip(
                    f"Rejected by: {self._get_verifier_name()}\n"
                    f"Reason: Community review did not approve this mod."
                )
            case VerificationStatus.PENDING:
                badge = QLabel("◷ Pending")
                badge.setObjectName("BadgeInfo")
                badge.setToolTip("Pending verification by an admin.")
        return badge

    def _get_verifier_name(self) -> str:
        """Returns the display name of the user who verified this mod."""
        if self.mod_item.verified_by:
            return f"User {self.mod_item.verified_by[:8]}"
        return "Unknown"

    def _setup_ui(self) -> None:
        self.setFrameShape(QFrame.Shape.StyledPanel); self.setObjectName("ModCardWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(8)

        # --- Top Header: Type Badge, Name, Outdated Indicator, Installed status ---
        header_layout = QHBoxLayout(); header_layout.setSpacing(8)

        # Type badge
        type_text: str = "PACK" if self.mod_item.is_pack else self.mod_item.entity_type.upper()
        type_badge = QLabel(f" {type_text} ")
        if self.mod_item.is_pack:
            type_badge.setObjectName("BadgePack")
        elif self.mod_item.entity_type == EntityType.STRUCTURE:
            type_badge.setObjectName("BadgeStructure")
        elif self.mod_item.entity_type == EntityType.ITEM:
            type_badge.setObjectName("BadgeItem")
        else:
            type_badge.setObjectName("BadgeEntity")
        header_layout.addWidget(type_badge)

        # Mod Name
        name_label = QLabel(self.mod_item.name)
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #cdd6f4;")
        header_layout.addWidget(name_label, stretch=1)

        # Outdated warning badge
        if self.mod_item.is_outdated:
            reasons_text: str = "\n• ".join(self.mod_item.outdated_reasons)
            outdated_badge = QLabel("Outdated")
            outdated_badge.setToolTip(f"Outdated Compatibility Warning:\n• {reasons_text}")
            outdated_badge.setObjectName("BadgeWarning")
            header_layout.addWidget(outdated_badge)

        # Installation / Update Status Badges
        if self.mod_item.is_local_only:
            local_badge = QLabel(f"★ Local Creation (v{self.mod_item.version})")
            local_badge.setObjectName("BadgeLocal")
            header_layout.addWidget(local_badge)
        elif self.mod_item.is_installed:
            if self.mod_item.has_update:
                update_badge = QLabel(f"➜] Update Available (v{self.mod_item.version})")
                update_badge.setToolTip(
                    f"Installed: v{self.mod_item.installed_version} → Latest: v{self.mod_item.version}"
                )
                update_badge.setObjectName("BadgeInfo")
                header_layout.addWidget(update_badge)
            else:
                ver_display = self.mod_item.installed_version or self.mod_item.version
                installed_badge = QLabel(f"✓ Installed (v{ver_display})")
                installed_badge.setObjectName("BadgeSuccess")
                header_layout.addWidget(installed_badge)

        # Verification status badge
        verification_badge: Optional[QLabel] = self._get_verification_badge()
        if verification_badge is not None:
            header_layout.addWidget(verification_badge)

        layout.addLayout(header_layout)

        # --- Sub-Header: Author, Badges, GitHub link, and Version ---
        sub_layout = QHBoxLayout(); sub_layout.setSpacing(6)

        by_label = QLabel("by")
        by_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        sub_layout.addWidget(by_label)

        author_label = QLabel(self.mod_item.author)
        author_label.setStyleSheet("color: #cdd6f4; font-size: 12px; font-weight: bold;")
        sub_layout.addWidget(author_label)

        # Developer badge
        if self.mod_item.is_developer:
            dev_badge = QLabel("★ Developer")
            dev_badge.setToolTip("Official PyToNingans Core Developer")
            dev_badge.setStyleSheet("""
                background-color: rgba(203, 166, 247, 0.25);
                color: #cba6f7;
                border: 1px solid #cba6f7;
                border-radius: 3px;
                padding: 1px 5px;
                font-size: 10px;
                font-weight: bold;
            """)
            sub_layout.addWidget(dev_badge)

        # Verified badge if not developer but verified
        elif "Verified Creator" in self.mod_item.author_badges:
            verified_badge = QLabel("✓ Verified")
            verified_badge.setToolTip("Verified Community Creator")
            verified_badge.setStyleSheet("""
                background-color: rgba(137, 220, 235, 0.2);
                color: #89dceb;
                border: 1px solid #89dceb;
                border-radius: 3px;
                padding: 1px 5px;
                font-size: 10px;
                font-weight: bold;
            """)
            sub_layout.addWidget(verified_badge)
        
        # print(f"[ModCardWidget::_setup_ui] Author Badges: {self.item.author_badges}")

        # GitHub Profile Link (clickable)
        author_gh: Optional[str] = self.mod_item.author_github
        if author_gh is not None:
            gh_link = QLabel(
                f"<a href='https://github.com/{author_gh}' "
                "style='color: #89b4fa; "
                f"text-decoration: none;'>{author_gh} ↗</a>"
            )
            gh_link.setOpenExternalLinks(True)
            gh_link.setToolTip(f"View the GitHub profile of '{author_gh}' in your default browser")
            gh_link.setStyleSheet("font-size: 11px;")
            sub_layout.addWidget(gh_link)

        sub_type: str = " • Local Draft" if self.mod_item.is_local_only else ""
        meta_label = QLabel(
            f"• v{self.mod_item.version} • {self.mod_item.formatted_size}{sub_type}"
        )
        meta_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        sub_layout.addWidget(meta_label)
        sub_layout.addStretch()

        layout.addLayout(sub_layout)

        # --- Description ---
        desc_label = QLabel(self.mod_item.description); desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #bac2de; font-size: 12px; margin-top: 2px; margin-bottom: 2px;")
        layout.addWidget(desc_label)

        # If modpack, display contained entities pill list
        if self.mod_item.is_pack and self.mod_item.contained_entities:
            pack_contents_lbl = QLabel(f"Includes: {', '.join(self.mod_item.contained_entities)}")
            pack_contents_lbl.setWordWrap(True)
            pack_contents_lbl.setStyleSheet("color: #89dceb; font-size: 11px; font-style: italic;")
            layout.addWidget(pack_contents_lbl)

        # --- Tags row ---
        if self.mod_item.tags:
            tags_layout = QHBoxLayout(); tags_layout.setSpacing(4)
            for tag in self.mod_item.tags[:4]:
                chip = QLabel(f"#{tag}")
                chip.setStyleSheet("color: #6c7086; font-size: 11px;")
                tags_layout.addWidget(chip)
            tags_layout.addStretch()
            layout.addLayout(tags_layout)

        # --- Stats and Actions Footer ---
        footer_layout = QHBoxLayout(); footer_layout.setSpacing(10)

        if self.mod_item.is_local_only:
            draft_lbl = QLabel("Local Workspace")
            draft_lbl.setStyleSheet("color: #cba6f7; font-size: 11px; font-style: italic;")
            footer_layout.addWidget(draft_lbl)
            footer_layout.addStretch()

            inspect_btn = QPushButton("Inspect")
            inspect_btn.setToolTip("View files and run AST security audit on this local mod")
            inspect_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
            inspect_btn.clicked.connect(lambda: self.inspect_requested.emit(self.mod_item))
            footer_layout.addWidget(inspect_btn)

            pub_btn = QPushButton("Publish to Community")
            pub_btn.setObjectName("SuccessBtn")
            pub_btn.setToolTip(f"Package and publish '{self.mod_item.name}' to the community catalog")
            pub_btn.setStyleSheet("padding: 4px 12px; font-size: 11px; font-weight: bold;")
            pub_btn.clicked.connect(lambda: self.publish_requested.emit(self.mod_item))
            footer_layout.addWidget(pub_btn)
        else:
            # Rating display
            rating_lbl = QLabel(self.mod_item.formatted_rating)
            rating_lbl.setStyleSheet("color: #f9e2af; font-weight: bold; font-size: 12px;")
            footer_layout.addWidget(rating_lbl)

            # Downloads display
            dl_lbl = QLabel(f"🡻 {self.mod_item.downloads}")
            dl_lbl.setStyleSheet("color: #a6adc8; font-size: 12px;")
            footer_layout.addWidget(dl_lbl)

            footer_layout.addStretch()

            # Action: Changelog button if multiple releases or changelog available
            if self.mod_item.releases:
                changelog_btn = QPushButton("Changelog")
                changelog_btn.setToolTip("View version history and release notes")
                changelog_btn.setStyleSheet("padding: 4px 8px; font-size: 11px; color: #a6adc8;")
                changelog_btn.clicked.connect(self._show_changelog)
                footer_layout.addWidget(changelog_btn)

            # Action 1: Rate button
            rate_btn = QPushButton("Rate")
            rate_btn.setToolTip(f"Submit a rating (1.0-10.0) for {self.mod_item.name}")
            rate_btn.setStyleSheet("padding: 4px 8px; font-size: 11px;")
            rate_btn.clicked.connect(lambda: self.rate_requested.emit(self.mod_item))
            footer_layout.addWidget(rate_btn)

            # Action 2: Inspect and Safety button
            inspect_btn = QPushButton("Inspect")
            inspect_btn.setToolTip("View files, source code, and run AST security audit")
            inspect_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
            inspect_btn.clicked.connect(lambda: self.inspect_requested.emit(self.mod_item))
            footer_layout.addWidget(inspect_btn)

            # Action 3: Install / Update / Uninstall buttons
            if self.mod_item.is_installed:
                if self.mod_item.has_update:
                    update_btn = QPushButton(f"Update (v{self.mod_item.version})")
                    update_btn.setToolTip(f"Upgrade to version {self.mod_item.version}")
                    update_btn.setObjectName("InfoBtn")
                    update_btn.clicked.connect(lambda: self.update_requested.emit(self.mod_item))
                    footer_layout.addWidget(update_btn)

                uninstall_btn = QPushButton("Uninstall")
                uninstall_btn.setObjectName("DangerBtn")
                uninstall_btn.clicked.connect(lambda: self.uninstall_requested.emit(self.mod_item))
                footer_layout.addWidget(uninstall_btn)
            else:
                install_btn = QPushButton("Install")
                install_btn.setObjectName("SuccessBtn")
                install_btn.clicked.connect(lambda: self.install_requested.emit(self.mod_item))
                footer_layout.addWidget(install_btn)

            # Action 4: Unpublish button (owner only)
            if self._is_owner():
                unpub_btn = QPushButton("Unpublish")
                unpub_btn.setObjectName("DangerBtn")
                unpub_btn.setToolTip(f"Remove '{self.mod_item.name}' from the community catalog")
                unpub_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
                unpub_btn.clicked.connect(lambda: self.unpublish_requested.emit(self.mod_item))
                footer_layout.addWidget(unpub_btn)

        layout.addLayout(footer_layout)

    def _show_changelog(self) -> None:
        """Displays release notes in an information dialog."""
        lines: list[str] = [f"<b>Release History for {self.mod_item.name}</b><br>"]
        for r in self.mod_item.releases:
            lines.append(f"<b>Version {r.version}</b> ({r.created_at}):<br>• {r.changelog}<br>")
        QMessageBox.information(self, f"{self.mod_item.name} - Changelog", "<br>".join(lines))

"""
PyToNingans Mod Browser - Admin Verification Dialog
===================================================
Allows admins to review pending mod submissions and approve/reject them.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Any, Literal

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QWidget, QFrame, QListWidget,
    QListWidgetItem, QTextEdit, QSplitter
)

from pytoningans.core.constants import VerificationStatus
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.utils.assets import get_main_icon
from ..auth import AuthManager

if TYPE_CHECKING:
    from ..client import ModBrowserClient
    from ..auth.models import UserProfile


class VerificationWorker(QThread):
    """Background worker for fetching pending mods and verifying them."""
    
    finished = Signal(bool, str, list)
    """Returns: `(ok, msg, data)`."""
    
    verify_finished = Signal(bool, str)
    """Returns: `(ok, msg)`."""
    
    def __init__(
        self, client: ModBrowserClient,
        action: Literal["fetch", "verify"] = "fetch",
        mod_id: str = "", status: str = ""
    ) -> None:
        super().__init__()
        self.client = client
        self.action = action
        self.mod_id = mod_id
        self.status = status
    
    def run(self) -> None:
        if self.action == "fetch":
            ok, msg, data = self.client.cloud.fetch_pending_mods()
            self.finished.emit(ok, msg, data)
        elif self.action == "verify":
            user: Optional[UserProfile] = AuthManager.get().current_user
            verified_by: str = user.id if user else "unknown"
            ok, msg = self.client.cloud.verify_mod(self.mod_id, self.status, verified_by)
            self.verify_finished.emit(ok, msg)


class VerificationDialog(QDialog):
    """Admin dialog for reviewing and verifying pending mod submissions."""
    
    def __init__(
        self, client: ModBrowserClient,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.client: ModBrowserClient = client
        self.auth: AuthManager = AuthManager.get()
        self.pending_mods: list[dict] = []
        self.selected_mod: Optional[dict] = None
        
        self.setWindowTitle("Admin Verification Panel"); self.setWindowIcon(get_main_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(900, 600)
        
        self._setup_ui()
        self._load_pending_mods()
    
    def exec(self) -> int:
        if not self._check_admin():
            QMessageBox.critical(
                self, "Access Denied", "You must be an admin to access this panel."
            )
            return QDialog.DialogCode.Rejected
        
        return super().exec()
    
    def _check_admin(self) -> bool:
        """Check if current user is an admin."""
        return self.client.cloud.is_admin(allow_devs=False)
    
    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self, "Admin Verification Panel")
        main_layout.addWidget(self.title_bar)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Pending Mod Submissions")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_pending_mods)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - List of pending mods
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel); left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.mod_list = QListWidget(); self.mod_list.setMinimumWidth(300)
        self.mod_list.currentItemChanged.connect(self._on_mod_selected)
        left_layout.addWidget(self.mod_list)
        
        # Right panel - Mod details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel); right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.details_frame = QFrame()
        self.details_frame.setFrameShape(QFrame.Shape.StyledPanel)
        details_layout = QVBoxLayout(self.details_frame)
        details_layout.setContentsMargins(16, 16, 16, 16); details_layout.setSpacing(8)
        
        self.detail_title = QLabel("Select a mod to review")
        self.detail_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        details_layout.addWidget(self.detail_title)
        
        self.detail_author = QLabel("")
        self.detail_author.setStyleSheet("color: #888888;")
        details_layout.addWidget(self.detail_author)
        
        self.detail_type = QLabel("")
        self.detail_type.setStyleSheet("color: #888888; font-size: 11px;")
        details_layout.addWidget(self.detail_type)
        
        details_layout.addWidget(QLabel("Description:"))
        self.detail_description = QTextEdit()
        self.detail_description.setReadOnly(True)
        self.detail_description.setMaximumHeight(100)
        details_layout.addWidget(self.detail_description)
        
        details_layout.addWidget(QLabel("Changelog:"))
        self.detail_changelog = QTextEdit()
        self.detail_changelog.setReadOnly(True)
        self.detail_changelog.setMaximumHeight(80)
        details_layout.addWidget(self.detail_changelog)
        
        # Verification info
        self.verification_info = QLabel("")
        self.verification_info.setStyleSheet("font-size: 11px; color: #888888;")
        details_layout.addWidget(self.verification_info)
        
        details_layout.addStretch()
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.reject_btn = QPushButton("Reject")
        self.reject_btn.setObjectName("DangerBtn")
        self.reject_btn.setEnabled(False)
        self.reject_btn.clicked.connect(lambda: self._verify_selected(VerificationStatus.REJECTED))
        action_layout.addWidget(self.reject_btn)
        
        self.approve_btn = QPushButton("Approve")
        self.approve_btn.setObjectName("SuccessBtn")
        self.approve_btn.setEnabled(False)
        self.approve_btn.clicked.connect(lambda: self._verify_selected(VerificationStatus.APPROVED))
        action_layout.addWidget(self.approve_btn)
        
        details_layout.addLayout(action_layout)
        
        right_layout.addWidget(self.details_frame)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 600])
        
        layout.addWidget(splitter)
        main_layout.addWidget(content)
    
    def _load_pending_mods(self) -> None:
        """Load pending mods from the cloud."""
        self.mod_list.clear()
        self.mod_list.addItem("Loading...")
        self.refresh_btn.setEnabled(False)
        
        self.worker = VerificationWorker(self.client, action="fetch")
        self.worker.finished.connect(self._on_pending_loaded)
        self.worker.start()
    
    def _on_pending_loaded(self, ok: bool, msg: str, data: list) -> None:
        """Handle loaded pending mods."""
        self.refresh_btn.setEnabled(True)
        self.mod_list.clear()
        
        if not ok:
            self.mod_list.addItem(f"Error: {msg}")
            return
        
        self.pending_mods = data
        
        if not data:
            self.mod_list.addItem("No pending mods to review.")
            return
        
        for mod in data:
            item = QListWidgetItem()
            name: str = mod.get("name", "Unknown")
            author: str = mod.get("author", "Unknown")
            version: str = mod.get("version", "1.0.0")
            is_pack: bool = mod.get("is_pack", False)
            type_label: str = "[PACK] " if is_pack else "[MOD] "
            item.setText(f"{type_label}{name} v{version} by {author}")
            item.setData(Qt.ItemDataRole.UserRole, mod)
            self.mod_list.addItem(item)
    
    def _on_mod_selected(
        self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]
    ) -> None:
        """Handle mod selection in the list."""
        if current is None:
            self._clear_details()
            return
        
        mod_data = current.data(Qt.ItemDataRole.UserRole)
        if not mod_data:
            self._clear_details()
            return
        
        self.selected_mod = mod_data
        self._display_mod_details(mod_data)
        self.approve_btn.setEnabled(True)
        self.reject_btn.setEnabled(True)
    
    def _clear_details(self) -> None:
        """Clear the details panel."""
        self.detail_title.setText("Select a mod to review")
        self.detail_author.setText("")
        self.detail_type.setText("")
        self.detail_description.setPlainText("")
        self.detail_changelog.setPlainText("")
        self.verification_info.setText("")
        self.selected_mod = None
        self.approve_btn.setEnabled(False)
        self.reject_btn.setEnabled(False)
    
    def _display_mod_details(self, mod: dict) -> None:
        """Display mod details in the right panel."""
        self.detail_title.setText(f"{mod.get('name', 'Unknown')} v{mod.get('version', '1.0.0')}")
        self.detail_author.setText(f"Author: {mod.get('author', 'Unknown')}")
        
        is_pack: bool = mod.get("is_pack", False)
        entity_type: str = mod.get("entity_type", "entity")
        self.detail_type.setText(f"Type: {'Modpack' if is_pack else entity_type.capitalize()}")
        
        self.detail_description.setPlainText(mod.get("description", "No description provided."))
        
        # Get latest release changelog
        releases: list[dict[str, Any]] = mod.get("mod_releases", [])
        if releases:
            latest = releases[0]
            self.detail_changelog.setPlainText(latest.get("changelog", "No changelog provided."))
        else:
            self.detail_changelog.setPlainText("No releases found.")
        
        # Verification info
        created_at: str = mod.get("created_at", "")
        self.verification_info.setText(f"Submitted: {created_at[:10] if created_at else 'Unknown'}")
    
    def _verify_selected(self, status: VerificationStatus) -> None:
        """Verify (approve/reject) the selected mod."""
        if not self.selected_mod:
            return
        
        mod_id: str = self.selected_mod.get("id", "")
        mod_name: str = self.selected_mod.get("name", "Unknown")
        
        reply: QMessageBox.StandardButton = QMessageBox.question(
            self,
            f"{status.capitalize()} Mod",
            f"Are you sure you want to {status} '{mod_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.approve_btn.setEnabled(False)
        self.reject_btn.setEnabled(False)
        
        self.worker = VerificationWorker(self.client, action="verify", mod_id=mod_id, status=status)
        self.worker.verify_finished.connect(self._on_verify_finished)
        self.worker.start()
    
    def _on_verify_finished(self, ok: bool, msg: str) -> None:
        """Handle verification result."""
        self.approve_btn.setEnabled(True)
        self.reject_btn.setEnabled(True)
        
        if ok:
            QMessageBox.information(self, "Success", msg)
            self._load_pending_mods()
        else:
            QMessageBox.warning(self, "Failed", msg)

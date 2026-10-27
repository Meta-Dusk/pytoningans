"""
PyToNingans Mod Browser - Async Background Workers
==================================================
Provides dedicated QThread worker implementations for non-blocking
catalog synchronization, mod downloads/installations, and authentication requests.
Keeps the main desktop UI responsive with 0ms freezing.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from PySide6.QtCore import QThread, Signal

if TYPE_CHECKING:
    from PySide6.QtCore import QObject
    from .client import ModBrowserClient
    from .models import CommunityModItem
    from .auth import AuthManager


class CatalogSyncWorker(QThread):
    """Background worker for querying and synchronizing community catalog from Supabase."""

    sync_completed = Signal(bool, str, int)
    """Broadcasts the following: `(success, message, total_mods_count)`."""

    def __init__(self, client: ModBrowserClient, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.client: ModBrowserClient = client

    def run(self) -> None:
        try:
            success, msg = self.client.refresh_catalog_from_cloud()
            count: int = len(self.client._catalog_items)
            self.sync_completed.emit(success, msg, count)
        except Exception as e:
            self.sync_completed.emit(False, f"Catalog sync error: {e}", 0)


class ModInstallWorker(QThread):
    """Background worker for non-blocking mod package downloading, extraction, or updates."""

    install_completed = Signal(bool, str, object)
    """`.connect(success, message, CommunityModItem)`"""

    def __init__(
        self,
        client: ModBrowserClient,
        item: CommunityModItem,
        action: str = "install",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.client: ModBrowserClient = client
        self.item: CommunityModItem = item
        self.action: str = action

    def run(self) -> None:
        try:
            if self.action == "install":
                success, msg = self.client.install_mod(self.item)
            elif self.action == "update":
                success, msg = self.client.update_mod(self.item)
            elif self.action == "uninstall":
                success, msg = self.client.uninstall_mod(self.item)
            else:
                success, msg = False, f"Unknown action '{self.action}'."

            self.install_completed.emit(success, msg, self.item)
        except Exception as e:
            self.install_completed.emit(False, f"Operation failed: {e}", self.item)


class AuthWorker(QThread):
    """Background worker for asynchronous Supabase Auth sign-in and sign-up requests."""

    auth_completed = Signal(bool, str, object)  # success, message, Optional[UserProfile]

    def __init__(
        self,
        auth: AuthManager,
        action: str,  # "signin" or "signup"
        email: str,
        password: str,
        username: str = "",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.auth: AuthManager = auth
        self.action: str = action
        self.email: str = email
        self.password: str = password
        self.username: str = username

    def run(self) -> None:
        try:
            if self.action == "signin":
                success, msg, user = self.auth.sign_in_with_password(self.email, self.password)
            elif self.action == "signup":
                success, msg, user = self.auth.sign_up(self.email, self.password, self.username)
            else:
                success, msg, user = False, f"Unknown auth action '{self.action}'", None

            self.auth_completed.emit(success, msg, user)
        except Exception as e:
            self.auth_completed.emit(False, f"Authentication error: {e}", None)


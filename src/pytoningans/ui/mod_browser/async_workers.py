"""
PyToNingans Mod Browser - Async Background Workers
==================================================
Provides dedicated QThread worker implementations for non-blocking
catalog synchronization, mod downloads/installations, and authentication requests.
Keeps the main desktop UI responsive with 0ms freezing.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Literal
from PySide6.QtCore import QThread, Signal

if TYPE_CHECKING:
    from PySide6.QtCore import QObject
    from .client import ModBrowserClient
    from .models import CommunityModItem
    from .auth import AuthManager

type _InstallWorkerAction = Literal["install", "update", "uninstall"]
type _AuthWorkerAction = Literal["signin", "signup"]


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
    """
    Passes a tuple of type:\n
    `(success: bool, message: str, CommunityModItem)`.
    """

    def __init__(
        self,
        client: ModBrowserClient,
        mod_item: CommunityModItem,
        action: _InstallWorkerAction = "install",
        parent: Optional[QObject] = None,
    ) -> None:
        """
        Install, uninstall, or update a mod/modpack.

        Args:
            client (ModBrowserClient): ModBrowserClient instance
            mod_item (CommunityModItem): CommunityModItem instance
            action (_InstallWorkerAction, optional): "(install | uninstall | update)".
                Defaults to "install".
            parent (Optional[QObject], optional): Optional widget tree parent. Defaults to None.
        """
        super().__init__(parent)
        self.client: ModBrowserClient = client
        self.mod_item: CommunityModItem = mod_item
        self.action: _InstallWorkerAction = action

    def run(self) -> None:
        """
        Attempts to either install, update, or uninstall the provided `mod_item`.\n
        Emits `install_completed` Signal.
        """
        try:
            match self.action:
                case "install":
                    success, msg = self.client.install_mod(self.mod_item)
                case "update":
                    success, msg = self.client.update_mod(self.mod_item)
                case "uninstall":
                    success, msg = self.client.uninstall_mod(self.mod_item)
                case _:
                    success, msg = False, f"Unknown action '{self.action}'."

            self.install_completed.emit(success, msg, self.mod_item)
        except Exception as e:
            self.install_completed.emit(False, f"Operation failed: {e}", self.mod_item)


class AuthWorker(QThread):
    """Background worker for asynchronous Supabase Auth sign-in and sign-up requests."""

    auth_completed = Signal(bool, str, object)
    """
    Passes a tuple of type:\n
    `(success: bool, message: str, Optional[UserProfile])`.
    """

    def __init__(
        self,
        auth: AuthManager,
        action: _AuthWorkerAction,
        email: str,
        password: str,
        username: str = "",
        parent: Optional[QObject] = None,
    ) -> None:
        """
        Request a sign-in or sign-up for Supabase Auth.

        Args:
            auth (AuthManager): AuthManager instance
            action (_AuthWorkerAction): "(signin | signup)"
            email (str): User email
            password (str): User password
            username (str, optional): Optional username. Defaults to "".
            parent (Optional[QObject], optional): Optional widget tree parent. Defaults to None.
        """
        super().__init__(parent)
        self.auth: AuthManager = auth
        self.action: _AuthWorkerAction = action
        self.email: str = email
        self.password: str = password
        self.username: str = username

    def run(self) -> None:
        """
        Attempts a request for the user to either sign-in or sign-up with the Supabase Auth.\n
        Emits `auth_completed` Signal.
        """
        try:
            match self.action:
                case "signin":
                    success, msg, user = self.auth.sign_in_with_password(self.email, self.password)
                case "signup":
                    success, msg, user = self.auth.sign_up(self.email, self.password, self.username)
                case _:
                    success, msg, user = False, f"Unknown auth action '{self.action}'", None

            self.auth_completed.emit(success, msg, user)
        except Exception as e:
            self.auth_completed.emit(False, f"Authentication error: {e}", None)

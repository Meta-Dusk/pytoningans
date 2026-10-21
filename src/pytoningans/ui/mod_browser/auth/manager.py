"""
PyToNingans Mod Browser :: Auth Manager
=======================================
Singleton QObject that composes AuthConfig, AuthSessionStore, and the auth mixin classes
into a single, unified authentication manager for the mod browser.
"""
from __future__ import annotations

import threading
from typing import Optional

from PySide6.QtCore import QObject, Signal

from .config import AuthConfig
from .session import AuthSessionStore
from .models import UserProfile
from .profile import AuthProfileMixin
from .sign_in import AuthSignInMixin
from .oauth import AuthOAuthMixin


class AuthManager(QObject, AuthProfileMixin, AuthSignInMixin, AuthOAuthMixin):
    """
    Manages user authentication against Supabase Auth (or offline local storage).
    Emits auth_state_changed whenever sign-in, sign-up, or sign-out occurs.

    Composition:
    - ``_config``  — AuthConfig: credential loading/saving and header building
    - ``_store``   — AuthSessionStore: on-disk session persistence and token refresh
    - AuthProfileMixin: creator profile read/write
    - AuthSignInMixin: email/password and local offline sign-in
    - AuthOAuthMixin: OAuth browser-redirect flows
    """

    auth_state_changed = Signal(object)
    """Emits Optional[UserProfile] — None on sign-out."""

    _instance: Optional[AuthManager] = None

    def __init__(self) -> None:
        super().__init__()
        self._config = AuthConfig()
        self._store = AuthSessionStore(self._config)
        self._oauth_server = None
        self._oauth_thread: Optional[threading.Thread] = None
            
        self._store.load(on_refresh=self._on_refresh)

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def get(cls) -> AuthManager:
        if cls._instance is None:
            cls._instance = AuthManager()
        return cls._instance

    # ------------------------------------------------------------------
    # Core properties
    # ------------------------------------------------------------------

    @property
    def current_user(self) -> Optional[UserProfile]:
        return (
            self._store.current_session.user if
            self._store.current_session is not None else None
        )

    @property
    def is_authenticated(self) -> bool:
        return self._store.current_session is not None

    @property
    def is_cloud_configured(self) -> bool:
        return self._config.is_cloud_configured
    
    @property
    def supabase_pub_key(self) -> str:
        return self._config.supabase_pub_key
    
    @property
    def supabase_url(self) -> str:
        return self._config.supabase_url

    # ------------------------------------------------------------------
    # Config delegation (backward-compatible surface)
    # ------------------------------------------------------------------

    def save_config(self, url: str, anon_key: str) -> None:
        """Persists Supabase credentials. Delegates to AuthConfig."""
        self._config.save(url, anon_key)

    # ------------------------------------------------------------------
    # Sign-out
    # ------------------------------------------------------------------

    def sign_out(self) -> None:
        """
        Clears local authentication session, notifies cloud if connected, and emits signal.
        """
        import urllib.request

        if (
            self.is_cloud_configured and
            self._store.current_session and
            self._store.current_session.access_token and
            self._store.current_session.access_token != "mock_local_token"
        ):
            try:
                logout_endpoint: str = self._config.auth_endpoint("/auth/v1/logout")
                headers: dict[str, str] = self._config.build_headers(
                    auth_token=self._store.current_session.access_token
                )
                logout_req = urllib.request.Request(
                    logout_endpoint,
                    data=b"{}",
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(logout_req, timeout=3) as _:
                    pass
            except Exception:
                pass

        self._store.current_session = None
        self._store.save()
        self.auth_state_changed.emit(None)

    # ------------------------------------------------------------------
    # Session delegation (backward-compatible surface)
    # ------------------------------------------------------------------
    
    def _on_refresh(self) -> None:
        self.refresh_session()

    def refresh_session(self) -> bool:
        """Refreshes the current access token. Delegates to AuthSessionStore."""
        return self._store.refresh()

    def ensure_valid_session(self) -> bool:
        """
        Ensures the session token is valid (proactive refresh). Delegates to AuthSessionStore.
        """
        return self._store.ensure_valid()

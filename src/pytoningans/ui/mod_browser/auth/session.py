"""
PyToNingans Mod Browser - Auth Session Persistence and Refresh
==============================================================
Handles loading, saving, and refreshing Supabase auth sessions from disk.
"""
from __future__ import annotations

import json, threading, time
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from pytoningans.utils.paths import get_settings_path
from pytoningans.core.settings import SettingsManager

from .models import AuthSession, UserProfile, is_known_developer

if TYPE_CHECKING:
    from .config import AuthConfig


class AuthSessionStore:
    """
    Manages on-disk session persistence and Supabase token refresh.
    Intended to be used as a component inside AuthManager.
    """

    def __init__(self, config: AuthConfig) -> None:
        self._config = config
        self._session_path: Path = get_settings_path().parent / "auth_session.json"
        self.current_session: Optional[AuthSession] = None

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def load(self, on_refresh: Optional[Callable[[], None]] = None) -> None:
        """
        Restores a previously saved AuthSession from disk.
        Triggers a background token refresh when the loaded token is near expiry.
        """
        if not self._session_path.exists():
            return
        try:
            data: dict[str, Any] = json.loads(self._session_path.read_text(encoding="utf-8"))
            user: UserProfile = self._build_user_from_session_data(data.get("user", {}))
            self.current_session = AuthSession(
                access_token=data.get("access_token", ""),
                refresh_token=data.get("refresh_token", ""),
                user=user,
                expires_at=data.get("expires_at", 0.0),
            )
            if (
                self.current_session.access_token and
                self.current_session.access_token != "mock_local_token" and
                time.time() >= self.current_session.expires_at - 120
            ):
                target = on_refresh or self.refresh
                threading.Thread(target=target, daemon=True).start()
        except Exception:
            self.current_session = None

    def save(self) -> None:
        """Writes the current session to disk, or removes the file when signed out."""
        if self.current_session is None:
            if self._session_path.exists():
                try:
                    self._session_path.unlink()
                except Exception:
                    pass
            return
        try:
            payload: dict[str, Any] = {
                "access_token": self.current_session.access_token,
                "refresh_token": self.current_session.refresh_token,
                "expires_at": self.current_session.expires_at,
                "user": asdict(self.current_session.user),
            }
            self._session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------

    def refresh(self) -> bool:
        """
        Refreshes the access token using the current refresh token against Supabase Auth.
        Returns True if the session was successfully refreshed, False otherwise.
        """
        if (
            self.current_session is None or
            not self._config.is_cloud_configured or
            not self.current_session.refresh_token or
            self.current_session.refresh_token == "mock_refresh_token"
        ):
            return False

        endpoint: str = self._config.auth_endpoint("/auth/v1/token?grant_type=refresh_token")
        payload: bytes = json.dumps(
            {"refresh_token": self.current_session.refresh_token}
        ).encode("utf-8")
        req = urllib.request.Request(
            endpoint, data=payload, headers=self._config.build_headers(), method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
                new_access_token: str = data.get("access_token", "")
                if new_access_token:
                    self.current_session.access_token = new_access_token
                    self.current_session.refresh_token = data.get(
                        "refresh_token", self.current_session.refresh_token
                    )
                    self.current_session.expires_at = time.time() + int(data.get("expires_in", 3600))
                    self.save()
                    return True
        except Exception:
            pass
        return False

    def ensure_valid(self) -> bool:
        """
        Proactively refreshes the session if the access token has expired or will
        expire within 60 seconds.
        Returns True when no action is required (local or offline session).
        """
        if (
            self.current_session is None or
            self.current_session.access_token == "mock_local_token" or
            not self._config.is_cloud_configured
        ):
            return True
        if time.time() >= self.current_session.expires_at - 60:
            return self.refresh()
        return True

    # ------------------------------------------------------------------
    # Session data deserialization
    # ------------------------------------------------------------------

    def _build_user_from_session_data(self, user_data: dict[str, Any]) -> UserProfile:
        """
        Deserializes raw session JSON into a UserProfile.
        Applies backward-compatibility provider deduction and badge assignment.
        """
        u_email: str = user_data.get("email", "creator@pytoningans.local")
        u_name: str = user_data.get("username", "Modder")
        u_gh = user_data.get("github_username")
        u_goog = user_data.get("google_email")
        u_prov = user_data.get("primary_provider", "email")
        u_provs: list[str] = list(user_data.get("providers", []))
        u_provs, u_prov, u_gh, u_goog = self._resolve_providers(
            user_data, u_provs, u_prov, u_gh, u_goog, u_name
        )
        u_cust = self._resolve_custom_avatar(user_data)
        is_dev, badges = self._resolve_developer_and_badges(user_data, u_name, u_gh, u_provs)

        return UserProfile(
            id=user_data.get("id", "local_user"),
            email=u_email,
            username=u_name,
            created_at=user_data.get("created_at", ""),
            avatar_url=user_data.get("avatar_url"),
            custom_avatar_path=u_cust,
            bio=user_data.get("bio", ""),
            primary_provider=u_prov,
            providers=u_provs,
            github_username=u_gh,
            google_email=u_goog,
            email_verified=user_data.get("email_verified", False),
            is_developer=is_dev,
            badges=badges,
        )

    @staticmethod
    def _resolve_providers(
        user_data: dict[str, Any],
        u_provs: list[str],
        u_prov: str,
        u_gh: Optional[str],
        u_goog: Optional[str],
        u_name: str,
    ) -> tuple[list[str], str, Optional[str], Optional[str]]:
        """
        Applies backward-compatible provider list deduction and fills in
        github_username / google_email from context where missing.
        """
        # Backward compatibility: single provider entry
        if not u_provs and u_prov:
            u_provs = [u_prov]

        avatar_url_str: str = str(user_data.get("avatar_url", "")).lower()

        # GitHub provider detection
        if (
            avatar_url_str and
            "github" in avatar_url_str or
            u_gh is not None or
            u_prov == "github" or
            "github" in u_provs
        ):
            if "github" not in u_provs:
                u_provs.append("github")
            u_prov = "github"
            if not u_gh and "github" in u_provs:
                u_gh = u_name

        # Google provider detection — only when genuinely linked via Google OAuth
        if "google" in avatar_url_str or u_prov == "google":
            if "google" not in u_provs:
                u_provs.append("google")
        if "google" not in u_provs and u_prov != "google":
            u_goog = None

        return u_provs, u_prov, u_gh, u_goog

    @staticmethod
    def _resolve_custom_avatar(user_data: dict[str, Any]) -> Optional[str]:
        """Returns a valid custom avatar path from session data or SettingsManager fallback."""
        u_avatar = user_data.get("custom_avatar_path")
        if not u_avatar:
            try:
                s_avatar = SettingsManager.get().settings.creator_avatar_path
                if s_avatar and Path(s_avatar).is_file():
                    u_avatar = s_avatar
            except Exception:
                pass
        return u_avatar or None

    @staticmethod
    def _resolve_developer_and_badges(
        user_data: dict[str, Any],
        username: str,
        github_username: Optional[str],
        providers: list[str],
    ) -> tuple[bool, list[str]]:
        """Resolves developer status and assembles the badge list for the user."""
        is_dev = user_data.get("is_developer")
        if is_dev is None:
            is_dev = is_known_developer(
                user_id=str(user_data.get("id", "")),
                username=username,
                github_username=github_username,
            )

        badges: list[str] = list(user_data.get("badges", []))
        if is_dev and "Developer" not in badges:
            badges.insert(0, "Developer")
        if (
            ("github" in providers or "google" in providers)
            and "Verified Creator" not in badges
            and not str(user_data.get("id", "")).startswith("local_")
        ):
            badges.append("Verified Creator")
        if str(user_data.get("id", "")).startswith("local_") and "Offline Creator" not in badges:
            badges.append("Offline Creator")

        return bool(is_dev), badges

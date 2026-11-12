"""
PyToNingans Mod Browser - Auth Session Persistence and Refresh
==============================================================
Handles loading, saving, and refreshing Supabase auth sessions using OS Keychains
for token storage and disk storage for non-sensitive metadata.
"""
from __future__ import annotations

import json, threading, time, keyring, logging
import urllib.request
import urllib.error

from keyring.errors import PasswordDeleteError
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from pytoningans.utils import get_settings_path
from pytoningans.core.settings import SettingsManager
from .models import AuthSession, UserProfile, is_known_developer

if TYPE_CHECKING:
    from .config import AuthConfig


logger: logging.Logger = logging.getLogger(__name__)

KEYRING_SERVICE_NAME = "PyToNingans"
KEYRING_ACCOUNT_NAME = "supabase_tokens"


class AuthSessionStore:
    """
    Manages session persistence and Supabase token refresh.
    Tokens are stored securely in the native OS Keychain (macOS / Windows), 
    while non-sensitive user profile metadata is stored on disk.
    """

    def __init__(self, config: AuthConfig) -> None:
        self._config = config
        self._session_path: Path = get_settings_path().parent / "auth_session.json"
        self.current_session: Optional[AuthSession] = None
        self.is_offline: bool = False

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def load(self, on_refresh: Optional[Callable[[], None]] = None) -> None:
        """
        Restores user profile metadata from disk and the refresh token from OS Keychain.
        Triggers a token refresh to obtain a valid access token on launch.
        """
        if not self._session_path.exists():
            return

        try:
            # Fetch non-sensitive user state from disk
            data: dict[str, Any] = json.loads(self._session_path.read_text(encoding="utf-8"))
            user: UserProfile = self._build_user_from_session_data(data.get("user", {}))

            # Fetch ONLY the short refresh token from OS Keychain
            stored_refresh_token = keyring.get_password(
                KEYRING_SERVICE_NAME, KEYRING_ACCOUNT_NAME
            ) or ""

            self.current_session = AuthSession(
                access_token="",  #? Access token will be populated upon refresh
                refresh_token=stored_refresh_token,
                user=user,
                expires_at=data.get("expires_at", 0.0),
            )

            # Fetch a fresh access token using the valid refresh token
            if (
                self.current_session.refresh_token and
                self.current_session.refresh_token != "mock_refresh_token"
            ):
                target = on_refresh or self.refresh
                threading.Thread(target=target, daemon=True).start()
        except Exception as e:
            err_msg: str = f"Failed to load local auth session: {e}"
            logger.error(err_msg)
            print(err_msg)
            self.current_session = None

    def save(self) -> None:
        """
        Persists the short refresh token to the OS Keychain and user metadata to disk.
        """
        if self.current_session is None:
            if self._session_path.exists():
                try:
                    self._session_path.unlink()
                except Exception:
                    pass
            try:
                keyring.delete_password(KEYRING_SERVICE_NAME, KEYRING_ACCOUNT_NAME)
            except (PasswordDeleteError, Exception):
                pass
            return

        try:
            # Store ONLY the short refresh token in OS Keychain
            # ?(bypasses Windows 512-byte limit)
            if self.current_session.refresh_token:
                keyring.set_password(
                    KEYRING_SERVICE_NAME,
                    KEYRING_ACCOUNT_NAME,
                    self.current_session.refresh_token,
                )

            # Ensure parent directory exists before writing
            self._session_path.parent.mkdir(parents=True, exist_ok=True)

            # Store non-sensitive metadata on disk
            metadata_payload: dict[str, Any] = {
                "expires_at": self.current_session.expires_at,
                "user": asdict(self.current_session.user),
            }
            self._session_path.write_text(
                json.dumps(metadata_payload, indent=2), encoding="utf-8"
            )
        except Exception as e:
            err_msg: str = f"Failed to save auth session: {e}"
            logger.error(err_msg)
            print(err_msg)

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
                
        except urllib.error.HTTPError as err:
            # 400 / 401: Refresh token invalid or revoked -> perform full logout
            if err.code in (400, 401):
                err_msg: str = "Refresh token expired or revoked. Logging out user."
                logger.warning(err_msg)
                print(err_msg)
                self.current_session = None
                self.save()
            else:
                self.is_offline = True
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            # Network connection error -> retain session for offline mode
            err_msg: str = f"Network unavailable during token refresh ({err}). Operating offline."
            logger.info(err_msg)
            print(err_msg)
            self.is_offline = True
        except Exception as e:
            err_msg: str = f"Unexpected error during refresh: {e}"
            logger.error(err_msg)
            print(err_msg)
            self.is_offline = True
            
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
        user_email: str = user_data.get("email", "creator@pytoningans.local")
        user_name: str = user_data.get("username", "Modder")
        user_gh = user_data.get("github_username")
        user_goog = user_data.get("google_email")
        user_prov = user_data.get("primary_provider", "email")
        user_provs: list[str] = list(user_data.get("providers", []))
        user_provs, user_prov, user_gh, user_goog = self._resolve_providers(
            user_data, user_provs, user_prov, user_gh, user_goog, user_name
        )
        user_cust = self._resolve_custom_avatar(user_data)
        is_dev, badges = self._resolve_developer_and_badges(user_data, user_name, user_gh, user_provs)

        return UserProfile(
            id=user_data.get("id", "local_user"),
            email=user_email,
            username=user_name,
            created_at=user_data.get("created_at", ""),
            avatar_url=user_data.get("avatar_url"),
            custom_avatar_path=user_cust,
            bio=user_data.get("bio", ""),
            primary_provider=user_prov,
            providers=user_provs,
            github_username=user_gh,
            google_email=user_goog,
            email_verified=user_data.get("email_verified", False),
            is_developer=is_dev,
            badges=badges,
        )

    @staticmethod
    def _resolve_providers(
        user_data: dict[str, Any],
        user_provs: list[str],
        user_prov: str,
        user_gh: Optional[str],
        user_goog: Optional[str],
        user_name: str,
    ) -> tuple[list[str], str, Optional[str], Optional[str]]:
        """
        Applies backward-compatible provider list deduction and fills in
        github_username / google_email from context where missing.
        """
        if not user_provs and user_prov:
            user_provs = [user_prov]

        avatar_url_str: str = str(user_data.get("avatar_url", "")).lower()

        if (
            avatar_url_str and
            "github" in avatar_url_str or
            user_gh is not None or
            user_prov == "github" or
            "github" in user_provs
        ):
            if "github" not in user_provs:
                user_provs.append("github")
            user_prov = "github"
            if not user_gh and "github" in user_provs:
                user_gh = user_name

        if "google" in avatar_url_str or user_prov == "google":
            if "google" not in user_provs:
                user_provs.append("google")
        if "google" not in user_provs and user_prov != "google":
            user_goog = None

        return user_provs, user_prov, user_gh, user_goog

    @staticmethod
    def _resolve_custom_avatar(user_data: dict[str, Any]) -> Optional[str]:
        """Returns a valid custom avatar path from session data or SettingsManager fallback."""
        user_avatar: Optional[str] = user_data.get("custom_avatar_path")
        if user_avatar is None:
            try:
                settings_avatar: str = SettingsManager.get().settings.creator_avatar_path
                if settings_avatar and Path(settings_avatar).is_file():
                    user_avatar = settings_avatar
            except Exception:
                pass
        return user_avatar or None

    @staticmethod
    def _resolve_developer_and_badges(
        user_data: dict[str, Any],
        username: str,
        github_username: Optional[str],
        providers: list[str],
    ) -> tuple[bool, list[str]]:
        """Resolves developer status and assembles the badge list for the user."""
        is_dev: Optional[bool] = user_data.get("is_developer")
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

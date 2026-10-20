"""
PyToNingans Mod Browser - Supabase Authentication and Session Manager
===================================================================
Provides user account management, secure session persistence, in-app Email/Password
authentication, and Google OAuth via system browser redirect and local callback server.
Offline-first: Gracefully supports local offline accounts when cloud is disconnected.
"""
from __future__ import annotations

import json, os, threading, time
import urllib.error, urllib.parse, urllib.request
import webbrowser, http.server
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal

from pytoningans.utils.paths import get_settings_path, get_base_path, get_app_version
from pytoningans.core.settings import SettingsManager
from .oauth_handler import OAuthCallbackServer, OAuthCallbackHandler


# TODO: Update `is_known_developer()` to just use a hidden column in database
def is_known_developer(
    email: str = "", username: str = "",
    github_username: Optional[str] = None
) -> bool:
    """
    Returns True if the user account is recognized as an 
    _official_ **PyToNingans** core developer.
    """
    clean_email: str = email.strip().lower()
    clean_user: str = username.strip().lower()
    clean_gh: str = (github_username or "").strip().lower()

    if clean_email in ("andredcxxv@gmail.com",):
        return True
    if clean_user in ("meta-dusk", "andredcxxv"):
        return True
    if clean_gh in ("meta-dusk", "andredcxxv"):
        return True
    return False


@dataclass
class UserProfile:
    """Represents a signed-in community creator account."""
    id: str
    email: str
    username: str
    created_at: str = ""
    avatar_url: Optional[str] = None
    custom_avatar_path: Optional[str] = None
    bio: str = ""
    primary_provider: str = "email"
    providers: list[str] = field(default_factory=list)
    github_username: Optional[str] = None
    google_email: Optional[str] = None
    email_verified: bool = False
    is_developer: bool = False
    badges: list[str] = field(default_factory=list)

    @property
    def display_provider(self) -> str:
        """Returns human-readable primary provider label."""
        provider: str = self.primary_provider.lower()
        if provider == "github":
            return "GitHub"
        elif provider == "google":
            return "Google"
        elif provider == "email":
            return "Email / Password"
        elif provider == "local":
            return "Offline Local"
        return provider.capitalize()


@dataclass
class AuthSession:
    """Represents persistent session tokens and user state."""
    access_token: str
    refresh_token: str
    user: UserProfile
    expires_at: float = 0.0


class AuthManager(QObject):
    """
    Manages user authentication against Supabase Auth (or offline local storage).
    Emits auth_state_changed whenever sign-in, sign-up, or sign-out occurs.
    """

    auth_state_changed = Signal(object)
    """Optional[UserProfile]"""

    _instance: Optional[AuthManager] = None

    def __init__(self) -> None:
        super().__init__()
        self._config_path: Path = get_settings_path().parent / "supabase_config.json"
        self._session_path: Path = get_settings_path().parent / "auth_session.json"

        self.supabase_url: str = os.environ.get("SUPABASE_URL", "")
        self.supabase_pub_key: str = os.environ.get("SUPABASE_ANON_KEY", "")

        self._current_session: Optional[AuthSession] = None
        self._oauth_server: Optional[http.server.HTTPServer] = None
        self._oauth_thread: Optional[threading.Thread] = None

        self._load_config()
        self._load_session()

    @classmethod
    def get(cls) -> AuthManager:
        if cls._instance is None:
            cls._instance = AuthManager()
        return cls._instance

    @property
    def current_user(self) -> Optional[UserProfile]:
        return self._current_session.user if self._current_session is not None else None

    @property
    def is_authenticated(self) -> bool:
        return self._current_session is not None

    @property
    def is_cloud_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_pub_key)

    @property
    def supabase_anon_key(self) -> str:
        return self.supabase_pub_key

    def _read_env_file(self, env_path: Path) -> dict[str, str]:
        """Simple, dependency-free key=value parser for local .env files."""
        results: dict[str, str] = {}
        if not env_path.is_file():
            return results
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line: str = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                results[k.strip()] = v.strip().strip("'\"")
        except Exception:
            pass
        return results

    def _load_config(self) -> None:
        """
        Loads Supabase configuration in hierarchical priority:
        1. Bundled cloud_config.json in application folder (packaged by installer)
        2. Local .env file in project root (for developer convenience)
        3. OS environment variables (SUPABASE_URL, SUPABASE_ANON_KEY)
        4. User documents override (if customized via Advanced Server settings)
        """
        # 1. Bundled cloud_config.json
        bundled_config = get_base_path() / "cloud_config.json"
        if bundled_config.is_file():
            try:
                b_data = json.loads(bundled_config.read_text(encoding="utf-8"))
                self.supabase_url = b_data.get("supabase_url", self.supabase_url)
                self.supabase_pub_key = b_data.get("supabase_anon_key", self.supabase_pub_key)
            except Exception:
                pass

        # 2. Local .env file
        env_vars = self._read_env_file(get_base_path() / ".env")
        if "SUPABASE_URL" in env_vars:
            self.supabase_url = env_vars["SUPABASE_URL"]
        if "SUPABASE_ANON_KEY" in env_vars:
            self.supabase_pub_key = env_vars["SUPABASE_ANON_KEY"]

        # 3. Environment variables
        self.supabase_url = os.environ.get("SUPABASE_URL", self.supabase_url)
        self.supabase_pub_key = os.environ.get("SUPABASE_ANON_KEY", self.supabase_pub_key)

        # 4. User documents override
        if not self._config_path.is_file(): return
        try:
            data: dict[str, Any] = json.loads(self._config_path.read_text(encoding="utf-8"))
            self.supabase_url = data.get("supabase_url", self.supabase_url)
            self.supabase_pub_key = data.get("supabase_anon_key", self.supabase_pub_key)
        except Exception:
            pass

    def save_config(self, url: str, anon_key: str) -> None:
        self.supabase_url = url.strip()
        self.supabase_pub_key = anon_key.strip()
        try:
            payload: dict[str, str] = {
                "supabase_url": self.supabase_url,
                "supabase_anon_key": self.supabase_pub_key,
            }
            self._config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_session(self) -> None:
        if not self._session_path.exists():
            return
        try:
            data: dict[str, Any] = json.loads(self._session_path.read_text(encoding="utf-8"))
            user_data: dict[str, Any] = data.get("user", {})
            u_email: str = user_data.get("email", "creator@pytoningans.local")
            u_name: str = user_data.get("username", "Modder")
            u_gh = user_data.get("github_username")
            u_goog = user_data.get("google_email")
            u_prov = user_data.get("primary_provider", "email")
            u_provs: list[str] = list(user_data.get("providers", []))

            # Backward compatibility deduction
            if not u_provs and u_prov:
                u_provs = [u_prov]
            if "github" in str(user_data.get("avatar_url", "")).lower() or u_gh or u_name == "Meta-Dusk":
                if "github" not in u_provs:
                    u_provs.append("github")
                u_prov = "github"
                if not u_gh:
                    u_gh = "Meta-Dusk" if u_name == "Meta-Dusk" else None

            if "google" in str(user_data.get("avatar_url", "")).lower() or u_goog or u_email.endswith("@gmail.com"):
                if not u_goog and u_email.endswith("@gmail.com"):
                    u_goog = u_email
                if "google" not in u_provs and "google" in str(user_data.get("avatar_url", "")).lower():
                    u_provs.append("google")

            u_cust = user_data.get("custom_avatar_path")
            if not u_cust:
                try:
                    s_cust = SettingsManager.get().settings.creator_avatar_path
                    if s_cust and Path(s_cust).is_file():
                        u_cust = s_cust
                except Exception:
                    pass

            is_dev = user_data.get("is_developer")
            if is_dev is None:
                is_dev = is_known_developer(u_email, u_name, u_gh)

            badges: list[str] = list(user_data.get("badges", []))
            if is_dev and "Developer" not in badges:
                badges.insert(0, "Developer")
            if (
                ("github" in u_provs or "google" in u_provs) and
                "Verified Creator" not in badges and
                not str(user_data.get("id", "")).startswith("local_")
            ):
                badges.append("Verified Creator")
            if (
                str(user_data.get("id", "")).startswith("local_") and
                "Offline Creator" not in badges
            ):
                badges.append("Offline Creator")

            user = UserProfile(
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
            self._current_session = AuthSession(
                access_token=data.get("access_token", ""),
                refresh_token=data.get("refresh_token", ""),
                user=user,
                expires_at=data.get("expires_at", 0.0),
            )
            if self._current_session.access_token and self._current_session.access_token != "mock_local_token":
                if time.time() >= self._current_session.expires_at - 120:
                    threading.Thread(target=self.refresh_session, daemon=True).start()
        except Exception:
            self._current_session = None

    def _save_session(self) -> None:
        if self._current_session is None:
            if self._session_path.exists():
                try:
                    self._session_path.unlink()
                except Exception:
                    pass
            return

        try:
            payload: dict[str, Any] = {
                "access_token": self._current_session.access_token,
                "refresh_token": self._current_session.refresh_token,
                "expires_at": self._current_session.expires_at,
                "user": asdict(self._current_session.user),
            }
            self._session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def refresh_session(self) -> bool:
        """
        Refreshes access_token using current refresh_token against Supabase Auth.
        Returns True if session was successfully refreshed, False otherwise.
        """
        if (
            self._current_session is None
            or not self.is_cloud_configured
            or not self._current_session.refresh_token
            or self._current_session.refresh_token == "mock_refresh_token"
        ):
            return False

        endpoint: str = f"{self.supabase_url.rstrip('/')}/auth/v1/token?grant_type=refresh_token"
        payload: bytes = json.dumps({
            "refresh_token": self._current_session.refresh_token
        }).encode("utf-8")
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "apikey": self.supabase_pub_key,
            "User-Agent": f"PyToNingans/{get_app_version()}",
        }
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
                new_access_token: str = data.get("access_token", "")
                new_refresh_token: str = data.get("refresh_token", self._current_session.refresh_token)
                expires_in: int = int(data.get("expires_in", 3600))
                if new_access_token:
                    self._current_session.access_token = new_access_token
                    self._current_session.refresh_token = new_refresh_token
                    self._current_session.expires_at = time.time() + expires_in
                    self._save_session()
                    return True
        except Exception:
            pass
        return False

    def ensure_valid_session(self) -> bool:
        """
        Proactively refreshes active session if access_token has expired or will expire within 60s.
        """
        if (
            self._current_session is None
            or self._current_session.access_token == "mock_local_token"
            or not self.is_cloud_configured
        ):
            return True

        if time.time() >= self._current_session.expires_at - 60:
            return self.refresh_session()
        return True

    def sign_out(self) -> None:
        """Clears local authentication session, notifies cloud if connected, and notifies listeners."""
        if (
            self.is_cloud_configured
            and self._current_session
            and self._current_session.access_token
            and self._current_session.access_token != "mock_local_token"
        ):
            try:
                logout_endpoint: str = f"{self.supabase_url.rstrip('/')}/auth/v1/logout"
                logout_req = urllib.request.Request(
                    logout_endpoint,
                    data=b"{}",
                    headers={
                        "Content-Type": "application/json",
                        "apikey": self.supabase_pub_key,
                        "Authorization": f"Bearer {self._current_session.access_token}",
                        "User-Agent": f"PyToNingans/{get_app_version()}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(logout_req, timeout=3) as _:
                    pass
            except Exception:
                pass

        self._current_session = None
        self._save_session()
        self.auth_state_changed.emit(None)
        
    def get_creator_name(self) -> str:
        """
        Returns active creator name from current session or app settings,
        fallback to 'Modder'.
        """
        if (
            self._current_session is not None and
            self._current_session.user is not None and
            self._current_session.user.username
        ):
            return self._current_session.user.username
        try:
            saved: str = SettingsManager.get().settings.creator_name.strip()
            if saved:
                return saved
        except Exception:
            pass
        return "Modder"

    def get_creator_bio(self) -> str:
        """Returns creator bio from session or settings."""
        if (
            self._current_session is not None and
            self._current_session.user is not None and
            self._current_session.user.bio
        ):
            return self._current_session.user.bio
        try:
            return SettingsManager.get().settings.creator_bio.strip()
        except Exception:
            return ""

    def get_creator_avatar(self) -> Optional[str]:
        """Returns the active avatar source (custom avatar file path or cloud avatar URL)."""
        if self._current_session and self._current_session.user:
            avatar_path: Optional[str] = self._current_session.user.custom_avatar_path
            if avatar_path and Path(avatar_path).is_file():
                return avatar_path
            if self._current_session.user.avatar_url:
                return self._current_session.user.avatar_url

        try:
            saved_avatar: str = SettingsManager.get().settings.creator_avatar_path.strip()
            if saved_avatar and Path(saved_avatar).is_file():
                return saved_avatar
        except Exception:
            pass
        return None

    def update_profile(
        self,
        new_username: str,
        bio: str = "",
        avatar_url: Optional[str] = None,
        custom_avatar_path: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Updates the active creator's username, bio, and custom avatar.
        Persists locally in session and AppSettings, and syncs to Supabase Cloud if authenticated.
        """
        clean_name: str = new_username.strip().replace(" ", "_")
        if not clean_name:
            return False, "Creator name cannot be empty."

        try:
            SettingsManager.get().update_settings(
                creator_name=clean_name,
                creator_bio=bio.strip(),
                creator_avatar_path=(
                    custom_avatar_path.strip() if
                    custom_avatar_path is not None else None
                )
            )
        except Exception:
            pass

        if self._current_session is not None:
            self._current_session.user.username = clean_name
            self._current_session.user.bio = bio.strip()
            if avatar_url is not None:
                self._current_session.user.avatar_url = avatar_url
            if custom_avatar_path is not None:
                self._current_session.user.custom_avatar_path = custom_avatar_path.strip()

            # Recompute developer & badges
            is_dev: bool = is_known_developer(
                self._current_session.user.email,
                clean_name,
                self._current_session.user.github_username,
            )
            self._current_session.user.is_developer = is_dev
            if is_dev and "Developer" not in self._current_session.user.badges:
                self._current_session.user.badges.insert(0, "Developer")
            self._save_session()
        else:
            self.sign_in_locally(clean_name)
            if self._current_session is not None:
                self._current_session.user.bio = bio.strip()
                if custom_avatar_path is not None:
                    self._current_session.user.custom_avatar_path = custom_avatar_path.strip()
                self._save_session()

        # If connected to cloud with an active token, update user metadata in Supabase
        if (
            self.is_authenticated
            and self.is_cloud_configured
            and self._current_session
            and self._current_session.access_token != "mock_local_token"
        ):
            try:
                self._sync_profile_to_cloud(clean_name, bio.strip())
            except Exception as e:
                print(f"Notice: Cloud profile sync warning: {e}")

        self.auth_state_changed.emit(self.current_user)
        return True, f"Profile updated! Creator handle set to '{clean_name}'."

    def _sync_profile_to_cloud(self, username: str, bio: str) -> None:
        """Synchronizes username and bio to Supabase user_metadata via Auth REST API."""
        if not self._current_session or not self.is_cloud_configured:
            return

        self.ensure_valid_session()

        endpoint: str = f"{self.supabase_url.rstrip('/')}/auth/v1/user"
        payload: bytes = json.dumps({
            "data": {"username": username, "bio": bio}
        }).encode("utf-8")
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "apikey": self.supabase_pub_key,
            "Authorization": f"Bearer {self._current_session.access_token}",
            "User-Agent": f"PyToNingans/{get_app_version()}",
        }
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                pass
        except urllib.error.HTTPError as e:
            # If 401/403 (e.g. token expired), attempt auto-refresh and retry once
            if e.code in (401, 403) and self.refresh_session():
                headers["Authorization"] = f"Bearer {self._current_session.access_token}"
                retry_req = urllib.request.Request(endpoint, data=payload, headers=headers, method="PUT")
                with urllib.request.urlopen(retry_req, timeout=8) as retry_resp:
                    pass
                return
            raise

    def sign_in_locally(self, username: str = "LocalCreator") -> UserProfile:
        """Sets up a local creator session for offline-first modding without cloud connection."""
        clean_name: str = username.strip().replace(" ", "_") or "LocalCreator"
        is_dev = is_known_developer("", clean_name, None)
        badges = ["Developer"] if is_dev else ["Offline Creator"]
        custom_avatar = ""
        try:
            custom_avatar = SettingsManager.get().settings.creator_avatar_path
        except Exception:
            pass

        user = UserProfile(
            id=f"local_{clean_name}",
            email=f"{clean_name.lower()}@pytoningans.local",
            username=clean_name,
            created_at=time.strftime("%Y-%m-%d"),
            custom_avatar_path=custom_avatar or None,
            primary_provider="local",
            providers=["local"],
            is_developer=is_dev,
            badges=badges,
        )
        self._current_session = AuthSession(
            access_token="mock_local_token",
            refresh_token="mock_refresh_token",
            user=user,
            expires_at=time.time() + 86400 * 365,
        )
        self._save_session()
        self.auth_state_changed.emit(user)
        return user

    def sign_in_with_password(
        self, email: str, password: str
    ) -> tuple[bool, str, Optional[UserProfile]]:

        """Signs in with email and password via Supabase Auth REST or local offline account."""
        email = email.strip()
        if not email or not password:
            return False, "Email and password are required.", None

        if not self.is_cloud_configured:
            # Offline/Local Mode fallback: allow local sign-in
            username: str = email.split("@")[0].replace(".", "_")
            is_dev = is_known_developer(email, username, None)
            badges = ["Developer"] if is_dev else ["Offline Creator"]
            user = UserProfile(
                id=f"local_{username}",
                email=email,
                username=username,
                created_at=time.strftime("%Y-%m-%d"),
                primary_provider="local",
                providers=["local"],
                is_developer=is_dev,
                badges=badges,
            )
            self._current_session = AuthSession(
                access_token="mock_local_token",
                refresh_token="mock_refresh_token",
                user=user,
                expires_at=time.time() + 86400 * 30,
            )
            self._save_session()
            self.auth_state_changed.emit(user)
            return True, f"Signed in locally as {username} (Offline Mode).", user

        endpoint: str = f"{self.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password"
        payload: bytes = json.dumps({"email": email, "password": password}).encode("utf-8")
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "apikey": self.supabase_pub_key,
        }

        request = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                response_data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
                user_obj: dict[str, Any] = response_data.get("user", {})
                meta: dict[str, Any] = user_obj.get("user_metadata", {})
                username: str = meta.get("username") or email.split("@")[0]

                is_dev: bool = is_known_developer(user_obj.get("email", email), username, None)
                badges: list[str] = ["Developer", "Verified Creator"] if is_dev else ["Verified Creator"]

                user = UserProfile(
                    id=user_obj.get("id", ""),
                    email=user_obj.get("email", email),
                    username=username,
                    created_at=user_obj.get("created_at", ""),
                    avatar_url=meta.get("avatar_url"),
                    primary_provider="email",
                    providers=["email"],
                    email_verified=meta.get("email_verified", False),
                    is_developer=is_dev,
                    badges=badges,
                )
                self._current_session = AuthSession(
                    access_token=response_data.get("access_token", ""),
                    refresh_token=response_data.get("refresh_token", ""),
                    user=user,
                    expires_at=time.time() + response_data.get("expires_in", 3600),
                )
                self._save_session()
                self.auth_state_changed.emit(user)
                return True, f"Welcome back, {username}!", user
        except urllib.error.HTTPError as e:
            try:
                err_data: dict[str, str] = json.loads(e.read().decode("utf-8"))
                msg: str = err_data.get("error_description") or err_data.get("msg") or str(e)
            except Exception:
                msg: str = f"HTTP Error {e.code}"
            return False, f"Sign in failed: {msg}", None
        except Exception as e:
            return False, f"Connection error: {e}", None

    def sign_up(
        self, email: str, password: str, username: str
    ) -> tuple[bool, str, Optional[UserProfile]]:
        """Registers a new creator account with email, password, and chosen username."""
        email = email.strip()
        username = username.strip().replace(" ", "_")
        if not email or not password or not username:
            return False, "Username, email, and password are required.", None

        if len(password) < 6:
            return False, "Password must be at least 6 characters long.", None

        if not self.is_cloud_configured:
            # Offline/Local Mode registration
            is_dev: bool = is_known_developer(email, username, None)
            badges = ["Developer"] if is_dev else ["Offline Creator"]
            user = UserProfile(
                id=f"local_{username}",
                email=email,
                username=username,
                created_at=time.strftime("%Y-%m-%d"),
                primary_provider="local",
                providers=["local"],
                is_developer=is_dev,
                badges=badges,
            )
            self._current_session = AuthSession(
                access_token="mock_local_token",
                refresh_token="mock_refresh_token",
                user=user,
                expires_at=time.time() + 86400 * 30,
            )
            self._save_session()
            self.auth_state_changed.emit(user)
            return True, f"Account '{username}' created in Offline Mode!", user

        endpoint: str = f"{self.supabase_url.rstrip('/')}/auth/v1/signup"
        payload: bytes = json.dumps({
            "email": email,
            "password": password,
            "data": {"username": username},
        }).encode("utf-8")
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "apikey": self.supabase_pub_key,
        }

        request = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                response_data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
                user_obj: dict[str, Any] = response_data.get("user", {}) or response_data
                meta: dict[str, Any] = user_obj.get("user_metadata", {})
                confirmed_username: str = meta.get("username", username)

                is_dev: bool = is_known_developer(user_obj.get("email", email), confirmed_username, None)
                badges: list[str] = ["Developer", "Verified Creator"] if is_dev else ["Verified Creator"]

                user = UserProfile(
                    id=user_obj.get("id", ""),
                    email=user_obj.get("email", email),
                    username=confirmed_username,
                    created_at=user_obj.get("created_at", ""),
                    primary_provider="email",
                    providers=["email"],
                    is_developer=is_dev,
                    badges=badges,
                )

                # Supabase may return session immediately or require email confirmation
                if "access_token" in response_data:
                    self._current_session = AuthSession(
                        access_token=response_data.get("access_token", ""),
                        refresh_token=response_data.get("refresh_token", ""),
                        user=user,
                        expires_at=time.time() + response_data.get("expires_in", 3600),
                    )
                    self._save_session()
                    self.auth_state_changed.emit(user)
                    return True, f"Account '{confirmed_username}' registered and signed in!", user
                else:
                    return True, "Registration successful! Please check your email for confirmation.", user
        except urllib.error.HTTPError as e:
            try:
                err_data: dict[str, str] = json.loads(e.read().decode("utf-8"))
                msg: str = err_data.get("msg") or err_data.get("error_description") or str(e)
            except Exception:
                msg: str = f"HTTP Error {e.code}"
            return False, f"Registration failed: {msg}", None
        except Exception as e:
            return False, f"Connection error: {e}", None

    def start_oauth(self, provider: str = "google", callback_port: int = 54321) -> tuple[bool, str]:
        """
        Launches OAuth (e.g. Google, GitHub) in the user's default browser with a
        temporary local redirect listener.
        Offline-first: Provides a mock creator profile when cloud is not configured.
        """
        prov_key: str = provider.lower()
        prov_name: str = "GitHub" if prov_key == "github" else provider.capitalize()

        if not self.is_cloud_configured:
            # Offline mock sign-in
            mock_id: str = f"{prov_key}_offline_user"
            mock_email: str = "user@gmail.com" if prov_key == "google" else f"creator@{prov_key}.local"
            mock_username: str = f"{prov_name}Creator"
            is_dev = is_known_developer(mock_email, mock_username, None)
            badges = ["Developer"] if is_dev else ["Offline Creator"]
            user = UserProfile(
                id=mock_id,
                email=mock_email,
                username=mock_username,
                created_at=time.strftime("%Y-%m-%d"),
                primary_provider=prov_key,
                providers=[prov_key],
                is_developer=is_dev,
                badges=badges,
            )
            self._current_session = AuthSession(
                access_token=f"mock_{prov_key}_token",
                refresh_token=f"mock_{prov_key}_refresh",
                user=user,
                expires_at=time.time() + 86400 * 30,
            )
            self._save_session()
            self.auth_state_changed.emit(user)
            return True, f"Signed in with {prov_name} (Offline Mode) as '{mock_username}'."

        redirect_uri: str = f"http://127.0.0.1:{callback_port}/callback"
        auth_url: str = (
            f"{self.supabase_url.rstrip('/')}/auth/v1/authorize?"
            f"provider={prov_key}&redirect_to={urllib.parse.quote(redirect_uri)}"
        )

        try:
            server = OAuthCallbackServer(
                ("127.0.0.1", callback_port),
                OAuthCallbackHandler,
                token_callback=self._handle_oauth_tokens,
            )
            self._oauth_server = server

            def serve() -> None:
                try:
                    server.handle_request()
                    server.handle_request()
                except Exception:
                    pass
                finally:
                    server.server_close()

            thread = threading.Thread(target=serve, daemon=True)
            self._oauth_thread = thread
            thread.start()

            webbrowser.open(auth_url)
            return True, f"Opened {prov_name} sign-in page in your browser..."
        except Exception as e:
            return False, f"Failed to start OAuth redirect listener: {e}"

    def start_google_oauth(self, callback_port: int = 54321) -> tuple[bool, str]:
        """Launches Google OAuth in the user's default browser."""
        return self.start_oauth("google", callback_port)

    def start_github_oauth(self, callback_port: int = 54321) -> tuple[bool, str]:
        """Launches GitHub OAuth in the user's default browser."""
        return self.start_oauth("github", callback_port)

    def _handle_oauth_tokens(self, access_token: str, refresh_token: str) -> None:
        """
        Queries user profile using the captured access token and activates the session.
        Applies creator identity separation and multi-provider inheritance:
        - First provider login sets default username and avatar.
        - Subsequent provider logins link to the profile without overriding custom creator details.
        """
        try:
            endpoint: str = f"{self.supabase_url.rstrip('/')}/auth/v1/user"
            headers: dict[str, str] = {
                "Authorization": f"Bearer {access_token}",
                "apikey": self.supabase_pub_key,
            }
            request = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
                app_meta: dict[str, Any] = data.get("app_metadata", {})
                meta: dict[str, Any] = data.get("user_metadata", {})
                identities: list[dict[str, Any]] = data.get("identities", [])

                prov_key: str = (app_meta.get("provider") or "").lower() or "oauth"
                incoming_providers: list[str] = [p.lower() for p in app_meta.get("providers", [])]
                if prov_key and prov_key not in incoming_providers:
                    incoming_providers.append(prov_key)

                # Scan identities to uncover all connected providers
                for identity in identities:
                    id_prov = (identity.get("provider") or "").lower()
                    if id_prov and id_prov not in incoming_providers:
                        incoming_providers.append(id_prov)

                # Extract GitHub username
                github_username: Optional[str] = None
                for identity in identities:
                    if identity.get("provider") == "github":
                        id_data = identity.get("identity_data", {})
                        github_username = id_data.get("user_name") or id_data.get("preferred_username")
                        break
                if not github_username and ("github" in incoming_providers or prov_key == "github"):
                    github_username = meta.get("user_name") or meta.get("preferred_username")

                # Extract Google email
                google_email: Optional[str] = None
                for identity in identities:
                    if identity.get("provider") == "google":
                        id_data = identity.get("identity_data", {})
                        google_email = id_data.get("email")
                        break
                if not google_email and ("google" in incoming_providers or prov_key == "google"):
                    google_email = data.get("email")

                email_verified: bool = (
                    bool(meta.get("email_verified")) or
                    bool(data.get("email_confirmed_at")) or
                    prov_key in ("google", "github")
                )
                avatar_url: Optional[str] = meta.get("avatar_url")

                # Multi-provider inheritance: Preserve customized profile if one already exists
                existing_handle: str = ""
                existing_bio: str = ""
                existing_custom_avatar: str = ""
                existing_providers: list[str] = []

                if (
                    self._current_session and
                    self._current_session.user and
                    not self._current_session.user.id.startswith("local_")
                ):
                    existing_handle = self._current_session.user.username
                    existing_bio = self._current_session.user.bio
                    existing_custom_avatar = self._current_session.user.custom_avatar_path or ""
                    existing_providers = list(self._current_session.user.providers)
                    if not github_username:
                        github_username = self._current_session.user.github_username
                    if not google_email:
                        google_email = self._current_session.user.google_email
                    if not avatar_url:
                        avatar_url = self._current_session.user.avatar_url
                else:
                    try:
                        saved_name = SettingsManager.get().settings.creator_name.strip()
                        if saved_name and saved_name != "Modder":
                            existing_handle = saved_name
                        saved_avatar = SettingsManager.get().settings.creator_avatar_path.strip()
                        if saved_avatar and Path(saved_avatar).is_file():
                            existing_custom_avatar = saved_avatar
                        existing_bio = SettingsManager.get().settings.creator_bio.strip()
                    except Exception:
                        pass

                # Determine creator handle
                if existing_handle:
                    chosen_username = existing_handle
                elif meta.get("username"):
                    chosen_username = str(meta.get("username")).replace(" ", "_")
                else:
                    # First-time login: inherit details from OAuth provider
                    raw_provider_name = (
                        github_username or
                        meta.get("user_name") or
                        meta.get("preferred_username") or
                        meta.get("full_name") or
                        meta.get("name") or
                        data.get("email", "").split("@")[0]
                    )
                    chosen_username = raw_provider_name.replace(" ", "_")
                    try:
                        SettingsManager.get().update_settings(creator_name=chosen_username)
                    except Exception:
                        pass

                # Combine provider records
                merged_providers = list(dict.fromkeys(existing_providers + incoming_providers))

                # Identify developer status
                is_dev: bool = is_known_developer(data.get("email", ""), chosen_username, github_username)
                badges: list[str] = []
                if is_dev:
                    badges.append("Developer")
                if "github" in merged_providers or "google" in merged_providers or email_verified:
                    badges.append("Verified Creator")

                user = UserProfile(
                    id=data.get("id", ""),
                    email=data.get("email", ""),
                    username=chosen_username,
                    created_at=data.get("created_at", ""),
                    avatar_url=avatar_url,
                    custom_avatar_path=existing_custom_avatar or None,
                    bio=existing_bio or meta.get("bio", ""),
                    primary_provider=prov_key,
                    providers=merged_providers,
                    github_username=github_username,
                    google_email=google_email,
                    email_verified=email_verified,
                    is_developer=is_dev,
                    badges=badges,
                )

                self._current_session = AuthSession(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    user=user,
                    expires_at=time.time() + 3600,
                )
                self._save_session()
                self.auth_state_changed.emit(user)
        except Exception:
            pass


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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal

from pytoningans.utils.paths import get_settings_path, get_base_path, get_app_version
from pytoningans.core.settings import SettingsManager
from .oauth_handler import OAuthCallbackServer, OAuthCallbackHandler


@dataclass
class UserProfile:
    """Represents a signed-in community creator account."""
    id: str
    email: str
    username: str
    created_at: str = ""
    avatar_url: Optional[str] = None
    bio: str = ""


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
            user_data: dict[str, str] = data.get("user", {})
            user = UserProfile(
                id=user_data.get("id", "local_user"),
                email=user_data.get("email", "creator@pytoningans.local"),
                username=user_data.get("username", "Modder"),
                created_at=user_data.get("created_at", ""),
                avatar_url=user_data.get("avatar_url"),
                bio=user_data.get("bio", ""),
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

    def update_profile(
        self, new_username: str, bio: str = "", avatar_url: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Updates the active creator's username, bio, and avatar.
        Persists locally in session and AppSettings, and syncs to Supabase Cloud if authenticated.
        """
        clean_name: str = new_username.strip().replace(" ", "_")
        if not clean_name:
            return False, "Creator name cannot be empty."

        try:
            SettingsManager.get().update_settings(
                creator_name=clean_name, creator_bio=bio.strip()
            )
        except Exception:
            pass

        if self._current_session is not None:
            self._current_session.user.username = clean_name
            self._current_session.user.bio = bio.strip()
            if avatar_url:
                self._current_session.user.avatar_url = avatar_url
            self._save_session()
        else:
            self.sign_in_locally(clean_name)
            if bio and self._current_session is not None:
                self._current_session.user.bio = bio.strip()
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
        return True, f"Profile updated! Creator name set to '{clean_name}'."

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
        user = UserProfile(
            id=f"local_{clean_name}",
            email=f"{clean_name.lower()}@pytoningans.local",
            username=clean_name,
            created_at=time.strftime("%Y-%m-%d"),
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
            user = UserProfile(
                id=f"local_{username}",
                email=email,
                username=username,
                created_at=time.strftime("%Y-%m-%d"),
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

                user = UserProfile(
                    id=user_obj.get("id", ""),
                    email=user_obj.get("email", email),
                    username=username,
                    created_at=user_obj.get("created_at", ""),
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
            user = UserProfile(
                id=f"local_{username}",
                email=email,
                username=username,
                created_at=time.strftime("%Y-%m-%d"),
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

                user = UserProfile(
                    id=user_obj.get("id", ""),
                    email=user_obj.get("email", email),
                    username=confirmed_username,
                    created_at=user_obj.get("created_at", ""),
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
            user = UserProfile(
                id=mock_id,
                email=mock_email,
                username=mock_username,
                created_at=time.strftime("%Y-%m-%d"),
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
        """Queries user profile using the captured access token and activates the session."""
        try:
            endpoint: str = f"{self.supabase_url.rstrip('/')}/auth/v1/user"
            headers: dict[str, str] = {
                "Authorization": f"Bearer {access_token}",
                "apikey": self.supabase_pub_key,
            }
            request = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
                meta: dict[str, Any] = data.get("user_metadata", {})
                username: str = (
                    meta.get("user_name") or
                    meta.get("preferred_username") or
                    meta.get("full_name") or
                    meta.get("name") or
                    data.get("email", "").split("@")[0]
                )
                username = username.replace(" ", "_")

                user = UserProfile(
                    id=data.get("id", ""),
                    email=data.get("email", ""),
                    username=username,
                    created_at=data.get("created_at", ""),
                    avatar_url=meta.get("avatar_url"),
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


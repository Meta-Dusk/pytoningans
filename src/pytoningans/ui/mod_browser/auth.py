"""
PyToNingans Mod Browser - Supabase Authentication & Session Manager
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

from pytoningans.utils.paths import get_settings_path, get_base_path
from .oauth_handler import OAuthCallbackServer, OAuthCallbackHandler


@dataclass
class UserProfile:
    """Represents a signed-in community creator account."""
    id: str
    email: str
    username: str
    created_at: str = ""
    avatar_url: Optional[str] = None


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
        self.supabase_anon_key: str = os.environ.get("SUPABASE_ANON_KEY", "")

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
        return bool(self.supabase_url and self.supabase_anon_key)

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
                self.supabase_anon_key = b_data.get("supabase_anon_key", self.supabase_anon_key)
            except Exception:
                pass

        # 2. Local .env file
        env_vars = self._read_env_file(get_base_path() / ".env")
        if "SUPABASE_URL" in env_vars:
            self.supabase_url = env_vars["SUPABASE_URL"]
        if "SUPABASE_ANON_KEY" in env_vars:
            self.supabase_anon_key = env_vars["SUPABASE_ANON_KEY"]

        # 3. Environment variables
        self.supabase_url = os.environ.get("SUPABASE_URL", self.supabase_url)
        self.supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY", self.supabase_anon_key)

        # 4. User documents override
        if not self._config_path.is_file(): return
        try:
            data: dict[str, Any] = json.loads(self._config_path.read_text(encoding="utf-8"))
            self.supabase_url = data.get("supabase_url", self.supabase_url)
            self.supabase_anon_key = data.get("supabase_anon_key", self.supabase_anon_key)
        except Exception:
            pass

    def save_config(self, url: str, anon_key: str) -> None:
        self.supabase_url = url.strip()
        self.supabase_anon_key = anon_key.strip()
        try:
            payload: dict[str, str] = {
                "supabase_url": self.supabase_url,
                "supabase_anon_key": self.supabase_anon_key,
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
            )
            self._current_session = AuthSession(
                access_token=data.get("access_token", ""),
                refresh_token=data.get("refresh_token", ""),
                user=user,
                expires_at=data.get("expires_at", 0.0),
            )
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

    def sign_out(self) -> None:
        """Clears local authentication session and notifies listeners."""
        self._current_session = None
        self._save_session()
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
            "apikey": self.supabase_anon_key,
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
            "apikey": self.supabase_anon_key,
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

    def start_google_oauth(self, callback_port: int = 54321) -> tuple[bool, str]:
        """
        Launches Google OAuth in the user's default browser with a 
        temporary local redirect listener.
        """
        if not self.is_cloud_configured:
            # Offline mock Google sign-in
            user = UserProfile(
                id="google_offline_user",
                email="user@gmail.com",
                username="GoogleCreator",
                created_at=time.strftime("%Y-%m-%d"),
            )
            self._current_session = AuthSession(
                access_token="mock_google_token",
                refresh_token="mock_google_refresh",
                user=user,
                expires_at=time.time() + 86400 * 30,
            )
            self._save_session()
            self.auth_state_changed.emit(user)
            return True, "Signed in with Google (Offline Mode) as 'GoogleCreator'."

        redirect_uri: str = f"http://127.0.0.1:{callback_port}/callback"
        auth_url: str = (
            f"{self.supabase_url.rstrip('/')}/auth/v1/authorize?"
            f"provider=google&redirect_to={urllib.parse.quote(redirect_uri)}"
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
            return True, "Opened Google sign-in page in your browser..."
        except Exception as e:
            return False, f"Failed to start OAuth redirect listener: {e}"

    def _handle_oauth_tokens(self, access_token: str, refresh_token: str) -> None:
        """Queries user profile using the captured access token and activates the session."""
        try:
            endpoint: str = f"{self.supabase_url.rstrip('/')}/auth/v1/user"
            headers: dict[str, str] = {
                "Authorization": f"Bearer {access_token}",
                "apikey": self.supabase_anon_key,
            }
            request = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
                meta: dict[str, Any] = data.get("user_metadata", {})
                username: str = (
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


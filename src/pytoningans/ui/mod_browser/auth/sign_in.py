"""
PyToNingans Mod Browser - Auth Sign-In and Sign-Up
==================================================
Email/password authentication, local offline accounts, and Supabase cloud registration.
"""
from __future__ import annotations

import json, time
import urllib.error, urllib.request
from typing import TYPE_CHECKING, Optional

from pytoningans.core.settings import SettingsManager

from .mixin import BaseAuthMixin
from .models import AuthSession, UserProfile, is_known_developer

if TYPE_CHECKING:
    from .manager import AuthManager


def _parse_http_error(e: urllib.error.HTTPError) -> str:
    """Extracts a human-readable message from a Supabase HTTPError response body."""
    try:
        err_data: dict[str, str] = json.loads(e.read().decode("utf-8"))
        return err_data.get("error_description") or err_data.get("msg") or str(e)
    except Exception:
        return f"HTTP Error {e.code}"


class AuthSignInMixin(BaseAuthMixin):
    """
    Mixin that provides sign-in, sign-up, and offline account creation for AuthManager.
    Requires the host class to expose: _store, _config, auth_state_changed.
    """

    # ------------------------------------------------------------------
    # Local / offline sign-in
    # ------------------------------------------------------------------

    def sign_in_locally(self, username: str = "LocalCreator") -> UserProfile:
        """Sets up a local creator session for offline-first modding without cloud connectivity."""
        clean_name: str = username.strip().replace(" ", "_") or "LocalCreator"
        user = self._build_local_user(
            user_id=f"local_{clean_name}",
            email=f"{clean_name.lower()}@pytoningans.local",
            username=clean_name,
            provider="local",
        )
        self._create_local_session(user, expires_offset=86400 * 365)
        return user

    # ------------------------------------------------------------------
    # Cloud sign-in / sign-up
    # ------------------------------------------------------------------

    def sign_in_with_password(
        self, email: str, password: str
    ) -> tuple[bool, str, Optional[UserProfile]]:
        """Signs in with email and password via Supabase Auth REST, or local offline account."""
        email = email.strip()
        if not email or not password:
            return False, "Email and password are required.", None
        
        manager: AuthManager = self._auth_manager()
        if not manager.is_cloud_configured:
            username: str = email.split("@")[0].replace(".", "_")
            user: UserProfile = self._build_local_user(
                user_id=f"local_{username}",
                email=email,
                username=username,
                provider="local",
            )
            self._create_local_session(user, expires_offset=86400 * 30)
            return True, f"Signed in locally as {username} (Offline Mode).", user

        endpoint: str = manager._config.auth_endpoint("/auth/v1/token?grant_type=password")
        payload: bytes = json.dumps({"email": email, "password": password}).encode("utf-8")
        headers = manager._config.build_headers()
        # Authorization header not needed for password grant; strip User-Agent to match
        # the original implementation which used a minimal header set for this endpoint
        headers.pop("User-Agent", None)

        request = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                response_data: dict = json.loads(response.read().decode("utf-8"))
                user_obj: dict = response_data.get("user", {})
                meta: dict = user_obj.get("user_metadata", {})
                username = meta.get("username") or email.split("@")[0]

                is_dev: bool = is_known_developer(
                    user_id=user_obj.get("id", ""),
                    username=username,
                    app_metadata=user_obj.get("app_metadata"),
                    user_metadata=meta,
                )
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
                manager._store.current_session = AuthSession(
                    access_token=response_data.get("access_token", ""),
                    refresh_token=response_data.get("refresh_token", ""),
                    user=user,
                    expires_at=time.time() + response_data.get("expires_in", 3600),
                )
                manager._store.save()
                manager.auth_state_changed.emit(user)
                return True, f"Welcome back, {username}!", user
        except urllib.error.HTTPError as e:
            return False, f"Sign in failed: {_parse_http_error(e)}", None
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
        
        manager = self._auth_manager()
        if not manager.is_cloud_configured:
            user = self._build_local_user(
                user_id=f"local_{username}",
                email=email,
                username=username,
                provider="local",
            )
            self._create_local_session(user, expires_offset=86400 * 30)
            return True, f"Account '{username}' created in Offline Mode!", user

        endpoint: str = manager._config.auth_endpoint("/auth/v1/signup")
        payload: bytes = json.dumps(
            {
                "email": email,
                "password": password,
                "data": {
                    "username": username
                }
            }
        ).encode("utf-8")
        headers: dict[str, str] = manager._config.build_headers()
        headers.pop("User-Agent", None)

        request = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                response_data: dict = json.loads(response.read().decode("utf-8"))
                user_obj: dict = response_data.get("user", {}) or response_data
                meta: dict = user_obj.get("user_metadata", {})
                confirmed_username: str = meta.get("username", username)

                is_dev: bool = is_known_developer(
                    user_id=user_obj.get("id", ""),
                    username=confirmed_username,
                    app_metadata=user_obj.get("app_metadata"),
                    user_metadata=meta,
                )
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

                # Supabase may return a session immediately or require email confirmation
                if "access_token" in response_data:
                    manager._store.current_session = AuthSession(
                        access_token=response_data.get("access_token", ""),
                        refresh_token=response_data.get("refresh_token", ""),
                        user=user,
                        expires_at=time.time() + response_data.get("expires_in", 3600),
                    )
                    manager._store.save()
                    manager.auth_state_changed.emit(user)
                    return True, f"Account '{confirmed_username}' registered and signed in!", user
                else:
                    return True, "Registration successful! Please check your email for confirmation.", user
        except urllib.error.HTTPError as e:
            return False, f"Registration failed: {_parse_http_error(e)}", None
        except Exception as e:
            return False, f"Connection error: {e}", None

    # ------------------------------------------------------------------
    # Shared local session builder
    # ------------------------------------------------------------------

    def _build_local_user(
        self,
        user_id: str,
        email: str,
        username: str,
        provider: str,
        providers: Optional[list[str]] = None,
    ) -> UserProfile:
        """
        Constructs a UserProfile for a local or offline account.
        Checks developer status and assigns the appropriate initial badge set.
        """
        is_dev: bool = is_known_developer(user_id=user_id, username=username)
        resolved_badges: list[str] = ["Developer"] if is_dev else ["Offline Creator"]
        resolved_providers: list[str] = providers if providers is not None else [provider]

        custom_avatar: str = ""
        try:
            custom_avatar = SettingsManager.get().settings.creator_avatar_path
        except Exception:
            pass

        return UserProfile(
            id=user_id,
            email=email,
            username=username,
            created_at=time.strftime("%Y-%m-%d"),
            custom_avatar_path=custom_avatar or None,
            primary_provider=provider,
            providers=resolved_providers,
            is_developer=is_dev,
            badges=resolved_badges,
        )

    def _create_local_session(
        self,
        user: UserProfile,
        expires_offset: float = 86400 * 30,
    ) -> None:
        """
        Creates a mock local AuthSession, saves it to disk, and emits auth_state_changed.
        Used by all offline/local sign-in paths.
        """
        provider: str = user.primary_provider
        manager = self._auth_manager()
        manager._store.current_session = AuthSession(
            access_token=f"mock_{provider}_token" if provider != "local" else "mock_local_token",
            refresh_token=f"mock_{provider}_refresh" if provider != "local" else "mock_refresh_token",
            user=user,
            expires_at=time.time() + expires_offset,
        )
        manager._store.save()
        manager.auth_state_changed.emit(user)

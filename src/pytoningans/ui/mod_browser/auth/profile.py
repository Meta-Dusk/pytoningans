"""
PyToNingans Mod Browser :: Auth Profile Management
=================================================
Creator profile reading, local persistence, and cloud sync via Supabase Auth REST.
"""
from __future__ import annotations

import json
import urllib.error, urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pytoningans.core.settings import SettingsManager

from .mixin import BaseAuthMixin
from .models import is_known_developer

if TYPE_CHECKING:
    from .manager import AuthManager
    from .models import UserProfile
    from pytoningans.ui.mod_browser.auth.models import AuthSession
    from pytoningans.ui.mod_browser.auth.session import AuthSessionStore


class AuthProfileMixin(BaseAuthMixin):
    """
    Mixin that provides creator profile read/write operations for AuthManager.
    Requires the host class to expose: _store, _config, current_user,
    is_authenticated, is_cloud_configured, auth_state_changed.
    """
    # ------------------------------------------------------------------
    # Profile reads
    # ------------------------------------------------------------------

    def get_creator_name(self) -> str:
        """
        Returns the active creator name from the current session or app settings,
        falling back to 'Modder'.
        """
        user: Optional[UserProfile] = self._current_user()
        if user is not None and user.username:
            return user.username
        try:
            saved: str = SettingsManager.get().settings.creator_name.strip()
            if saved:
                return saved
        except Exception:
            pass
        return "Modder"

    def get_creator_bio(self) -> str:
        """Returns the creator bio from the active session or app settings."""
        user: Optional[UserProfile] = self._current_user()
        if user is not None and user.bio:
            return user.bio
        try:
            return SettingsManager.get().settings.creator_bio.strip()
        except Exception:
            return ""

    def get_creator_avatar(self) -> Optional[str]:
        """
        Returns the active avatar source: custom file path, cloud URL, or settings fallback.
        """
        user: Optional[UserProfile] = self._current_user()
        if user is not None:
            if (
                user.custom_avatar_path is not None and
                Path(user.custom_avatar_path).is_file()
            ):
                return user.custom_avatar_path
            if user.avatar_url is not None:
                return user.avatar_url
        try:
            saved_avatar: str = SettingsManager.get().settings.creator_avatar_path.strip()
            if saved_avatar and Path(saved_avatar).is_file():
                return saved_avatar
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Profile writes
    # ------------------------------------------------------------------

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

        self._persist_profile_to_settings(clean_name, bio, custom_avatar_path)
        manager: Optional[AuthManager] = self._auth_manager()
        current_sesh: Optional[AuthSession] = manager._store.current_session

        if current_sesh is not None:
            self._apply_profile_to_session(clean_name, bio, avatar_url, custom_avatar_path)
        else:
            manager.sign_in_locally(clean_name)
            if current_sesh is not None:
                current_sesh.user.bio = bio.strip()
                if custom_avatar_path is not None:
                    current_sesh.user.custom_avatar_path = custom_avatar_path.strip()
                manager._store.save()

        if (
            manager.is_authenticated and
            manager.is_cloud_configured and
            current_sesh is not None and
            current_sesh.access_token != "mock_local_token"
        ):
            try:
                self._sync_profile_to_cloud(clean_name, bio.strip())
            except Exception as e:
                print(f"Notice: Cloud profile sync warning: {e}")

        manager.auth_state_changed.emit(manager.current_user)
        return True, f"Profile updated! Creator handle set to '{clean_name}'."

    def _persist_profile_to_settings(
        self,
        username: str,
        bio: str,
        custom_avatar_path: Optional[str],
    ) -> None:
        """Saves creator profile fields to AppSettings."""
        try:
            SettingsManager.get().update_settings(
                creator_name=username,
                creator_bio=bio.strip(),
                creator_avatar_path=(
                    custom_avatar_path.strip() if custom_avatar_path is not None else None
                ),
            )
        except Exception:
            pass

    def _apply_profile_to_session(
        self,
        clean_name: str,
        bio: str,
        avatar_url: Optional[str],
        custom_avatar_path: Optional[str],
    ) -> None:
        """Updates the in-memory session user fields and recomputes developer badges."""
        manager: Optional[AuthManager] = self._auth_manager()
        store: AuthSessionStore = manager._store
        sesh: Optional[AuthSession] = store.current_session
        if sesh is None: return
        
        sesh.user.username = clean_name
        sesh.user.bio = bio.strip()
        if avatar_url is not None:
            sesh.user.avatar_url = avatar_url
        if custom_avatar_path is not None:
            sesh.user.custom_avatar_path = custom_avatar_path.strip()
        self._recompute_developer_badges(sesh.user, clean_name)
        store.save()

    def _recompute_developer_badges(self, user: UserProfile, username: str) -> None:
        """Re-evaluates developer status and inserts the Developer badge if warranted."""
        is_dev: bool = is_known_developer(
            user_id=user.id,
            username=username,
            github_username=user.github_username,
        )
        user.is_developer = is_dev
        if is_dev and "Developer" not in user.badges:
            user.badges.insert(0, "Developer")

    def _sync_profile_to_cloud(self, username: str, bio: str) -> None:
        """Synchronizes username and bio to Supabase user_metadata via the Auth REST API."""
        manager: Optional[AuthManager] = self._auth_manager()
        store: AuthSessionStore = manager._store
        sesh: Optional[AuthSession] = store.current_session
        store.ensure_valid()
        if sesh is None or not manager.is_cloud_configured:
            return

        endpoint: str = store._config.auth_endpoint("/auth/v1/user")
        payload: bytes = json.dumps(
            {
                "data": {
                    "username": username,
                    "bio": bio
                }
            }
        ).encode("utf-8")
        headers: dict[str, str] = store._config.build_headers(auth_token=sesh.access_token)

        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=8) as _:
                pass
        except urllib.error.HTTPError as error:
            # On 401/403 (expired token), attempt one auto-refresh and retry
            if error.code in (401, 403) and store.refresh():
                headers["Authorization"] = f"Bearer {sesh.access_token}"
                retry_req = urllib.request.Request(
                    endpoint, data=payload, headers=headers, method="PUT"
                )
                with urllib.request.urlopen(retry_req, timeout=8) as _:
                    pass
                return
            raise

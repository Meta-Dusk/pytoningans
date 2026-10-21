"""
PyToNingans Mod Browser :: OAuth Sign-In (Google, GitHub)
=========================================================
Launches provider OAuth in the system browser via a temporary local redirect listener.
"""
from __future__ import annotations

import json, threading, time, webbrowser
import urllib.parse, urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from pytoningans.core.settings import SettingsManager

from .mixin import BaseAuthMixin
from .models import AuthSession, UserProfile, is_known_developer

if TYPE_CHECKING:
    from .manager import AuthManager


class AuthOAuthMixin(BaseAuthMixin):
    """
    Mixin that provides OAuth browser-redirect sign-in flows for AuthManager.
    Requires the host class to expose: _store, _config, is_cloud_configured,
    auth_state_changed, _build_local_user, _create_local_session.
    """

    def start_oauth(self, provider: str = "google", callback_port: int = 54321) -> tuple[bool, str]:
        """
        Launches OAuth (Google, GitHub, etc.) in the user's default browser with a
        temporary local redirect listener.
        Falls back to a mock offline creator profile when cloud is not configured.
        """
        from ..oauth_handler import OAuthCallbackServer, OAuthCallbackHandler

        prov_key: str = provider.lower()
        prov_name: str = "GitHub" if prov_key == "github" else provider.capitalize()
        manager: AuthManager = self._auth_manager()

        if not manager.is_cloud_configured:
            user: UserProfile = self._build_offline_oauth_user(prov_key, prov_name)
            manager._create_local_session(user, expires_offset=86400 * 30)
            return True, f"Signed in with {prov_name} (Offline Mode) as '{user.username}'."

        redirect_uri: str = f"http://127.0.0.1:{callback_port}/callback"
        auth_url: str = (
            f"{manager._config.auth_endpoint('/auth/v1/authorize')}?"
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

    def _build_offline_oauth_user(self, prov_key: str, prov_name: str) -> UserProfile:
        """Constructs a mock UserProfile for offline OAuth fallback."""
        mock_id: str = f"{prov_key}_offline_user"
        mock_email: str = "user@gmail.com" if prov_key == "google" else f"creator@{prov_key}.local"
        mock_username: str = f"{prov_name}Creator"
        return self._auth_manager()._build_local_user(
            user_id=mock_id,
            email=mock_email,
            username=mock_username,
            provider=prov_key,
        )

    def _handle_oauth_tokens(self, access_token: str, refresh_token: str) -> None:
        """
        Queries user profile using the captured access token and activates the session.
        Applies creator identity separation and multi-provider inheritance:
        - First provider login sets default username and avatar.
        - Subsequent provider logins link to the profile without overriding custom creator details.
        """
        try:
            manager: AuthManager = self._auth_manager()
            endpoint: str = manager._config.auth_endpoint("/auth/v1/user")
            headers: dict[str, str] = manager._config.build_headers(auth_token=access_token)
            request = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                data: dict[str, Any] = json.loads(response.read().decode("utf-8"))

                app_meta: dict[str, Any] = data.get("app_metadata", {})
                meta: dict[str, Any] = data.get("user_metadata", {})
                identities: list[dict[str, Any]] = data.get("identities", [])

                prov_key, incoming_providers = self._extract_providers(
                    app_meta, identities
                )
                github_username = self._extract_github_username(
                    identities, incoming_providers, prov_key, meta
                )
                google_email = self._extract_google_email(
                    identities, incoming_providers, prov_key, data
                )

                email_verified: bool = (
                    bool(meta.get("email_verified"))
                    or bool(data.get("email_confirmed_at"))
                    or prov_key in ("google", "github")
                )
                avatar_url: Optional[str] = meta.get("avatar_url")

                existing: dict[str, Any] = self._gather_existing_profile(
                    github_username, google_email, avatar_url
                )
                github_username = existing["github_username"]
                google_email = existing["google_email"]
                avatar_url = existing["avatar_url"]
                existing_providers: list[str] = existing["providers"]
                existing_handle: str = existing["handle"]
                existing_bio: str = existing["bio"]
                existing_custom_avatar: str = existing["custom_avatar"]

                chosen_username: str = self._resolve_creator_handle(
                    existing_handle, meta, github_username, data
                )

                # Combine provider records
                merged_providers = list(dict.fromkeys(existing_providers + incoming_providers))

                is_dev: bool = is_known_developer(
                    user_id=data.get("id", ""),
                    username=chosen_username,
                    github_username=github_username,
                    app_metadata=app_meta,
                    user_metadata=meta,
                )
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

                manager._store.current_session = AuthSession(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    user=user,
                    expires_at=time.time() + 3600,
                )
                manager._store.save()
                manager.auth_state_changed.emit(user)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Extracted OAuth helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_providers(
        app_meta: dict[str, Any],
        identities: list[dict[str, Any]],
    ) -> tuple[str, list[str]]:
        """Extracts the primary provider key and full list of linked providers."""
        prov_key: str = (app_meta.get("provider") or "").lower() or "oauth"
        incoming_providers: list[str] = [p.lower() for p in app_meta.get("providers", [])]
        if prov_key and prov_key not in incoming_providers:
            incoming_providers.append(prov_key)
        # Scan identities to uncover all connected providers
        for identity in identities:
            id_prov = (identity.get("provider") or "").lower()
            if id_prov and id_prov not in incoming_providers:
                incoming_providers.append(id_prov)
        return prov_key, incoming_providers

    @staticmethod
    def _extract_github_username(
        identities: list[dict[str, Any]],
        incoming_providers: list[str],
        prov_key: str,
        meta: dict[str, Any],
    ) -> Optional[str]:
        """Extracts the GitHub username from identity data or user metadata fallback."""
        github_username: Optional[str] = None
        for identity in identities:
            if identity.get("provider") == "github":
                id_data = identity.get("identity_data", {})
                github_username = id_data.get("user_name") or id_data.get("preferred_username")
                break
        if not github_username and ("github" in incoming_providers or prov_key == "github"):
            github_username = meta.get("user_name") or meta.get("preferred_username")
        return github_username

    @staticmethod
    def _extract_google_email(
        identities: list[dict[str, Any]],
        incoming_providers: list[str],
        prov_key: str,
        data: dict[str, Any],
    ) -> Optional[str]:
        """Extracts the Google account email from identity data or top-level user email fallback."""
        google_email: Optional[str] = None
        for identity in identities:
            if identity.get("provider") == "google":
                id_data = identity.get("identity_data", {})
                google_email = id_data.get("email")
                break
        if not google_email and ("google" in incoming_providers or prov_key == "google"):
            google_email = data.get("email")
        return google_email

    def _gather_existing_profile(
        self,
        github_username: Optional[str],
        google_email: Optional[str],
        avatar_url: Optional[str],
    ) -> dict[str, Any]:
        """
        Collects the current in-memory or settings-persisted creator profile fields
        for multi-provider merging during OAuth token handling.
        """
        result: dict[str, Any] = {
            "handle": "",
            "bio": "",
            "custom_avatar": "",
            "providers": [],
            "github_username": github_username,
            "google_email": google_email,
            "avatar_url": avatar_url,
        }
        
        sesh: Optional[AuthSession] = self._auth_manager()._store.current_session
        if (
            sesh is not None and
            not sesh.user.id.startswith("local_")
        ):
            result["handle"] = sesh.user.username
            result["bio"] = sesh.user.bio
            result["custom_avatar"] = sesh.user.custom_avatar_path or ""
            result["providers"] = list(sesh.user.providers)
            if not github_username:
                result["github_username"] = sesh.user.github_username
            if not google_email:
                result["google_email"] = sesh.user.google_email
            if not avatar_url:
                result["avatar_url"] = sesh.user.avatar_url
        else:
            try:
                saved_name: str = SettingsManager.get().settings.creator_name.strip()
                if saved_name and saved_name != "Modder":
                    result["handle"] = saved_name
                saved_avatar: str = SettingsManager.get().settings.creator_avatar_path.strip()
                if saved_avatar and Path(saved_avatar).is_file():
                    result["custom_avatar"] = saved_avatar
                result["bio"] = SettingsManager.get().settings.creator_bio.strip()
            except Exception:
                pass

        return result

    @staticmethod
    def _resolve_creator_handle(
        existing_handle: str,
        meta: dict[str, Any],
        github_username: Optional[str],
        data: dict[str, Any],
    ) -> str:
        """
        Resolves the creator handle to use for the new OAuth session.
        Prefers the existing customized handle, then Supabase metadata username,
        then falls back to inferring a handle from the OAuth provider identity.
        """
        if existing_handle:
            return existing_handle
        if meta.get("username"):
            return str(meta.get("username")).replace(" ", "_")

        # First-time login: inherit details from OAuth provider
        raw_provider_name: str = (
            github_username or
            meta.get("user_name") or
            meta.get("preferred_username") or
            meta.get("full_name") or
            meta.get("name") or
            data.get("email", "").split("@")[0]
        )
        chosen: str = raw_provider_name.replace(" ", "_")
        try:
            SettingsManager.get().update_settings(creator_name=chosen)
        except Exception:
            pass
        return chosen

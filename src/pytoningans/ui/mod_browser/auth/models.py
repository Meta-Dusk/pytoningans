"""
PyToNingans Mod Browser :: Auth Data Models
==========================================
Pure data containers for user identity and session state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from pytoningans.core.roles import is_developer_account


def is_known_developer(
    user_id: str = "",
    username: str = "",
    github_username: Optional[str] = None,
    app_metadata: Optional[dict[str, Any]] = None,
    user_metadata: Optional[dict[str, Any]] = None,
) -> bool:
    """
    Returns True if the user account is recognized as an official PyToNingans core developer.
    Evaluates:
    1. Supabase Auth app_metadata (e.g. role == 'developer')
    2. Supabase Auth user_metadata
    3. The public.creator_roles database table (cached locally by user_id UUID)
    """
    return is_developer_account(
        user_id=user_id,
        handle=username or (github_username or ""),
        app_metadata=app_metadata,
        user_metadata=user_metadata,
    )


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

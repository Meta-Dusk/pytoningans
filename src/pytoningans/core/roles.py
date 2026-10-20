"""
PyToNingans - Flexible Account Roles and Developer Verification System
=====================================================================
Manages creator account roles (e.g. Developer, Moderator, Verified Creator).
Supports:
1. Supabase Auth app_metadata and user_metadata role attributes.
2. Supabase public.creator_roles database table for dynamic administrator control.
3. Local disk caching and offline fallbacks for offline-first modding.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from pytoningans.utils.paths import get_settings_path

_DEFAULT_ROLES: dict[str, str] = {
    "meta-dusk": "developer",
    "andredcxxv@gmail.com": "developer",
}


def get_roles_cache_path() -> Path:
    """Returns the local path to the cached creator roles file."""
    return get_settings_path().parent / "creator_roles_cache.json"


def load_cached_roles() -> dict[str, str]:
    """Loads cached creator roles from disk, falling back to default core developers."""
    cache_path: Path = get_roles_cache_path()
    roles: dict[str, str] = dict(_DEFAULT_ROLES)
    if cache_path.is_file():
        try:
            data: dict[str, Any] = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(k, str) and isinstance(v, str):
                        roles[k.strip().lower()] = v.strip().lower()
        except Exception:
            pass
    return roles


def save_cached_roles(roles: dict[str, str]) -> None:
    """Persists fetched roles to local disk cache for instant offline access."""
    cache_path: Path = get_roles_cache_path()
    try:
        clean: dict[str, str] = {k.strip().lower(): v.strip().lower() for k, v in roles.items()}
        cache_path.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_role_for_creator(handle: str = "", email: str = "") -> Optional[str]:
    """
    Looks up the role for a given creator handle or email address.
    Returns 'developer', 'moderator', etc., or None if not assigned a special role.
    """
    roles: dict[str, str] = load_cached_roles()
    if handle and handle.strip().lower() in roles:
        return roles[handle.strip().lower()]
    if email and email.strip().lower() in roles:
        return roles[email.strip().lower()]
    return None


def is_developer_account(
    handle: str = "",
    email: str = "",
    github_username: Optional[str] = None,
    app_metadata: Optional[dict[str, Any]] = None,
    user_metadata: Optional[dict[str, Any]] = None,
) -> bool:
    """
    Evaluates whether an account possesses the official Core Developer role through:
    1. Supabase Auth app_metadata (e.g. {"role": "developer"} or {"is_developer": true})
    2. Supabase Auth user_metadata
    3. The public.creator_roles table (cached locally)
    4. Default core developer handles (offline fallback)
    """
    dev_role: str = "developer"
    
    # Supabase Auth app_metadata (Admin-only in Supabase Dashboard)
    if app_metadata is not None:
        role: str = str(app_metadata.get("role", "")).lower()
        roles_list: list[str] = [
            str(r).lower() for r in app_metadata.get("roles", []) if isinstance(r, str)
        ]
        if (
            role == dev_role or dev_role in roles_list or
            app_metadata.get("is_developer") is True
        ):
            return True

    # Supabase Auth user_metadata
    if user_metadata is not None:
        role = str(user_metadata.get("role", "")).lower()
        if role == dev_role or user_metadata.get("is_developer") is True:
            return True

    # Database roles lookup (handle, email, or GitHub username)
    if handle and get_role_for_creator(handle=handle) == dev_role:
        return True
    if email and get_role_for_creator(email=email) == dev_role:
        return True
    if (
        github_username is not None and
        get_role_for_creator(handle=github_username) == dev_role
    ):
        return True

    return False


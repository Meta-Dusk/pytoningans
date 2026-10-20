"""
PyToNingans - Database-Driven Account Roles and Developer Verification System
=============================================================================
Manages creator account roles (e.g. Developer, Moderator, Verified Creator).
Supports:
1. Supabase public.creator_roles database table for dynamic administrator control.
2. Cryptographic user_id (UUID) verification from Supabase Auth tokens to prevent spoofing.
3. Supabase Auth app_metadata and user_metadata role attributes.
4. Local disk caching for offline-first modding.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from pytoningans.utils.paths import get_settings_path


def get_roles_cache_path() -> Path:
    """Returns the local path to the cached creator roles file."""
    return get_settings_path().parent / "creator_roles_cache.json"


def load_cached_roles() -> dict[str, dict[str, str]]:
    """
    Loads cached creator roles from disk.
    Structure:
    {
        "user_ids": { "uuid": "role" },
        "handles": { "handle_lower": "role" },
        "github": { "uuid_or_handle": "github_username" }
    }
    """
    cache_path: Path = get_roles_cache_path()
    roles: dict[str, dict[str, str]] = {
        "user_ids": {},
        "handles": {},
        "github": {},
    }
    if cache_path.is_file():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                roles["user_ids"] = {
                    str(k): str(v).lower()
                    for k, v in data.get("user_ids", {}).items()
                }
                roles["handles"] = {
                    str(k).lower(): str(v).lower()
                    for k, v in data.get("handles", {}).items()
                }
                roles["github"] = {
                    str(k).lower(): str(v)
                    for k, v in data.get("github", {}).items()
                }
        except Exception:
            pass
    return roles


def save_cached_roles(raw_rows: list[dict[str, Any]]) -> None:
    """
    Normalizes and persists fetched database rows from public.creator_roles
    to local disk cache for instant offline access.
    """
    cache_path: Path = get_roles_cache_path()
    roles: dict[str, dict[str, str]] = {
        "user_ids": {},
        "handles": {},
        "github": {},
    }
    for row in raw_rows:
        uid: str = str(row.get("user_id") or "").strip()
        role: str = str(row.get("role") or "developer").strip().lower()
        handle: str = str(row.get("handle") or "").strip().lower()
        gh: str = str(row.get("github_username") or "").strip()

        if uid:
            roles["user_ids"][uid] = role
            if gh:
                roles["github"][uid] = gh
        if handle:
            roles["handles"][handle] = role
            if gh:
                roles["github"][handle] = gh

    try:
        cache_path.write_text(json.dumps(roles, indent=2), encoding="utf-8")
    except Exception:
        pass


def is_developer_account(
    user_id: str = "",
    handle: str = "",
    app_metadata: Optional[dict[str, Any]] = None,
    user_metadata: Optional[dict[str, Any]] = None,
) -> bool:
    """
    Evaluates whether an account possesses the official Core Developer role.
    Securely checks by authenticated user_id UUID and Supabase metadata:
    1. Supabase Auth app_metadata (e.g. {"role": "developer"} or {"is_developer": true})
    2. Supabase Auth user_metadata
    3. The public.creator_roles table (cached locally by user_id UUID)
    """
    dev_role: str = "developer"

    # Supabase Auth app_metadata (from JWT or user payload)
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

    # Database creator_roles lookup by authenticated user_id UUID
    cached: dict[str, dict[str, str]] = load_cached_roles()
    if user_id:
        return cached.get("user_ids", {}).get(user_id) == dev_role

    # Handle lookup in verified database roles (only when user_id is absent, e.g. offline seed data)
    clean_handle: str = handle.strip().lower()
    if clean_handle and cached.get("handles", {}).get(clean_handle) == dev_role:
        return True

    return False


def get_github_for_creator(user_id: str = "", handle: str = "") -> Optional[str]:
    """Retrieves verified GitHub username for a creator if registered in creator_roles."""
    cached: dict[str, dict[str, str]] = load_cached_roles()
    gh_map: dict[str, str] = cached.get("github", {})
    if user_id:
        return gh_map.get(user_id)
    clean_handle: str = handle.strip().lower()
    if clean_handle and clean_handle in gh_map:
        return gh_map.get(clean_handle)
    return None

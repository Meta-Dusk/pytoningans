"""
PyToNingans Mod Browser :: Auth Configuration
=============================================
Loads and persists Supabase project credentials with hierarchical source priority.
"""
from __future__ import annotations

import json, os
from pathlib import Path
from typing import Any, Optional

from pytoningans.utils.paths import get_settings_path, get_base_path, get_app_version


class AuthConfig:
    """
    Manages Supabase project credentials (URL + anon key).

    Loads configuration in hierarchical priority:
    1. Bundled cloud_config.json in application folder (packaged by installer)
    2. Local .env file in project root (for developer convenience)
    3. OS environment variables (SUPABASE_URL, SUPABASE_ANON_KEY)
    4. User documents override (if customized via Advanced Server settings)
    """

    def __init__(self) -> None:
        self._config_path: Path = get_settings_path().parent / "supabase_config.json"
        self.supabase_url: str = os.environ.get("SUPABASE_URL", "")
        self.supabase_pub_key: str = os.environ.get("SUPABASE_ANON_KEY", "")
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_cloud_configured(self) -> bool:
        """True when both Supabase URL and anon key are present."""
        return bool(self.supabase_url and self.supabase_pub_key)

    def auth_endpoint(self, path: str) -> str:
        """Builds a full Supabase Auth REST endpoint URL for a given path."""
        return f"{self.supabase_url.rstrip('/')}{path}"

    def build_headers(
        self, *,
        auth_token: Optional[str] = None,
        content_type: str = "application/json",
    ) -> dict[str, str]:
        """
        Builds standard Supabase request headers.
        Includes Authorization bearer token only when *auth_token* is provided.
        """
        headers: dict[str, str] = {
            "Content-Type": content_type,
            "apikey": self.supabase_pub_key,
            "User-Agent": f"PyToNingans/{get_app_version()}",
        }
        if auth_token is not None:
            headers["Authorization"] = f"Bearer {auth_token}"
        return headers

    def save(self, url: str, anon_key: str) -> None:
        """Persists Supabase credentials to the user documents override file."""
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

    # ------------------------------------------------------------------
    # Internal loading logic
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._load_bundled_config()
        self._load_env_file()
        self._load_env_vars()
        self._load_user_override()

    def _load_bundled_config(self) -> None:
        """Applies credentials from the installer-bundled cloud_config.json, if present."""
        bundled_config: Path = get_base_path() / "cloud_config.json"
        if not bundled_config.is_file():
            return
        try:
            data: dict[str, Any] = json.loads(bundled_config.read_text(encoding="utf-8"))
            self.supabase_url = data.get("supabase_url", self.supabase_url)
            self.supabase_pub_key = data.get("supabase_anon_key", self.supabase_pub_key)
        except Exception:
            pass

    def _load_env_file(self) -> None:
        """Applies credentials from a local .env file in the project root."""
        env_vars: dict[str, str] = self._read_env_file(get_base_path() / ".env")
        if "SUPABASE_URL" in env_vars:
            self.supabase_url = env_vars["SUPABASE_URL"]
        if "SUPABASE_ANON_KEY" in env_vars:
            self.supabase_pub_key = env_vars["SUPABASE_ANON_KEY"]

    def _load_env_vars(self) -> None:
        """Applies credentials from OS environment variables."""
        self.supabase_url = os.environ.get("SUPABASE_URL", self.supabase_url)
        self.supabase_pub_key = os.environ.get("SUPABASE_ANON_KEY", self.supabase_pub_key)

    def _load_user_override(self) -> None:
        """Applies credentials from the user's personal server settings override file."""
        if not self._config_path.is_file():
            return
        try:
            data: dict[str, Any] = json.loads(self._config_path.read_text(encoding="utf-8"))
            self.supabase_url = data.get("supabase_url", self.supabase_url)
            self.supabase_pub_key = data.get("supabase_anon_key", self.supabase_pub_key)
        except Exception:
            pass

    @staticmethod
    def _read_env_file(env_path: Path) -> dict[str, str]:
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

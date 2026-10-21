"""
PyToNingans Mod Browser - Supabase Cloud REST Client
===================================================
Provides PostgREST API operations and Storage bucket management for community mods,
releases, package archives, and ratings.
Designed with timeouts and graceful error handling for robust offline/online resilience.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING
import urllib.error, urllib.parse, urllib.request

from pytoningans.utils.paths import get_app_version
from pytoningans.core.roles import save_cached_roles
from .auth import AuthManager

if TYPE_CHECKING:
    from pytoningans.ui.mod_browser.auth import AuthSession, UserProfile


class SupabaseClient:
    """Client for querying and updating Supabase database tables and storage."""

    def __init__(self, auth: Optional[AuthManager] = None) -> None:
        self.auth: AuthManager = auth or AuthManager.get()

    @property
    def is_configured(self) -> bool:
        return bool(self.auth.supabase_url and self.auth.supabase_pub_key)

    @property
    def base_url(self) -> str:
        return self.auth.supabase_url

    @property
    def publishable_key(self) -> str:
        return self.auth.supabase_pub_key

    def _headers(self, requires_auth: bool = False, is_upload: bool = False) -> dict[str, str]:
        headers: dict[str, str] = {
            "apikey": self.publishable_key,
            "User-Agent": f"PyToNingans/{get_app_version()}",
        }
        if not is_upload:
            headers["Content-Type"] = "application/json"

        self.auth.ensure_valid_session()

        # user = self.auth.current_user
        current_sesh: Optional[AuthSession] = self.auth._store.current_session
        token: Optional[str] = current_sesh.access_token if current_sesh is not None else None

        if token and token != "mock_local_token" and token != "mock_google_token":
            print("[_headers] Using JWT")
            headers["Authorization"] = f"Bearer {token}"
        elif requires_auth:
            print("[_headers] Using default pub key")
            headers["Authorization"] = f"Bearer {self.publishable_key}"
        else:
            print("[_headers] Using default pub key")
            headers["Authorization"] = f"Bearer {self.publishable_key}"

        return headers

    def fetch_creator_roles(self) -> list[dict[str, Any]]:
        """
        Fetches creator roles from public.creator_roles and caches them locally.
        Gracefully returns empty list if table does not exist or network fails.
        """
        if not self.is_configured:
            return []

        endpoint: str = (
            self.base_url +
            "/rest/v1/creator_roles?select=user_id,role,handle,github_username,email"
        )
        headers: dict[str, str] = self._headers(requires_auth=False)
        req = urllib.request.Request(endpoint, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                data: list[dict[str, Any]] = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    save_cached_roles(data)
                    return data
        except Exception:
            pass
        return []

    def fetch_catalog(self) -> tuple[bool, str, list[dict[str, Any]]]:
        """Queries the public.mods table including joined mod_releases and mod_ratings."""
        if not self.is_configured:
            return False, "Supabase cloud is not configured.", []

        # Refresh creator roles in background
        try:
            self.fetch_creator_roles()
        except Exception:
            pass

        endpoint: str = f"{self.base_url}/rest/v1/mods?select=*,mod_releases(*),mod_ratings(*)"
        headers: dict[str, str] = self._headers(requires_auth=False)
        req = urllib.request.Request(endpoint, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                formatted_items: list[dict[str, Any]] = []

                for row in data:
                    ratings_list: list[dict[str, Any]] = row.get("mod_ratings", [])
                    rating_count = len(ratings_list)
                    avg_rating: float = 10.0
                    if rating_count > 0:
                        total_pts: float = sum(float(r.get("rating", 10.0)) for r in ratings_list)
                        avg_rating = round(total_pts / rating_count, 1)

                    releases_list: list[dict[str, Any]] = sorted(
                        row.get("mod_releases", []),
                        key=lambda r: r.get("created_at", ""),
                        reverse=True,
                    )

                    formatted_items.append({
                        "id": row.get("id"),
                        "name": row.get("name"),
                        "entity_type": row.get("entity_type"),
                        "version": row.get("version"),
                        "author": row.get("author"),
                        "author_id": row.get("author_id"),
                        "description": row.get("description", ""),
                        "tags": list(row.get("tags") or []),
                        "rating": avg_rating,
                        "rating_count": rating_count,
                        "downloads": int(row.get("downloads", 0)),
                        "size_bytes": int(row.get("size_bytes", 0)),
                        "is_pack": bool(row.get("is_pack", False)),
                        "contained_entities": list(row.get("contained_entities") or []),
                        "icon_url": row.get("icon_url"),
                        "package_url": row.get("package_url"),
                        "config_version": int(row.get("config_version", 10)),
                        "target_app_version": row.get("target_app_version", "0.8.0"),
                        "created_at": str(row.get("created_at", ""))[:10],
                        "updated_at": str(row.get("updated_at", ""))[:10],
                        "releases": [
                            {
                                "version": r.get("version"),
                                "changelog": r.get("changelog", ""),
                                "created_at": str(r.get("created_at", ""))[:10],
                                "config_version": int(r.get("config_version", 10)),
                                "target_app_version": r.get("target_app_version", "0.8.0"),
                                "download_url": r.get("download_url"),
                            }
                            for r in releases_list
                        ],
                    })

                return True, f"Loaded {len(formatted_items)} mods from cloud.", formatted_items
        except urllib.error.HTTPError as e:
            return False, f"Cloud query failed: HTTP {e.code}", []
        except Exception as e:
            return False, f"Network error connecting to cloud: {e}", []

    def upload_package(self, zip_path: Path, filename: str) -> tuple[bool, str, Optional[str]]:
        """
        Uploads a package zip archive to the 'mods' storage bucket and returns its public URL.
        """
        if not self.is_configured:
            print(
                "[upload_package] Upload status...\n"
                " ok=False\n"
                " msg=\"Cloud storage not configured.\"\n"
                " url=None"
            )
            return False, "Cloud storage not configured.", None

        if not zip_path.exists():
            print(
                "[upload_package] Upload status...\n"
                " ok=False\n"
                f" msg=\"Zip file does not exist: {zip_path}\"\n"
                " url=None"
            )
            return False, f"Zip file does not exist: {zip_path}", None
        
        print(f"Zip file created at: {zip_path}")

        clean_filename: str = urllib.parse.quote(filename.replace(" ", "_"), safe="/")
        endpoint: str = f"{self.base_url}/storage/v1/object/mods/{clean_filename}"

        headers: dict[str, str] = self._headers(requires_auth=True, is_upload=True)
        headers["Content-Type"] = "application/zip"
        headers["x-upsert"] = "true"

        data_bytes: bytes = zip_path.read_bytes()
        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                public_url = f"{self.base_url}/storage/v1/object/public/mods/{clean_filename}"
                print(
                    "[upload_package] Upload status...\n"
                    " ok=True\n"
                    " msg=\"Uploaded package to cloud storage.\"\n"
                    f" url={public_url}"
                )
                return True, "Uploaded package to cloud storage.", public_url
        except urllib.error.HTTPError as e:
            try:
                err_text = e.read().decode("utf-8")
            except Exception:
                err_text = str(e)
            print(
                "[upload_package] Upload status...\n"
                " ok=False\n"
                f" msg=\"Storage upload failed (HTTP {e.code}): {err_text}\"\n"
                " url=None"
            )
            return False, f"Storage upload failed (HTTP {e.code}): {err_text}", None
        except Exception as e:
            print(
                "[upload_package] Upload status...\n"
                " ok=False\n"
                f" msg=\"Failed to upload package: {e}\"\n"
                " url=None"
            )
            return False, f"Failed to upload package: {e}", None

    def publish_new_mod(self, mod_data: dict[str, Any], release_data: dict[str, Any]) -> tuple[bool, str]:
        """Inserts a new mod and its initial release into public.mods and public.mod_releases."""
        if not self.is_configured:
            print("[publish_new_mod] Cloud database not configured.")
            return False, "Cloud database not configured."

        headers: dict[str, str] = self._headers(requires_auth=True)
        # Upsert handling allows retries without 409 Conflict errors
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        # Register or update parent mod record
        mods_endpoint: str = f"{self.base_url}/rest/v1/mods"
        payload: bytes = json.dumps(mod_data).encode("utf-8")
        req = urllib.request.Request(mods_endpoint, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"[publish_new_mod] Failed to register mod (HTTP {e.code}): {err_body}")
            return False, f"Failed to register mod (HTTP {e.code}): {err_body}"
        except Exception as e:
            print(f"[publish_new_mod] Connection error registering mod: {e}")
            return False, f"Connection error registering mod: {e}"

        # Insert initial release record
        rel_endpoint: str = f"{self.base_url}/rest/v1/mod_releases"
        rel_payload: bytes = json.dumps(release_data).encode("utf-8")
        rel_req = urllib.request.Request(rel_endpoint, data=rel_payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(rel_req, timeout=10):
                print("[publish_new_mod] Successfully registered mod and release in cloud database.")
                return True, "Successfully registered mod and release in cloud database."
        except urllib.error.HTTPError as e:
            err_body: str = e.read().decode("utf-8", errors="replace")
            print(f"[publish_new_mod] Mod registered, but release entry failed (HTTP {e.code}): {err_body}")
            return False, f"Mod registered, but release entry failed (HTTP {e.code}): {err_body}"
        except Exception as e:
            print(f"[publish_new_mod] Mod registered, but release entry failed: {e}")
            return False, f"Mod registered, but release entry failed: {e}"

    def publish_release_update(
        self, mod_id: str, mod_update: dict[str, Any], release_data: dict[str, Any]
    ) -> tuple[bool, str]:
        """Updates public.mods and appends a new release row in public.mod_releases."""
        if not self.is_configured:
            return False, "Cloud database not configured."

        # Update mods table
        mod_patch_url: str = f"{self.base_url}/rest/v1/mods?id=eq.{urllib.parse.quote(mod_id)}"
        headers: dict[str, str] = self._headers(requires_auth=True)
        patch_payload: bytes = json.dumps(mod_update).encode("utf-8")
        req = urllib.request.Request(mod_patch_url, data=patch_payload, headers=headers, method="PATCH")

        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except urllib.error.HTTPError as e:
            return False, f"Failed to update mod entry: HTTP {e.code}"
        except Exception as e:
            return False, f"Connection error: {e}"

        # Insert new release row
        rel_endpoint: str = f"{self.base_url}/rest/v1/mod_releases"
        headers["Prefer"] = "resolution=merge-duplicates"
        rel_payload: bytes = json.dumps(release_data).encode("utf-8")
        rel_req = urllib.request.Request(rel_endpoint, data=rel_payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(rel_req, timeout=10):
                return True, "Successfully published release update to cloud."
        except Exception as e:
            return False, f"Failed to register release in cloud: {e}"

    def submit_rating(self, mod_id: str, score: float) -> tuple[bool, str]:
        """Submits or updates a rating (1.0 to 10.0) in public.mod_ratings."""
        if not self.is_configured:
            return False, "Cloud database not configured."

        user: Optional[UserProfile] = self.auth.current_user
        if user is None or not user.id:
            return False, "You must be signed in to submit cloud ratings."

        endpoint: str = f"{self.base_url}/rest/v1/mod_ratings"
        headers: dict[str, str] = self._headers(requires_auth=True)
        headers["Prefer"] = "resolution=merge-duplicates"

        payload: bytes = json.dumps({
            "mod_id": mod_id,
            "user_id": user.id,
            "rating": round(score, 1),
        }).encode("utf-8")

        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10):
                return True, f"Rating of {score:.1f}/10 synchronized to cloud!"
        except Exception as e:
            return False, f"Failed to sync rating to cloud: {e}"

    def download_package(self, download_url: str, destination_path: Path) -> tuple[bool, str]:
        """Downloads a zip package from a remote URL into destination_path."""
        headers: dict[str, str] = self._headers(requires_auth=False)
        req = urllib.request.Request(download_url, headers=headers, method="GET")

        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(req, timeout=30) as resp, open(destination_path, "wb") as f:
                while chunk := resp.read(65536):
                    f.write(chunk)
            return True, f"Package downloaded ({destination_path.stat().st_size} bytes)."
        except Exception as e:
            if destination_path.exists():
                destination_path.unlink()
            return False, f"Failed to download package: {e}"


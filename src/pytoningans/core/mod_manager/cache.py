from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap

type CacheKey = tuple[str, int, int, int, int]

shared_frame_cache: dict[CacheKey, QPixmap] = {}
"""Cache mapping (mod_name, x, y, width, height) -> sliced QPixmap."""

shared_sheets: dict[str, QPixmap] = {}
"""Cache mapping mod_folder_name -> full sprite sheet QPixmap."""


def clear_shared_cache() -> None:
    """Flushes all extracted master frames and sprite sheets from memory."""
    shared_frame_cache.clear()
    shared_sheets.clear()


def clear_mod_cache(mod_folder: str) -> None:
    """Flushes cached sprite sheets and sliced frames for a specific mod folder."""
    if mod_folder in shared_sheets:
        del shared_sheets[mod_folder]
    keys_to_remove: list[CacheKey] = [
        key for key in shared_frame_cache if key[0] == mod_folder
    ]
    for key in keys_to_remove:
        del shared_frame_cache[key]


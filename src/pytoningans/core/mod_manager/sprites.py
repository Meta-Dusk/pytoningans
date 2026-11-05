from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPixmap

from .cache import clear_shared_cache, shared_frame_cache

if TYPE_CHECKING:
    from ..constants import AnimationMeta
    from .cache import CacheKey


def resolve_dimensions(
    global_sheet: Optional[QPixmap],
    global_columns: int,
    global_rows: int,
    animations: dict[str, AnimationMeta],
) -> None:
    """Pre-computes tile and frame extraction dimensions for all animations."""
    if not global_sheet:
        return
    base_w: int = global_sheet.width() // max(1, global_columns)
    base_h: int = global_sheet.height() // max(1, global_rows)

    for meta in animations.values():
        meta.base_h = base_h
        meta.computed_w = meta.override_width if meta.override_width > 0 else base_w
        meta.computed_h = meta.override_height if meta.override_height > 0 else base_h


def get_frame(
    global_sheet: Optional[QPixmap],
    current_mod_name: str,
    animations: dict[str, AnimationMeta],
    state: str,
    tick_index: int,
) -> Optional[QPixmap]:
    """Crops and returns the specific animation frame from the sprite sheet with caching."""
    if not global_sheet:
        return None
    anim_meta: Optional[AnimationMeta] = animations.get(state)
    if anim_meta is None:
        return None

    total_play_frames: int = max(1, (anim_meta.end_frame - anim_meta.start_frame) + 1)

    mapped_index: int = 0
    if anim_meta.loop:
        mapped_index = tick_index % total_play_frames
    else:
        mapped_index = min(tick_index, total_play_frames - 1)

    if anim_meta.reverse:
        mapped_index = (total_play_frames - 1) - mapped_index

    actual_sheet_index: int = anim_meta.start_frame + mapped_index

    final_w: int = anim_meta.computed_w
    final_h: int = anim_meta.computed_h

    x_pos: int = (actual_sheet_index * final_w) + anim_meta.offset_x
    y_pos: int = (anim_meta.row * anim_meta.base_h) + anim_meta.offset_y

    crop_rect = QRect(x_pos, y_pos, final_w, final_h)
    safe_rect: QRect = crop_rect.intersected(global_sheet.rect())

    if safe_rect.isEmpty(): return None

    cache_key: CacheKey = (
        current_mod_name,
        safe_rect.x(),
        safe_rect.y(),
        safe_rect.width(),
        safe_rect.height(),
    )

    if cache_key in shared_frame_cache:
        return shared_frame_cache[cache_key]

    frame: QPixmap = global_sheet.copy(safe_rect)
    shared_frame_cache[cache_key] = frame

    return frame


def bake_sprite_sheet(
    mods_dir: Path,
    current_mod_folder: str,
    global_sheet: Optional[QPixmap],
    global_columns: int,
    global_rows: int,
    animations: dict[str, AnimationMeta],
    save_callback: Callable[[], None],
) -> tuple[bool, Optional[QPixmap]]:
    """Permanently bakes all crop settings into a new optimized sprite sheet file."""
    if not global_sheet:
        return False, None

    cols: int = max(1, global_columns)
    rows: int = max(1, global_rows)
    base_w: int = global_sheet.width() // cols
    base_h: int = global_sheet.height() // rows

    new_cell_w, new_cell_h = 1, 1
    for meta in animations.values():
        w: int = meta.override_width if meta.override_width > 0 else base_w
        h: int = meta.override_height if meta.override_height > 0 else base_h
        new_cell_w: int = max(new_cell_w, w)
        new_cell_h: int = max(new_cell_h, h)

    new_sheet = QPixmap(new_cell_w * cols, new_cell_h * rows)
    new_sheet.fill(Qt.GlobalColor.transparent)
    painter = QPainter(new_sheet)

    painted_cells: set[tuple[int, int]] = set()

    for _, meta in animations.items():
        w = meta.override_width if meta.override_width > 0 else base_w
        h = meta.override_height if meta.override_height > 0 else base_h

        for sheet_idx in range(meta.start_frame, meta.end_frame + 1):
            cell_key: tuple[int, int] = (meta.row, sheet_idx)
            if cell_key in painted_cells:
                continue

            x_pos: int = (sheet_idx * w) + meta.offset_x
            y_pos: int = (meta.row * base_h) + meta.offset_y
            crop_rect = QRect(x_pos, y_pos, w, h).intersected(global_sheet.rect())

            if not crop_rect.isEmpty():
                frame: QPixmap = global_sheet.copy(crop_rect)
                dest_x: int = (sheet_idx * new_cell_w) + ((new_cell_w - frame.width()) // 2)
                dest_y: int = (meta.row * new_cell_h) + ((new_cell_h - frame.height()) // 2)
                painter.drawPixmap(dest_x, dest_y, frame)

            painted_cells.add(cell_key)

    painter.end()

    mod_path: Path = mods_dir / current_mod_folder
    sprite_path: Path = mod_path / "sprite_sheet.png"
    success: bool = new_sheet.save(str(sprite_path), "PNG")
    if not success:
        return False, None

    clear_shared_cache()

    for meta in animations.values():
        meta.offset_x = 0
        meta.offset_y = 0
        meta.override_width = 0
        meta.override_height = 0

    save_callback()
    return True, new_sheet


from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QPoint, QRect

from pytoningans.core.constants import EntityType, ItemState

if TYPE_CHECKING:
    from pytoningans.core.constants import AnimationMeta


def get_frame_physics(
    animations: dict[str, AnimationMeta],
    state: str,
    tick_index: int,
    is_static: bool = False,
    entity_type: str = EntityType.ENTITY.value,
) -> tuple[QPoint, QRect]:
    """Returns the (Anchor Point, Hitbox Rect) for the current frame."""
    anim_meta: Optional[AnimationMeta] = animations.get(state)
    if is_static:
        if anim_meta is None:
            anim_meta = (
                animations.get(ItemState.IDLE.value)
                or animations.get("idle")
                or animations.get("default")
                or next(iter(animations.values()), None)
            )
        if anim_meta is None:
            return QPoint(0, 0), QRect(0, 0, 50, 50)
        hw = anim_meta.hitbox_w if anim_meta.hitbox_w > 0 else anim_meta.computed_w
        hh = anim_meta.hitbox_h if anim_meta.hitbox_h > 0 else anim_meta.computed_h
        return QPoint(anim_meta.anchor_x, anim_meta.anchor_y), QRect(
            anim_meta.hitbox_x, anim_meta.hitbox_y, hw, hh
        )

    # Fallback defaults if state doesn't exist
    if anim_meta is None:
        return QPoint(0, 0), QRect(0, 0, 50, 50)

    total_play_frames: int = max(1, (anim_meta.end_frame - anim_meta.start_frame) + 1)

    # Calculate exactly which relative frame index we are playing
    mapped_index: int = (
        tick_index % total_play_frames
        if anim_meta.loop else
        min(tick_index, total_play_frames - 1)
    )
    if anim_meta.reverse:
        mapped_index = (total_play_frames - 1) - mapped_index

    # Start with the state's baseline physics
    ax, ay = anim_meta.anchor_x, anim_meta.anchor_y
    hx, hy = anim_meta.hitbox_x, anim_meta.hitbox_y
    hw, hh = anim_meta.hitbox_w, anim_meta.hitbox_h

    # Apply per-frame overrides if the user edited this specific frame
    frame_key: str = str(mapped_index)
    if frame_key in anim_meta.frame_overrides:
        override = anim_meta.frame_overrides[frame_key]
        ax = override.get("anchor_x", ax)
        ay = override.get("anchor_y", ay)
        hx = override.get("hitbox_x", hx)
        hy = override.get("hitbox_y", hy)
        hw = override.get("hitbox_w", hw)
        hh = override.get("hitbox_h", hh)

    # If hitbox width/height are 0 (unconfigured), default to the full image cell
    if hw == 0 or hh == 0:
        hw = anim_meta.computed_w
        hh = anim_meta.computed_h

    return QPoint(ax, ay), QRect(hx, hy, hw, hh)


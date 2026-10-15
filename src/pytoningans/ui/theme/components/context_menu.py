from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tokens import ThemePalette


def get_context_menu_styles(p: ThemePalette) -> str:
    """Returns EntityContextMenu card, title, badges, and container styles."""
    return f"""
QFrame#ContextMenuCard {{
    background-color: {p.context_card_bg};
    border: 1px solid {p.context_card_border};
    border-radius: 8px;
}}

QLabel#ContextMenuTitle {{
    font-weight: bold;
    font-size: 14px;
    color: {p.context_title};
}}

QLabel#ContextMenuSubtitle {{
    color: {p.context_subtitle};
    font-size: 11px;
}}

QLabel#ContextMenuSection {{
    font-weight: bold;
    color: {p.context_section};
    font-size: 12px;
}}

QLabel#ContextMenuTagBadge {{
    background-color: {p.tag_badge_bg};
    color: {p.tag_badge_text};
    border: 1px solid {p.tag_badge_border};
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: bold;
}}

QScrollArea#ContextMenuScrollArea,
QScrollArea#ContextMenuTagsScroll {{
    background: transparent;
    border: none;
}}

QWidget#ContextMenuActionsContainer,
QWidget#ContextMenuTagsContainer {{
    background: transparent;
}}
"""


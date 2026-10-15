from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tokens import ThemePalette


def get_menu_styles(p: ThemePalette) -> str:
    """Returns QMenu, MenuSeparator, and ActionRow styles."""
    return f"""
QMenu {{
    background-color: {p.menu_bg};
    border: 1px solid {p.menu_border};
    border-radius: 4px;
    padding: 4px 0px;
}}

QMenu::item {{
    padding: 6px 24px;
    color: {p.menu_item_text};
}}

QMenu::item:selected {{
    background-color: {p.menu_item_selected_bg};
    color: {p.menu_item_selected_text};
}}

QFrame#MenuSeparator {{
    border: none;
    border-top: 1px solid {p.menu_separator};
    max-height: 1px;
}}

QFrame#ActionRow {{
    background-color: {p.action_row_bg};
    border: 1px solid {p.action_row_border};
    border-radius: 6px;
}}
"""


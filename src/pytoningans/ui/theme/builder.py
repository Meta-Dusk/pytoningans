from __future__ import annotations

from .components import (
    get_base_styles,
    get_button_styles,
    get_context_menu_styles,
    get_menu_styles,
    get_overlay_styles,
    get_table_styles,
    get_container_styles,
)
from .tokens import ThemePalette


def build_theme(palette: ThemePalette) -> str:
    """Builds a complete QSS stylesheet string for the specified theme palette."""
    return "\n".join([
        get_base_styles(palette),
        get_button_styles(palette),
        get_table_styles(palette),
        get_menu_styles(palette),
        get_overlay_styles(palette),
        get_context_menu_styles(palette),
        get_container_styles(palette),
    ])



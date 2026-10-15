"""UI Theme styling system with typed tokens and modular components."""
from .builder import build_theme
from .tokens import DARK_PALETTE, LIGHT_PALETTE, ThemePalette

LIGHT_THEME: str = build_theme(LIGHT_PALETTE)
DARK_THEME: str = build_theme(DARK_PALETTE)


def get_theme(name: str = "dark") -> str:
    """Returns the rendered QSS stylesheet for the named theme ('dark' or 'light')."""
    if name.lower() == "light":
        return LIGHT_THEME
    return DARK_THEME


__all__ = [
    "LIGHT_THEME",
    "DARK_THEME",
    "ThemePalette",
    "LIGHT_PALETTE",
    "DARK_PALETTE",
    "build_theme",
    "get_theme",
]


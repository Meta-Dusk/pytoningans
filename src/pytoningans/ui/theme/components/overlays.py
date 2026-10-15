from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tokens import ThemePalette


def get_overlay_styles(p: ThemePalette) -> str:
    """Returns TitleBar, ToolTip, and SpeechBubble styles."""
    return f"""
QLabel#ToolTipText {{
    color: {p.tooltip_text};
    font-size: 12px;
}}

QWidget#ToolTipLabel {{
    background-color: {p.tooltip_bg};
    border: 1px solid {p.tooltip_border};
    border-radius: 6px;
}}

QWidget#CustomTitleBar {{
    background-color: {p.titlebar_bg};
    border: 1px solid {p.titlebar_border};
}}

QLabel#TitleBarText {{
    color: {p.titlebar_text};
    font-weight: bold; 
}}

QLabel#TitleBarVersion {{
    color: {p.titlebar_version};
    font-size: 11px;
    font-weight: normal;
    padding-left: 2px;
}}

#SpeechBubbleLabel {{
    background-color: {p.speech_bubble_bg};
    color: {p.speech_bubble_text};
    border: 2px solid {p.speech_bubble_border};
    border-radius: 8px;
    padding: 8px;
    font-family: 'Pixel Code', monospace;
    font-size: 14px;
}}
"""


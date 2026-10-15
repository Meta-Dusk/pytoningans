from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tokens import ThemePalette


def get_button_styles(p: ThemePalette) -> str:
    """Returns QPushButton and variant (Danger, TitleBar, RowBtn) styles."""
    return f"""
QPushButton {{
    background-color: {p.btn_bg};
    border: 1px solid {p.btn_border};
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {p.btn_hover_bg};
    border: 1px solid {p.btn_hover_border};
}}

QPushButton:pressed {{
    background-color: {p.btn_pressed_bg};
}}

QPushButton:disabled {{
    background-color: {p.btn_disabled_bg};
    border: 1px solid {p.btn_disabled_border};
    color: {p.btn_disabled_text};
}}

QPushButton#RowBtn {{
    padding: 3px 10px;
    font-size: 12px;
}}

QPushButton#DangerBtn {{
    background-color: {p.danger_btn_bg};
    border: 1px solid {p.danger_btn_border};
    color: {p.danger_btn_text};
    font-weight: 500;
}}

QPushButton#DangerBtn:hover {{
    background-color: {p.danger_btn_hover_bg};
    border: 1px solid {p.danger_btn_hover_border};
    color: #ffffff;
}}

QPushButton#DangerBtn:pressed {{
    background-color: {p.danger_btn_pressed_bg};
}}

QPushButton#DangerBtn:disabled {{
    background-color: {p.btn_disabled_bg};
    border: 1px solid {p.btn_disabled_border};
    color: {p.btn_disabled_text};
}}

QPushButton#TitleBarBtn {{ 
    background: transparent; 
    border: none; 
    color: {p.titlebar_btn_color}; 
    border-radius: 0px; 
    padding: 0px; 
    font-size: 14px; 
    font-family: 'Pixel Code', monospace;
}}

QPushButton#TitleBarBtn:hover {{ 
    color: {p.titlebar_btn_hover_color}; 
}}

QPushButton#TitleBarCloseBtn {{ 
    background: transparent; 
    border: none; 
    color: {p.titlebar_btn_color}; 
    border-radius: 0px; 
    padding: 0px; 
    font-size: 14px; 
    font-family: 'Pixel Code', monospace;
}}

QPushButton#TitleBarCloseBtn:hover {{ 
    background-color: #e81123; 
    color: white; 
}}
"""


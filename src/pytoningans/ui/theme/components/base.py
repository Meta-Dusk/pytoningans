from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tokens import ThemePalette


def get_base_styles(p: ThemePalette) -> str:
    """Returns base QWidget, inputs, checkboxes, and label styles."""
    return f"""
QWidget {{
    background-color: {p.bg_base};
    color: {p.text_base};
    font-family: {p.font_family};
    font-size: {p.font_size};
}}

QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
    background-color: {p.input_bg};
    border: 1px solid {p.input_border};
    border-radius: 4px;
    padding: 4px 8px;
}}

QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{
    border: 1px solid {p.accent};
}}

QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{
    border: 1px solid {p.accent};
}}

QCheckBox {{
    color: {p.checkbox_text};
    spacing: 8px;
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {p.checkbox_indicator_border};
    border-radius: 4px;
    background-color: {p.checkbox_indicator_bg};
}}

QCheckBox::indicator:hover {{
    border: 1px solid {p.accent};
}}

QCheckBox::indicator:checked {{
    background-color: {p.checkbox_checked_bg};
    border: 1px solid {p.checkbox_checked_bg};
}}

QLabel {{
    color: {p.text_base};
    background: transparent;
    border: none;
}}

QLabel#HelperText {{
    color: {p.helper_text};
    font-style: italic;
}}

QLabel#BannerText {{
    font-weight: bold; 
    color: {p.banner_text}; 
    background-color: {p.banner_bg}; 
    padding: 5px;
}}

QLabel#PreviewTitle {{
    font-weight: bold; 
    color: {p.preview_title};
}}

QLabel#SectionHeader {{
    font-weight: bold;
    color: {p.section_header};
    font-size: 14px;
}}

QLabel#StatAliveLabel {{
    color: {p.stat_alive};
    font-weight: bold;
    font-size: 13px;
}}

QLabel#StatDeadLabel {{
    color: {p.stat_dead};
    font-weight: bold;
    font-size: 13px;
}}

QLabel#StatStructLabel {{
    color: {p.stat_struct};
    font-weight: bold;
    font-size: 13px;
}}
"""


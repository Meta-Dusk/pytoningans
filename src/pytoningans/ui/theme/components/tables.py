from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tokens import ThemePalette


def get_table_styles(p: ThemePalette) -> str:
    """Returns QTableWidget, QListWidget, and QHeaderView styles."""
    return f"""
QTableWidget {{
    background-color: {p.table_bg};
    alternate-background-color: {p.table_alt_bg};
    border: 1px solid {p.table_border};
    border-radius: 4px;
    gridline-color: {p.table_gridline};
    selection-background-color: {p.table_sel_bg};
    selection-color: {p.table_sel_text};
}}

QTableWidget::item {{
    padding: 5px 8px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {p.table_sel_bg};
    color: {p.table_sel_text};
}}

QListWidget {{
    background-color: {p.table_bg};
    alternate-background-color: {p.table_alt_bg};
    border: 1px solid {p.table_border};
    border-radius: 4px;
    selection-background-color: {p.table_sel_bg};
    selection-color: {p.table_sel_text};
    outline: none;
}}

QListWidget::item {{
    padding: 5px 8px;
    border: none;
    color: {p.text_base};
}}

QListWidget::item:selected {{
    background-color: {p.table_sel_bg};
    color: {p.table_sel_text};
}}

QListWidget::item:hover {{
    background-color: {p.list_hover_bg};
}}

QHeaderView::section {{
    background-color: {p.header_bg};
    color: {p.header_text};
    font-weight: bold;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid {p.header_border};
    border-bottom: 1px solid {p.header_border};
}}

QHeaderView::section:hover {{
    background-color: {p.header_hover_bg};
}}
"""


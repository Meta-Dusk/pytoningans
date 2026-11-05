"""Container, Tab, Card, and Badge theme style generators."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tokens import ThemePalette


def get_container_styles(p: ThemePalette) -> str:
    """Returns QSS styles for tabs, cards, status badges, and notification banners."""
    return f"""
/* --- Tab Widget and Bar --- */
QTabWidget::pane {{
    border: 1px solid {p.tab_pane_border};
    border-radius: 6px;
    background-color: {p.tab_pane_bg};
    padding: 10px;
}}

QTabBar::tab {{
    background: {p.tab_bg};
    border: 1px solid {p.tab_border};
    color: {p.tab_text};
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background: {p.tab_selected_bg};
    color: {p.tab_selected_text};
    font-weight: bold;
    border-bottom: 2px solid {p.accent};
}}

QTabBar::tab:hover {{
    background: {p.tab_hover_bg};
}}


/* --- Vertical Resize Handle & Splitter --- */
VerticalResizeHandle, QFrame#VerticalResizeHandle {{
    background-color: {p.tab_bg};
    border: 1px solid {p.card_border};
    border-top: none;
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
}}

VerticalResizeHandle:hover, QFrame#VerticalResizeHandle:hover {{
    background-color: {p.tab_hover_bg};
    border-color: {p.accent};
}}

QSplitter::handle:horizontal {{
    background-color: {p.tab_border};
    width: 6px;
    margin: 0px 2px;
    border-radius: 3px;
}}

QSplitter::handle:horizontal:hover {{
    background-color: {p.accent};
}}

/* --- Card Containers --- */
ModCardWidget, QFrame#CardWidget, QFrame#ModCardWidget {{
    background-color: {p.card_bg};
    border: 1px solid {p.card_border};
    border-radius: 8px;
    padding: 4px;
}}

ModCardWidget:hover, QFrame#CardWidget:hover, QFrame#ModCardWidget:hover {{
    border: 1px solid {p.card_hover_border};
    background-color: {p.card_hover_bg};
}}

/* --- Badges and Status Pills --- */
QLabel#BadgeWarning {{
    background-color: {p.badge_warning_bg};
    color: {p.badge_warning_text};
    border: 1px solid {p.badge_warning_border};
    font-weight: bold;
    font-size: 11px;
    border-radius: 4px;
    padding: 2px 6px;
}}

QLabel#BadgeSuccess {{
    background-color: {p.badge_success_bg};
    color: {p.badge_success_text};
    border: 1px solid {p.badge_success_border};
    font-weight: bold;
    font-size: 11px;
    border-radius: 4px;
    padding: 2px 6px;
}}

QLabel#BadgeInfo {{
    background-color: {p.badge_info_bg};
    color: {p.badge_info_text};
    border: 1px solid {p.badge_info_border};
    font-weight: bold;
    font-size: 11px;
    border-radius: 4px;
    padding: 2px 6px;
}}

QLabel#BadgeDanger {{
    background-color: {p.badge_danger_bg};
    color: {p.badge_danger_text};
    border: 1px solid {p.badge_danger_border};
    font-weight: bold;
    font-size: 11px;
    border-radius: 4px;
    padding: 2px 6px;
}}

QLabel#BadgePack {{
    background-color: {p.badge_pack_bg};
    color: white;
    font-weight: bold;
    font-size: 11px;
    border-radius: 4px;
    padding: 2px 5px;
}}

QLabel#BadgeStructure {{
    background-color: {p.badge_structure_bg};
    color: white;
    font-weight: bold;
    font-size: 11px;
    border-radius: 4px;
    padding: 2px 5px;
}}

QLabel#BadgeItem {{
    background-color: {p.badge_item_bg};
    color: white;
    font-weight: bold;
    font-size: 11px;
    border-radius: 4px;
    padding: 2px 5px;
}}

QLabel#BadgeEntity {{
    background-color: {p.badge_entity_bg};
    color: white;
    font-weight: bold;
    font-size: 11px;
    border-radius: 4px;
    padding: 2px 5px;
}}

QLabel#StatusBadgeOnline {{
    color: {p.badge_success_text};
    font-weight: bold;
    font-size: 11px;
    background-color: {p.badge_success_bg};
    border-radius: 4px;
    padding: 4px 8px;
}}

QLabel#StatusBadgeOffline {{
    color: {p.badge_info_text};
    font-weight: bold;
    font-size: 11px;
    background-color: {p.badge_info_bg};
    border-radius: 4px;
    padding: 4px 8px;
}}

QLabel#BadgeLocal {{
    background-color: rgba(203, 166, 247, 0.2);
    color: #cba6f7;
    border: 1px solid #cba6f7;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: bold;
}}

/* --- Banners and Verification Frames --- */
QLabel#UserBanner {{
    background-color: {p.badge_info_bg};
    color: {p.badge_info_text};
    border: 1px solid {p.badge_info_border};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 11px;
}}

QLabel#ModeBanner {{
    background-color: {p.input_bg};
    color: {p.helper_text};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}

QLabel#ModeBannerActive {{
    background-color: {p.badge_info_bg};
    color: {p.badge_info_text};
    border: 1px solid {p.badge_info_border};
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: bold;
    font-size: 11px;
}}

QFrame#SecurityClean {{
    background-color: {p.badge_success_bg};
    border: 1px solid {p.badge_success_border};
    border-radius: 4px;
}}

QFrame#SecurityWarning {{
    background-color: {p.badge_warning_bg};
    border: 1px solid {p.badge_warning_border};
    border-radius: 4px;
}}

QFrame#SecurityDangerous {{
    background-color: {p.badge_danger_bg};
    border: 1px solid {p.badge_danger_border};
    border-radius: 4px;
}}

/* --- Progress Bar / Loading Indicator --- */
QProgressBar#IndeterminateBar {{
    border: none;
    border-radius: 2px;
    background-color: {p.input_bg};
    max-height: 4px;
    text-align: center;
}}

QProgressBar#IndeterminateBar::chunk {{
    background-color: {p.accent};
    border-radius: 2px;
}}
"""


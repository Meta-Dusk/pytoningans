from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemePalette:
    """Strongly typed color tokens and typography for the UI theme."""

    # General / Base
    bg_base: str
    text_base: str
    font_family: str
    font_size: str

    # Inputs / Controls
    input_bg: str
    input_border: str
    accent: str
    checkbox_text: str
    checkbox_indicator_bg: str
    checkbox_indicator_border: str
    checkbox_checked_bg: str

    # Tables / Lists
    table_bg: str
    table_alt_bg: str
    table_border: str
    table_gridline: str
    table_sel_bg: str
    table_sel_text: str
    list_hover_bg: str
    header_bg: str
    header_text: str
    header_border: str
    header_hover_bg: str

    # Labels and Headers
    helper_text: str
    banner_text: str
    banner_bg: str
    preview_title: str
    section_header: str
    stat_alive: str
    stat_dead: str
    stat_struct: str

    # Standard Buttons
    btn_bg: str
    btn_border: str
    btn_hover_bg: str
    btn_hover_border: str
    btn_pressed_bg: str
    btn_disabled_bg: str
    btn_disabled_border: str
    btn_disabled_text: str

    # Danger Buttons
    danger_btn_bg: str
    danger_btn_border: str
    danger_btn_text: str
    danger_btn_hover_bg: str
    danger_btn_hover_border: str
    danger_btn_pressed_bg: str

    # Custom Title Bar
    titlebar_bg: str
    titlebar_border: str
    titlebar_text: str
    titlebar_version: str
    titlebar_btn_color: str
    titlebar_btn_hover_color: str

    # Tooltip and Speech Bubble
    tooltip_bg: str
    tooltip_border: str
    tooltip_text: str
    speech_bubble_bg: str
    speech_bubble_text: str
    speech_bubble_border: str

    # Menus and Action Rows
    menu_bg: str
    menu_border: str
    menu_item_text: str
    menu_item_selected_bg: str
    menu_item_selected_text: str
    menu_separator: str
    action_row_bg: str
    action_row_border: str

    # Context Menu Card
    context_card_bg: str
    context_card_border: str
    context_title: str
    context_subtitle: str
    context_section: str
    tag_badge_bg: str
    tag_badge_text: str
    tag_badge_border: str


LIGHT_PALETTE = ThemePalette(
    # General / Base
    bg_base="#f9f9f9",
    text_base="#1e1e1e",
    font_family="'Pixel Code', monospace",
    font_size="14px",

    # Inputs / Controls
    input_bg="#ffffff",
    input_border="#d1d1d1",
    accent="#0078d4",
    checkbox_text="#1e1e1e",
    checkbox_indicator_bg="#ffffff",
    checkbox_indicator_border="#d1d1d1",
    checkbox_checked_bg="#0078d4",

    # Tables / Lists
    table_bg="#ffffff",
    table_alt_bg="#f7f7f7",
    table_border="#d1d1d1",
    table_gridline="#f0f0f0",
    table_sel_bg="#e3f2fd",
    table_sel_text="#0d47a1",
    list_hover_bg="#f0f0f0",
    header_bg="#f0f0f0",
    header_text="#333333",
    header_border="#dcdcdc",
    header_hover_bg="#e5e5e5",

    # Labels and Headers
    helper_text="#666666",
    banner_text="#444444",
    banner_bg="#eeeeee",
    preview_title="#666666",
    section_header="#333333",
    stat_alive="#2e7d32",
    stat_dead="#c62828",
    stat_struct="#1565c0",

    # Standard Buttons
    btn_bg="#ffffff",
    btn_border="#d1d1d1",
    btn_hover_bg="#f0f0f0",
    btn_hover_border="#0078d4",
    btn_pressed_bg="#e5e5e5",
    btn_disabled_bg="#f5f5f5",
    btn_disabled_border="#e5e5e5",
    btn_disabled_text="#a0a0a0",

    # Danger Buttons
    danger_btn_bg="#ffffff",
    danger_btn_border="#f5c2c7",
    danger_btn_text="#c62828",
    danger_btn_hover_bg="#dc3545",
    danger_btn_hover_border="#dc3545",
    danger_btn_pressed_bg="#b02a37",

    # Custom Title Bar
    titlebar_bg="#e5e5e5",
    titlebar_border="#b0b0b0",
    titlebar_text="#1e1e1e",
    titlebar_version="#666666",
    titlebar_btn_color="#666666",
    titlebar_btn_hover_color="black",

    # Tooltip and Speech Bubble
    tooltip_bg="#ffffff",
    tooltip_border="#dcdcdc",
    tooltip_text="#1e1e1e",
    speech_bubble_bg="#FFFFFF",
    speech_bubble_text="#000000",
    speech_bubble_border="#333333",

    # Menus and Action Rows
    menu_bg="#ffffff",
    menu_border="#d1d1d1",
    menu_item_text="#1e1e1e",
    menu_item_selected_bg="#f0f0f0",
    menu_item_selected_text="#0078d4",
    menu_separator="#d1d1d1",
    action_row_bg="#f2f2f2",
    action_row_border="#dcdcdc",

    # Context Menu Card
    context_card_bg="#ffffff",
    context_card_border="#d1d1d1",
    context_title="#1e1e1e",
    context_subtitle="#666666",
    context_section="#0078d4",
    tag_badge_bg="rgba(0, 120, 212, 0.12)",
    tag_badge_text="#0078d4",
    tag_badge_border="rgba(0, 120, 212, 0.35)",
)


DARK_PALETTE = ThemePalette(
    # General / Base
    bg_base="#202020",
    text_base="#f3f3f3",
    font_family="'Pixel Code', monospace",
    font_size="14px",

    # Inputs / Controls
    input_bg="#2d2d2d",
    input_border="#3d3d3d",
    accent="#4a90e2",
    checkbox_text="#e0e0e0",
    checkbox_indicator_bg="#252526",
    checkbox_indicator_border="#4d4d4d",
    checkbox_checked_bg="#0078d4",

    # Tables / Lists
    table_bg="#252525",
    table_alt_bg="#2a2a2a",
    table_border="#3d3d3d",
    table_gridline="#333333",
    table_sel_bg="#1e3a5f",
    table_sel_text="#ffffff",
    list_hover_bg="#303030",
    header_bg="#2d2d2d",
    header_text="#e0e0e0",
    header_border="#3d3d3d",
    header_hover_bg="#383838",

    # Labels and Headers
    helper_text="#aaaaaa",
    banner_text="#e0e0e0",
    banner_bg="#333333",
    preview_title="#aaaaaa",
    section_header="#cccccc",
    stat_alive="#4caf50",
    stat_dead="#ef5350",
    stat_struct="#42a5f5",

    # Standard Buttons
    btn_bg="#2d2d2d",
    btn_border="#3d3d3d",
    btn_hover_bg="#383838",
    btn_hover_border="#4a90e2",
    btn_pressed_bg="#1e1e1e",
    btn_disabled_bg="#222222",
    btn_disabled_border="#2a2a2a",
    btn_disabled_text="#666666",

    # Danger Buttons
    danger_btn_bg="#2d2020",
    danger_btn_border="#4d2d2d",
    danger_btn_text="#ef5350",
    danger_btn_hover_bg="#e53935",
    danger_btn_hover_border="#e53935",
    danger_btn_pressed_bg="#b71c1c",

    # Custom Title Bar
    titlebar_bg="#1a1a1a",
    titlebar_border="#4a4a4a",
    titlebar_text="#f3f3f3",
    titlebar_version="#888888",
    titlebar_btn_color="#aaaaaa",
    titlebar_btn_hover_color="white",

    # Tooltip and Speech Bubble
    tooltip_bg="#2b2b2b",
    tooltip_border="#3d3d3d",
    tooltip_text="#f3f3f3",
    speech_bubble_bg="#2D2D2D",
    speech_bubble_text="#FFFFFF",
    speech_bubble_border="#555555",

    # Menus and Action Rows
    menu_bg="#2b2b2b",
    menu_border="#3d3d3d",
    menu_item_text="#f3f3f3",
    menu_item_selected_bg="#383838",
    menu_item_selected_text="#4a90e2",
    menu_separator="#3d3d3d",
    action_row_bg="#262626",
    action_row_border="#363636",

    # Context Menu Card
    context_card_bg="#202020",
    context_card_border="#3d3d3d",
    context_title="#f3f3f3",
    context_subtitle="#aaaaaa",
    context_section="#4a90e2",
    tag_badge_bg="rgba(74, 144, 226, 0.18)",
    tag_badge_text="#4a90e2",
    tag_badge_border="rgba(74, 144, 226, 0.45)",
)


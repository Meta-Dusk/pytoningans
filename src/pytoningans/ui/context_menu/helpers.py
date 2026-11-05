from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from pytoningans.ui.tool_tip import ToolTipLabel


def create_info_row(label_text: str, tooltip_text: str) -> QWidget:
    """Helper creating a compact label with a [?] custom tooltip helper icon."""
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(6)
    lbl = QLabel(label_text); lbl.setObjectName("ContextMenuSection")
    layout.addWidget(lbl)
    layout.addWidget(ToolTipLabel(text="[?]", tooltip_text=tooltip_text))
    layout.addStretch()
    return widget


def create_separator() -> QFrame:
    """Creates a standardized theme divider line."""
    sep = QFrame(); sep.setObjectName("MenuSeparator")
    sep.setFrameShape(QFrame.Shape.HLine)
    return sep

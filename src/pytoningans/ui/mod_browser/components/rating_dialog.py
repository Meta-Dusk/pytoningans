"""
PyToNingans Mod Browser - Rating Dialog
=======================================
Interactive modal dialog allowing users to score mods on a 1-10 scale.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QWidget
)

from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.utils.assets import get_main_icon
from ..models import CommunityModItem


RATING_DESCRIPTIONS: dict[int, str] = {
    10: "10 / 10 — Masterpiece! ★★★★★",
    9: "9 / 10 — Fantastic! ★★★★★",
    8: "8 / 10 — Great! ★★★★☆",
    7: "7 / 10 — Good ★★★★☆",
    6: "6 / 10 — Above Average ★★★☆☆",
    5: "5 / 10 — Average ★★★☆☆",
    4: "4 / 10 — Below Average ★★☆☆☆",
    3: "3 / 10 — Needs Improvement ★★☆☆☆",
    2: "2 / 10 — Buggy ★☆☆☆☆",
    1: "1 / 10 — Poor ☆☆☆☆☆",
}


class RatingDialog(QDialog):
    """Modal dialog allowing users to submit a 1-10 rating for a community mod."""

    def __init__(self, item: CommunityModItem, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.item: CommunityModItem = item
        self.selected_rating: int = 10

        self.setWindowTitle(f"Rate {self.item.name}")
        self.setWindowIcon(get_main_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(420, 260); self.setFixedSize(420, 260)

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, f"Rate Mod: {self.item.name}")
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(12)

        prompt_lbl = QLabel(
            f"How would you rate <b>{self.item.name}</b> by {self.item.author}?"
        )
        prompt_lbl.setWordWrap(True)
        layout.addWidget(prompt_lbl)

        # Large Score Label
        self.score_label = QLabel(RATING_DESCRIPTIONS[10])
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #f9e2af; margin: 6px 0;"
        )
        layout.addWidget(self.score_label)

        # 1-10 Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 10); self.slider.setValue(10)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        submit_btn = QPushButton("Submit Rating")
        submit_btn.setObjectName("SuccessBtn"); submit_btn.clicked.connect(self._on_submit)
        btn_layout.addWidget(submit_btn)

        layout.addLayout(btn_layout)
        main_layout.addWidget(content)

    def _on_slider_changed(self, value: int) -> None:
        self.selected_rating = value
        self.score_label.setText(RATING_DESCRIPTIONS.get(value, f"{value} / 10.0"))

    def _on_submit(self) -> None:
        self.accept()


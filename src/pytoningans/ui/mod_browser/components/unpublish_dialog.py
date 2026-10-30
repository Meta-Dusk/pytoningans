"""
PyToNingans Mod Browser - Unpublish Dialog
=======================================
Confirmation dialog for unpublishing a mod/modpack
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)

from ...title_bar import CustomTitleBar
from pytoningans.utils.assets import get_main_icon

if TYPE_CHECKING:
    from ..models import CommunityModItem


class UnpublishModDialog(QDialog):
    """Modal dialog allowing users to _unpublish_ their already published community mod."""

    def __init__(self, mod_item: CommunityModItem, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.mod_item: CommunityModItem = mod_item

        self.setWindowTitle(f"Unpublish {self.mod_item.name}")
        self.setWindowIcon(get_main_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(420, 260); self.setFixedSize(420, 260)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(
            self, "Confirm Unpublishing",
            show_version=False, can_minimize=False, can_maximize=False
        )
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(12)
        mod_pack_type: str = "modpack" if self.mod_item.is_pack else "mod"

        prompt_lbl = QLabel(
            f"Unpublish {mod_pack_type} <b>\"{self.mod_item.name}\"</b> "
            "from the community catalogue?"
        )
        prompt_lbl.setWordWrap(True)
        layout.addWidget(prompt_lbl)
        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        submit_btn = QPushButton(f"Unpublish {mod_pack_type.capitalize()}")
        submit_btn.setObjectName("DangerBtn"); submit_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(submit_btn)

        layout.addLayout(btn_layout)
        main_layout.addWidget(content)

    def _on_confirm(self) -> None:
        self.accept()

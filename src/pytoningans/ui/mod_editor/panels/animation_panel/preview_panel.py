from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QFrame
)
from PySide6.QtCore import Qt

from pytoningans.ui.mod_editor.components import PreviewLabel


class AnimationPreviewPanel(QWidget):
    """Panel containing the live animation preview viewport and zoom controls."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Live Animation Preview")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PreviewTitle")
        
        self.preview_label = PreviewLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(150)
        self.preview_label.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        
        preview_ctrls = QHBoxLayout()
        self.preview_zoom_spin = QSpinBox()
        self.preview_zoom_spin.setPrefix("Zoom: ")
        self.preview_zoom_spin.setSuffix("x")
        self.preview_zoom_spin.setRange(1, 20)
        self.preview_zoom_spin.setValue(self.preview_label.zoom)

        self.preview_reset_btn = QPushButton("Reset View")
        self.restart_btn = QPushButton("Restart Animation")

        preview_ctrls.addWidget(self.preview_zoom_spin)
        preview_ctrls.addWidget(self.preview_reset_btn)
        preview_ctrls.addWidget(self.restart_btn)

        layout.addWidget(title)
        layout.addWidget(self.preview_label)
        layout.addLayout(preview_ctrls)


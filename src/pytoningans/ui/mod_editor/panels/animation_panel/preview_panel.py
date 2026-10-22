from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QFrame
)
from PySide6.QtCore import Qt

from pytoningans.ui.mod_editor.components import PreviewLabel, VerticalResizeHandle


class AnimationPreviewPanel(QWidget):
    """Panel containing the live animation preview viewport, interactive resize handle, and zoom controls."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        
        title = QLabel("Live Animation Preview")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PreviewTitle")
        
        self.preview_label = PreviewLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFixedHeight(220)
        self.preview_label.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        
        self.resize_handle = VerticalResizeHandle(
            self.preview_label, default_height=220, min_height=120, max_height=750
        )
        self.resize_handle.height_changed.connect(self._on_height_changed)
        
        preview_ctrls = QHBoxLayout()
        preview_ctrls.setContentsMargins(0, 6, 0, 0)
        self.preview_zoom_spin = QSpinBox()
        self.preview_zoom_spin.setPrefix("Zoom: "); self.preview_zoom_spin.setSuffix("x")
        self.preview_zoom_spin.setRange(1, 20)
        self.preview_zoom_spin.setValue(self.preview_label.zoom)

        self.preview_reset_btn = QPushButton("⛶ Reset View")
        self.restart_btn = QPushButton("⭮ Restart Animation")
        self.expand_btn = QPushButton("[+] Expand")
        self.expand_btn.setToolTip(
            "Quickly toggle between standard (220px) and tall (420px) preview height"
        )
        self.expand_btn.clicked.connect(self._toggle_expand)

        preview_ctrls.addWidget(self.preview_zoom_spin)
        preview_ctrls.addWidget(self.preview_reset_btn)
        preview_ctrls.addWidget(self.restart_btn)
        preview_ctrls.addWidget(self.expand_btn)

        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.resize_handle)
        layout.addLayout(preview_ctrls)

    def _toggle_expand(self) -> None:
        if self.preview_label.height() >= 360:
            self.preview_label.setFixedHeight(220)
            self.expand_btn.setText("[+] Expand")
        else:
            self.preview_label.setFixedHeight(420)
            self.expand_btn.setText("[-] Compact")

    def _on_height_changed(self, height: int) -> None:
        if height >= 360:
            self.expand_btn.setText("[-] Compact")
        else:
            self.expand_btn.setText("[+] Expand")

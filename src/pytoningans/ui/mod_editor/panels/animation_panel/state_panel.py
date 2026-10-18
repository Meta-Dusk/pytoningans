from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QPushButton,
    QFormLayout, QSpinBox
)

from pytoningans.ui.mod_editor.components import (
    CollapsibleSection, create_info_label, create_spinbox, create_info_widget
)


class StateConfigPanel(QWidget):
    """Panel containing animation state selection, swap, crop, and frame configuration."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.state_section = CollapsibleSection("Animation State Config")
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(
            create_info_label(
                "State:",
                "The State of the Entity to edit the values for."
            )
        )
        
        self.state_combo = QComboBox()
        h_layout.addWidget(self.state_combo, stretch=1)
        
        self.copy_btn = QPushButton("Copy")
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setEnabled(False)
        
        h_layout.addWidget(self.copy_btn)
        h_layout.addWidget(self.paste_btn)
        self.state_section.content_layout.addLayout(h_layout)
        
        swap_layout = QHBoxLayout()
        swap_layout.addWidget(
            create_info_label(
                "Swap State Data With:",
                "Swaps all the data between the two selected States "
                "(the top and bottom combo boxes)."
            )
        )
        self.swap_combo = QComboBox()
        self.swap_btn = QPushButton("Swap")
        swap_layout.addWidget(self.swap_combo)
        swap_layout.addWidget(self.swap_btn)
        self.state_section.content_layout.addLayout(swap_layout)
        
        form = QFormLayout()
        self.row_spin: QSpinBox = create_spinbox(0, 100)
        self.start_spin: QSpinBox = create_spinbox(0, 100)
        self.end_spin: QSpinBox = create_spinbox(0, 100)
        self.loop_check = QCheckBox("Loop Animation")
        self.reverse_check = QCheckBox("Play in Reverse")
        
        crop_layout = QHBoxLayout()
        self.crop_check = QCheckBox("Interactive Crop")
        self.crop_check.setStyleSheet("font-weight: bold; color: #ff4444;")
        crop_check_info = create_info_widget(
            self.crop_check,
            "Shows a red outline as the cropping area. Resizeable by dragging its borders."
        )
        
        self.apply_all_btn = QPushButton("Apply to All")
        self.apply_all_btn.setStyleSheet("font-weight: bold;")
        
        self.bake_btn = QPushButton("Bake to File")
        self.bake_btn.setStyleSheet("background-color: #aa0000; color: white; font-weight: bold;")
        
        crop_layout.addWidget(self.apply_all_btn)
        crop_layout.addWidget(self.bake_btn)
        
        self.width_spin: QSpinBox = create_spinbox(0, 2048)
        self.height_spin: QSpinBox = create_spinbox(0, 2048)
        self.offset_x_spin: QSpinBox = create_spinbox(-2048, 2048)
        self.offset_y_spin: QSpinBox = create_spinbox(-2048, 2048)
        self.fps_spin: QSpinBox = create_spinbox(1, 60)
        
        form.addRow(
            create_info_label(
                "Mapped Row Index:",
                "The row index (from 0) where the animation frames are sourced from."
            ),
            self.row_spin
        )
        form.addRow(
            create_info_label(
                "Start Frame Index:",
                "The column index (from 0) where the animation begins."
            ),
            self.start_spin
        )
        form.addRow(
            create_info_label(
                "End Frame Index:",
                "The column index (from 0) where the animation ends."
            ),
            self.end_spin
        )
        form.addRow(self.loop_check, self.reverse_check)
        form.addRow(crop_check_info, crop_layout)
        form.addRow(
            create_info_label(
                "Override Width (px):",
                "Set above 0 to manually define this frame's width, ignoring the global grid."
            ),
            self.width_spin
        )
        form.addRow(
            create_info_label(
                "Override Height (px):",
                "Set above 0 to manually define this frame's height, ignoring the global grid."
            ),
            self.height_spin
        )
        form.addRow(
            create_info_label(
                "Offset X (px):",
                "Nudge the frame extraction boundary horizontally."
            ),
            self.offset_x_spin
        )
        form.addRow(
            create_info_label(
                "Offset Y (px):",
                "Nudge the frame extraction boundary vertically."
            ),
            self.offset_y_spin
        )
        form.addRow(
            create_info_label(
                "Playback Speed (FPS):",
                "How fast the animation plays. Higher means faster."
            ),
            self.fps_spin
        )
        
        self.state_section.content_layout.addLayout(form)
        layout.addWidget(self.state_section)


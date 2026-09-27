from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QSpinBox,
    QPushButton, QFormLayout, QFrame, QCheckBox
)
from PySide6.QtCore import Qt

from pytoningans.core.constants import PetState
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.tool_tip import ToolTipLabel

class ModEditorUI:
    """Handles ONLY visual drawing and layout structuring."""
    
    def setup_ui(self, window: QWidget) -> None:
        window.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        window.resize(850, 580)
        
        self.main_layout = QVBoxLayout(window)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(window, "Mod Editor")
        self.main_layout.addWidget(self.title_bar)
        
        content_widget = QWidget(window)
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(20, 15, 20, 20)
        self.content_layout.setSpacing(10)

        self._build_header()
        
        self.sheet_info_label = QLabel("Sheet: -- x -- px | Base Tile: -- x -- px")
        self.sheet_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sheet_info_label.setObjectName("BannerText")
        self.content_layout.addWidget(self.sheet_info_label)

        split_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()
        
        split_layout.addLayout(self.left_layout, stretch=1)
        split_layout.addLayout(self.right_layout, stretch=1)
        
        self.content_layout.addLayout(split_layout)

        self._build_mod_selection()
        self._build_global_settings()
        self._build_preview_area()
        self._build_state_overrides()

        self.save_btn = QPushButton("Save config.json")
        self.content_layout.addWidget(self.save_btn)
        
        self.main_layout.addWidget(content_widget)

    def _build_header(self) -> None:
        info_label = QLabel(
            "Grid automatically splits your sprite sheet.\n"
            "Ensure every state is mapped to a valid row.",
            alignment=Qt.AlignmentFlag.AlignCenter
        )
        info_label.setObjectName("HelperText")
        self.content_layout.addWidget(info_label)

    def _build_mod_selection(self) -> None:
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Target Mod:"))
        self.mod_combo = QComboBox()
        layout.addWidget(self.mod_combo)
        self.left_layout.addLayout(layout)

    def _build_global_settings(self) -> None:
        layout = QFormLayout()
        self.global_cols_spin = self._create_spinbox(1, 100)
        self.global_rows_spin = self._create_spinbox(1, 100)
        
        self.can_fly_check = QCheckBox("Enable Flight (Ignores Gravity)")
        
        lbl_cols = self._create_info_label("Total Sheet Columns:", "How many columns the entire sprite sheet is divided into evenly.")
        lbl_rows = self._create_info_label("Total Sheet Rows:", "How many rows the entire sprite sheet is divided into evenly.")
        
        layout.addRow(lbl_cols, self.global_cols_spin)
        layout.addRow(lbl_rows, self.global_rows_spin)
        layout.addRow("", self.can_fly_check)
        self.left_layout.addLayout(layout)

    def _build_state_overrides(self) -> None:
        layout = QHBoxLayout()
        layout.addWidget(QLabel("State Config:"))
        self.state_combo = QComboBox()
        layout.addWidget(self.state_combo)
        
        self.copy_btn = QPushButton("Copy")
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setEnabled(False) 

        layout.addWidget(self.copy_btn)
        layout.addWidget(self.paste_btn)
        self.right_layout.addLayout(layout)
        
        swap_layout = QHBoxLayout()
        swap_layout.addWidget(QLabel("Swap Data With:"))
        
        self.swap_combo = QComboBox()
        for state in PetState:
            self.swap_combo.addItem(state.value.capitalize(), userData=state)
            
        self.swap_btn = QPushButton("Swap")
        
        swap_layout.addWidget(self.swap_combo)
        swap_layout.addWidget(self.swap_btn)
        self.right_layout.addLayout(swap_layout)

        form = QFormLayout()
        self.row_spin = self._create_spinbox(0, 100)
        self.start_spin = self._create_spinbox(0, 100)
        self.end_spin = self._create_spinbox(0, 100)
        
        self.loop_check = QCheckBox("Loop Animation")
        self.reverse_check = QCheckBox("Play in Reverse")
        
        self.width_spin = self._create_spinbox(0, 2048)
        self.height_spin = self._create_spinbox(0, 2048)
        self.offset_x_spin = self._create_spinbox(-2048, 2048)
        self.offset_y_spin = self._create_spinbox(-2048, 2048)
        self.fps_spin = self._create_spinbox(1, 60)

        form.addRow(self._create_info_label("Mapped Row Index:", "..."), self.row_spin)
        form.addRow(self._create_info_label("Start Frame Index:", "The column index (from 0) where the animation begins."), self.start_spin)
        form.addRow(self._create_info_label("End Frame Index:", "The column index (from 0) where the animation ends."), self.end_spin)
        form.addRow("", self.loop_check)
        form.addRow("", self.reverse_check)
        form.addRow(self._create_info_label("Override Width (px):", "Set above 0 to manually define this frame's width, ignoring the global grid."), self.width_spin)
        form.addRow(self._create_info_label("Override Height (px):", "Set above 0 to manually define this frame's height, ignoring the global grid."), self.height_spin)
        form.addRow(self._create_info_label("Offset X (px):", "Nudge the frame extraction boundary horizontally."), self.offset_x_spin)
        form.addRow(self._create_info_label("Offset Y (px):", "Nudge the frame extraction boundary vertically."), self.offset_y_spin)
        form.addRow(self._create_info_label("Playback Speed (FPS):", "How fast the animation plays. Higher means faster."), self.fps_spin)
        
        self.right_layout.addLayout(form)
        self.right_layout.addStretch()

    def _build_preview_area(self) -> None:
        layout = QVBoxLayout()
        title = QLabel("Live Animation Preview")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PreviewTitle")
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(150)
        self.preview_label.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        
        self.restart_btn = QPushButton("Restart Animation")
        
        layout.addWidget(title)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.restart_btn)
        self.left_layout.addLayout(layout)
        self.left_layout.addStretch()

    def _create_spinbox(self, min_val: int, max_val: int, special_text: Optional[str] = None) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        if special_text:
            spin.setSpecialValueText(special_text)
        return spin
    
    def _create_info_label(self, text: str, tooltip_text: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(text)
        icon_lbl = ToolTipLabel(text="[?]", tooltip_text=tooltip_text)
        
        layout.addWidget(lbl)
        layout.addWidget(icon_lbl)
        layout.addStretch() 
        return widget
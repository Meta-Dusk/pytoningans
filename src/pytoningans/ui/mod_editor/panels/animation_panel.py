from dataclasses import replace
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, 
    QPushButton, QLabel, QFormLayout, QFrame
)
from PySide6.QtCore import Qt, QTimer

from pytoningans.core.constants import PetState, AnimationMeta
from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.components import CollapsibleSection, PreviewLabel
from pytoningans.ui.mod_editor.panels.behavior_panel import create_info_label, create_spinbox

class AnimationSubsystem:
    """Manages all animation-related UI panels, timers, and state bridging."""
    def __init__(self, controller: ModEditorController, dynamic_info_label: QLabel) -> None:
        self.controller = controller
        self.info_label = dynamic_info_label
        self._is_updating_ui = False
        self._copied_meta: Optional[AnimationMeta] = None
        self._preview_frame = 0
        
        self._preview_timer = QTimer()
        self._preview_timer.timeout.connect(self._update_preview)
        self._preview_timer.setInterval(100)
        
        self._build_grid_panel()
        self._build_preview_panel()
        self._build_debug_panel()
        self._build_state_panel()
        self._connect_signals()
        
        self._preview_timer.start()

    def load_data(self) -> None:
        self._is_updating_ui = True
        cols, rows = self.controller.get_global_grid()
        self.cols_spin.setValue(cols)
        self.rows_spin.setValue(rows)
        self._is_updating_ui = False
        
        self._refresh_dynamic_info()
        self._refresh_state_dropdown()
        self._on_state_changed()

    def _build_grid_panel(self) -> None:
        self.grid_panel = QWidget()
        layout = QVBoxLayout(self.grid_panel)
        layout.setContentsMargins(0,0,0,0)
        section = CollapsibleSection("Grid & Extraction Settings")
        form = QFormLayout()
        
        self.cols_spin = create_spinbox(1, 100)
        self.rows_spin = create_spinbox(1, 100)
        
        form.addRow(create_info_label("Columns:", "Total columns."), self.cols_spin)
        form.addRow(create_info_label("Rows:", "Total rows."), self.rows_spin)
        section.content_layout.addLayout(form)
        layout.addWidget(section)

    def _build_preview_panel(self) -> None:
        self.preview_panel = QWidget()
        layout = QVBoxLayout(self.preview_panel)
        layout.setContentsMargins(0,0,0,0)
        
        title = QLabel("Live Animation Preview")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PreviewTitle")
        
        self.preview_label = PreviewLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(150)
        self.preview_label.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        
        self.restart_btn = QPushButton("Restart Animation")
        
        layout.addWidget(title)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.restart_btn)

    def _build_debug_panel(self) -> None:
        self.debug_panel = QWidget()
        layout = QVBoxLayout(self.debug_panel)
        layout.setContentsMargins(0,0,0,0)
        section = CollapsibleSection("Debug Settings")
        sec_layout = QVBoxLayout()
        
        self.borders_check = QCheckBox("Show Sprite Borders (Blue)")
        
        sec_layout.addWidget(self.borders_check)
        section.content_layout.addLayout(sec_layout)
        layout.addWidget(section)

    def _build_state_panel(self) -> None:
        self.state_panel = QWidget()
        layout = QVBoxLayout(self.state_panel)
        layout.setContentsMargins(0,0,0,0)
        section = CollapsibleSection("Animation State Config")
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("State:"))
        self.state_combo = QComboBox()
        h_layout.addWidget(self.state_combo)
        self.copy_btn = QPushButton("Copy")
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setEnabled(False)
        h_layout.addWidget(self.copy_btn)
        h_layout.addWidget(self.paste_btn)
        section.content_layout.addLayout(h_layout)
        
        swap_layout = QHBoxLayout()
        swap_layout.addWidget(QLabel("Swap With:"))
        self.swap_combo = QComboBox()
        for state in PetState:
            self.swap_combo.addItem(state.value.capitalize(), userData=state)
        self.swap_btn = QPushButton("Swap")
        swap_layout.addWidget(self.swap_combo)
        swap_layout.addWidget(self.swap_btn)
        section.content_layout.addLayout(swap_layout)
        
        form = QFormLayout()
        self.row_spin = create_spinbox(0, 100)
        self.start_spin = create_spinbox(0, 100)
        self.end_spin = create_spinbox(0, 100)
        self.loop_check = QCheckBox("Loop Animation")
        self.reverse_check = QCheckBox("Play in Reverse")
        self.crop_check = QCheckBox("Enable Interactive Cropping")
        self.crop_check.setStyleSheet("font-weight: bold; color: #ff4444;")
        self.width_spin = create_spinbox(0, 2048)
        self.height_spin = create_spinbox(0, 2048)
        self.off_x_spin = create_spinbox(-2048, 2048)
        self.off_y_spin = create_spinbox(-2048, 2048)
        self.fps_spin = create_spinbox(1, 60)
        
        form.addRow("Mapped Row Index:", self.row_spin)
        form.addRow("Start Frame Index:", self.start_spin)
        form.addRow("End Frame Index:", self.end_spin)
        form.addRow("", self.loop_check)
        form.addRow("", self.reverse_check)
        form.addRow("", self.crop_check)
        form.addRow("Override Width:", self.width_spin)
        form.addRow("Override Height:", self.height_spin)
        form.addRow("Offset X:", self.off_x_spin)
        form.addRow("Offset Y:", self.off_y_spin)
        form.addRow("FPS:", self.fps_spin)
        
        section.content_layout.addLayout(form)
        layout.addWidget(section)
    
    def _connect_signals(self) -> None:
        self.cols_spin.valueChanged.connect(self._on_global_edited)
        self.rows_spin.valueChanged.connect(self._on_global_edited)
        
        self.state_combo.currentIndexChanged.connect(self._on_state_changed)
        self.copy_btn.clicked.connect(self._on_copy)
        self.paste_btn.clicked.connect(self._on_paste)
        self.swap_btn.clicked.connect(self._on_swap)
        self.restart_btn.clicked.connect(self._restart_preview)
        
        self.borders_check.stateChanged.connect(self._on_borders_toggled)
        self.crop_check.stateChanged.connect(self._on_crop_toggled)
        
        for widget in (self.row_spin, self.start_spin, self.end_spin, self.width_spin, 
                       self.height_spin, self.off_x_spin, self.off_y_spin, self.fps_spin):
            widget.valueChanged.connect(self._on_meta_edited)
        self.loop_check.stateChanged.connect(self._on_meta_edited)
        self.reverse_check.stateChanged.connect(self._on_meta_edited)
        self.preview_label.crop_updated.connect(self._on_crop_dragged)

    # --- Handlers ---
    def _refresh_dynamic_info(self) -> None:
        sw, sh, base_w, base_h = self.controller.get_sheet_info()
        self.info_label.setText(f"Sheet: {sw} x {sh} px | Base Tile: {base_w} x {base_h} px")
        self.width_spin.setSpecialValueText(f"0 (Auto: {base_w}px)")
        self.height_spin.setSpecialValueText(f"0 (Auto: {base_h}px)")

    def _refresh_state_dropdown(self) -> None:
        current = self.state_combo.currentData()
        self.state_combo.blockSignals(True)
        self.state_combo.clear()
        target_idx = 0
        for i, state in enumerate(PetState):
            exists, row = self.controller.has_mapped_row(state)
            self.state_combo.addItem(
                f"{state.value.capitalize()} [{'Row ' + str(row) if exists else 'Missing'}]",
                userData=state
            )
            if state == current: target_idx = i
        self.state_combo.setCurrentIndex(target_idx)
        self.state_combo.blockSignals(False)

    def _on_global_edited(self, *_) -> None:
        if self._is_updating_ui: return
        self.controller.update_global_grid(self.cols_spin.value(), self.rows_spin.value())
        self._refresh_dynamic_info()
        self._update_preview()

    def _on_state_changed(self, *_) -> None:
        state = self.state_combo.currentData()
        if not state: return
        meta = self.controller.get_meta(state)
        
        self._is_updating_ui = True
        self.row_spin.setValue(meta.row)
        self.start_spin.setValue(meta.start_frame)
        self.end_spin.setValue(meta.end_frame)
        self.loop_check.setChecked(meta.loop)
        self.reverse_check.setChecked(meta.reverse)
        self.width_spin.setValue(meta.override_width)
        self.height_spin.setValue(meta.override_height)
        self.off_x_spin.setValue(meta.offset_x)
        self.off_y_spin.setValue(meta.offset_y)
        self.fps_spin.setValue(meta.fps)
        self._is_updating_ui = False
        self._preview_timer.setInterval(1000 // max(1, meta.fps))

    def _on_meta_edited(self, *_) -> None:
        if self._is_updating_ui: return
        state = self.state_combo.currentData()
        if not state: return
        
        new_meta = AnimationMeta(
            row=self.row_spin.value(),
            start_frame=self.start_spin.value(),
            end_frame=self.end_spin.value(),
            loop=self.loop_check.isChecked(),
            reverse=self.reverse_check.isChecked(),
            override_width=self.width_spin.value(),
            override_height=self.height_spin.value(),
            offset_x=self.off_x_spin.value(),
            offset_y=self.off_y_spin.value(),
            fps=self.fps_spin.value()
        )
        self.controller.update_meta(state, new_meta)
        self._preview_timer.setInterval(1000 // max(1, self.fps_spin.value()))

    def _on_copy(self) -> None:
        state = self.state_combo.currentData()
        if state:
            self._copied_meta = replace(self.controller.get_meta(state))
            self.paste_btn.setEnabled(True)

    def _on_paste(self) -> None:
        state = self.state_combo.currentData()
        if state and self._copied_meta:
            self.controller.update_meta(state, replace(self._copied_meta))
            self._refresh_state_dropdown()
            self._on_state_changed()
            self._restart_preview()

    def _on_swap(self) -> None:
        state_a, state_b = self.state_combo.currentData(), self.swap_combo.currentData()
        if state_a and state_b and state_a != state_b:
            meta_a, meta_b = self.controller.get_meta(state_a), self.controller.get_meta(state_b)
            self.controller.update_meta(state_a, meta_b)
            self.controller.update_meta(state_b, meta_a)
            self._refresh_state_dropdown()
            self._on_state_changed()
            self._restart_preview()

    def _update_preview(self) -> None:
        state = self.state_combo.currentData()
        if not state: return
        self._preview_frame += 1
        
        if self.preview_label.show_crop:
            frame, crop_rect = self.controller.get_raw_preview(state, self._preview_frame)
            self.preview_label.crop_rect = crop_rect
        else:
            frame = self.controller.get_frame(state, self._preview_frame)
            
        self.preview_label.setPixmap(frame) if frame else self.preview_label.setText("No Image")

    def _restart_preview(self) -> None:
        self._preview_frame = -1
        self._update_preview()

    def _on_borders_toggled(self, checked: bool) -> None:
        self.preview_label.show_borders = checked
        self.preview_label.update()
        
    def _on_crop_toggled(self, checked: bool) -> None:
        self.preview_label.show_crop = checked
        self._update_preview()
    
    def _on_crop_dragged(self, x: int, y: int, w: int, h: int) -> None:
        """Instantly updates the UI spinboxes while dragging the red overlay."""
        # Block _on_meta_edited from firing prematurely during the fast setValue updates
        self._is_updating_ui = True
        
        self.off_x_spin.setValue(x)
        self.off_y_spin.setValue(y)
        self.width_spin.setValue(w)
        self.height_spin.setValue(h)
        
        self._is_updating_ui = False
        
        # Manually trigger the meta save to apply the new coordinates to the Controller
        self._on_meta_edited()
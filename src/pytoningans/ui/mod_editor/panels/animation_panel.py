import copy

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, 
    QPushButton, QLabel, QFormLayout, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QRect

from pytoningans.core.constants import EntityState, AnimationMeta
from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.components import (
    CollapsibleSection, PreviewLabel, create_info_label, create_spinbox, create_info_widget
)

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
        section = CollapsibleSection("Grid and Extraction Settings")
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
        self.range_check = QCheckBox("Show Attack Range (Red Circle)")
        
        sec_layout.addWidget(self.borders_check)
        sec_layout.addWidget(self.range_check)
        section.content_layout.addLayout(sec_layout)
        layout.addWidget(section)

    def _build_state_panel(self) -> None:
        self.state_panel = QWidget()
        layout = QVBoxLayout(self.state_panel)
        layout.setContentsMargins(0,0,0,0)
        section = CollapsibleSection("Animation State Config")
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(
            create_info_label(
                "State:",
                "The State of the Pet to edit the values for."
            )
        )
        self.state_combo = QComboBox()
        h_layout.addWidget(self.state_combo)
        self.copy_btn = QPushButton("Copy")
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setEnabled(False)
        h_layout.addWidget(self.copy_btn)
        h_layout.addWidget(self.paste_btn)
        section.content_layout.addLayout(h_layout)
        
        swap_layout = QHBoxLayout()
        swap_layout.addWidget(
            create_info_label(
                "Swap State Data With:",
                "Swaps all the data between the two selected States "
                "(the top and bottom combo boxes)."
            )
        )
        self.swap_combo = QComboBox()
        for state in EntityState:
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
        self.crop_check = QCheckBox("Interactive Cropping")
        
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
        
        self.width_spin = create_spinbox(0, 2048)
        self.height_spin = create_spinbox(0, 2048)
        self.offset_x_spin = create_spinbox(-2048, 2048)
        self.offset_y_spin = create_spinbox(-2048, 2048)
        self.fps_spin = create_spinbox(1, 60)
        
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
        self.range_check.stateChanged.connect(self._on_range_toggled)
        self.crop_check.stateChanged.connect(self._on_crop_toggled)
        
        for widget in (
            self.row_spin, self.start_spin, self.end_spin, self.width_spin,
            self.height_spin, self.offset_x_spin, self.offset_y_spin, self.fps_spin
        ):
            widget.valueChanged.connect(self._on_meta_edited)
            
        self.loop_check.stateChanged.connect(self._on_meta_edited)
        self.reverse_check.stateChanged.connect(self._on_meta_edited)
        self.preview_label.crop_updated.connect(self._on_crop_dragged)
        self.bake_btn.clicked.connect(self._on_bake_clicked)
        self.apply_all_btn.clicked.connect(self._on_apply_all_clicked)

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
        for i, state in enumerate(EntityState):
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
        self.offset_x_spin.setValue(meta.offset_x)
        self.offset_y_spin.setValue(meta.offset_y)
        self.fps_spin.setValue(meta.fps)
        self._is_updating_ui = False
        self._preview_timer.setInterval(1000 // max(1, meta.fps))
        self._restart_preview()

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
            offset_x=self.offset_x_spin.value(),
            offset_y=self.offset_y_spin.value(),
            fps=self.fps_spin.value()
        )
        self.controller.update_meta(state, new_meta)
        self._preview_timer.setInterval(1000 // max(1, self.fps_spin.value()))

    def _on_copy(self) -> None:
        state: Optional[EntityState] = self.state_combo.currentData()
        if state is None: return
        
        self._copied_meta = copy.deepcopy(self.controller.get_meta(state))
        self.paste_btn.setEnabled(True)

    def _on_paste(self) -> None:
        state: Optional[EntityState] = self.state_combo.currentData()
        if state is None or self._copied_meta is None: return
        
        self.controller.update_meta(state, copy.deepcopy(self._copied_meta))
        self._refresh_state_dropdown()
        self._on_state_changed()
        self._restart_preview()

    def _on_swap(self) -> None:
        state_a, state_b = self.state_combo.currentData(), self.swap_combo.currentData()
        if state_a or state_b or state_a == state_b: return
            
        meta_a: AnimationMeta = copy.deepcopy(self.controller.get_meta(state_a))
        meta_b: AnimationMeta = copy.deepcopy(self.controller.get_meta(state_b))
        self.controller.update_meta(state_a, meta_b)
        self.controller.update_meta(state_b, meta_a)
        self._refresh_state_dropdown()
        self._on_state_changed()
        self._restart_preview()

    def _update_preview(self) -> None:
        state: Optional[EntityState] = self.state_combo.currentData()
        if state is None: return
        self._preview_frame += 1
        
        # Fetch the exact anchor for the current frame
        anchor, hitbox = self.controller.manager.get_frame_physics(state, self._preview_frame)
        self.preview_label.current_anchor = anchor
        self.preview_label.current_hitbox = hitbox
        self.preview_label.attack_range = self.controller.manager.attack_range
        
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
        
        self.offset_x_spin.setValue(x)
        self.offset_y_spin.setValue(y)
        self.width_spin.setValue(w)
        self.height_spin.setValue(h)
        
        self._is_updating_ui = False
        
        # Manually trigger the meta save to apply the new coordinates to the Controller
        self._on_meta_edited()
    
    def _on_bake_clicked(self) -> None:
        self.bake_btn.setEnabled(False)
        
        reply: QMessageBox.StandardButton = QMessageBox.question(
            self.state_panel, "Bake Sprite Sheet",
            "This will permanently crop the physical sprite_sheet.png "
            "file and reset your offsets to 0.\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.controller.bake_sprite_sheet():
                self.crop_check.setChecked(False)
                self.preview_label.crop_rect = QRect()
                self.load_data() # Reload UI to reflect the reset 0 offsets
                self._restart_preview()
                QMessageBox.information(
                    self.state_panel, "Success",
                    "Sprite sheet successfully baked and optimized!"
                )
            else:
                QMessageBox.critical(
                    self.state_panel, 
                    "Error", 
                    "Failed to overwrite sprite_sheet.png. Ensure the file isn't open in an image editor."
                )
        
        self.bake_btn.setEnabled(True)
    
    def _on_apply_all_clicked(self) -> None:
        state: Optional[EntityState] = self.state_combo.currentData()
        if state is None: return
        
        reply: QMessageBox.StandardButton = QMessageBox.question(
            self.state_panel, "Apply Crop to All",
            "This will overwrite the Width, Height, Offset X, and Offset Y of "
            "EVERY state with the current state's values.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.apply_crop_to_all(state)
            QMessageBox.information(
                self.state_panel, 
                "Success", 
                "Crop settings successfully applied to all animation states!"
            )
    
    def _on_range_toggled(self, checked: bool) -> None:
        self.preview_label.show_attack_range = checked
        self.preview_label.update()
from typing import Tuple, Callable, Optional
from dataclasses import replace

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QSpinBox,
    QPushButton, QFormLayout, QMessageBox, QFrame, QCheckBox
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication

from pytoningans.core.mod_manager import ModManager, CURRENT_CONFIG_VERSION
from pytoningans.core.constants import PetState, AnimationMeta
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.tool_tip import ToolTipLabel

class ModEditorController:
    """Handles data bridging between the UI and the ModManager."""
    def __init__(self, mod_manager: ModManager) -> None:
        self.manager: ModManager = mod_manager

    def get_mod_list(self) -> list[str]:
        return self.manager.get_available_mods()

    def load_mod(self, folder: str) -> bool:
        return self.manager.load_mod(folder)

    def save_mod(self, folder: str) -> None:
        self.manager.save_mod_config(folder, self.manager.current_mod_name)

    def get_global_grid(self) -> Tuple[int, int]:
        return self.manager.global_columns, self.manager.global_rows

    def update_global_grid(self, cols: int, rows: int) -> None:
        self.manager.global_columns = cols
        self.manager.global_rows = rows

    def get_meta(self, state: PetState) -> AnimationMeta:
        return self.manager.animations.get(state, AnimationMeta(row=0, start_frame=0, end_frame=1))

    def update_meta(self, state: PetState, meta: AnimationMeta) -> None:
        self.manager.animations[state] = meta
        self.manager.clear_cache()

    def get_frame(self, state: PetState, frame_index: int):
        return self.manager.get_frame(state, frame_index)
        
    def has_mapped_row(self, state: PetState) -> Tuple[bool, int]:
        meta = self.manager.animations.get(state)
        return (True, meta.row) if meta else (False, 0)
    
    def get_sheet_info(self) -> Tuple[int, int, int, int]:
        """Returns (sheet_width, sheet_height, base_tile_width, base_tile_height)."""
        sheet = self.manager._global_sheet
        if not sheet:
            return 0, 0, 0, 0
            
        sw, sh = sheet.width(), sheet.height()
        cols = max(1, self.manager.global_columns)
        rows = max(1, self.manager.global_rows)
        return sw, sh, sw // cols, sh // rows
    
    def get_behavior(self) -> bool:
        return self.manager.can_fly

    def update_behavior(self, can_fly: bool) -> None:
        self.manager.can_fly = can_fly


class ModEditorWindow(QWidget):
    """Handles ONLY visual drawing and user interactions."""
    def __init__(self, mod_manager: ModManager) -> None:
        super().__init__()
        self.controller: ModEditorController = ModEditorController(mod_manager)
        self._is_updating_ui: bool = False
        
        self._preview_frame: int = 0
        self._preview_timer: QTimer = QTimer(self)
        self._preview_timer.timeout.connect(self._update_preview)
        self._preview_timer.setInterval(100)
        
        self._copied_meta: Optional[AnimationMeta] = None
        
        self._setup_ui()
        self._refresh_mod_list()
        self._preview_timer.start()

    # --- UI Construction Helpers ---

    def _setup_ui(self) -> None:
        # Strip the OS window frame and resize for a horizontal layout
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(850, 580)
        
        self.main_layout: QVBoxLayout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self, "Mod Editor")
        self.main_layout.addWidget(self.title_bar)
        
        # Create the padded content container
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(20, 15, 20, 20)
        self.content_layout.setSpacing(10)

        # Top Span (Header and Banner)
        self._build_header()
        
        self.sheet_info_label = QLabel("Sheet: -- x -- px | Base Tile: -- x -- px")
        self.sheet_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sheet_info_label.setObjectName("BannerText")
        self.content_layout.addWidget(self.sheet_info_label)

        # Horizontal Split
        split_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()
        
        split_layout.addLayout(self.left_layout, stretch=1)
        split_layout.addLayout(self.right_layout, stretch=1)
        
        self.content_layout.addLayout(split_layout)

        # Build Components (Now they will route to left/right layouts)
        self._build_mod_selection()
        self._build_global_settings()
        self._build_preview_area()
        self._build_state_overrides()

        # Bottom Span (Save Button)
        self.save_btn = QPushButton("Save config.json")
        self.save_btn.clicked.connect(self._save_changes)
        self.content_layout.addWidget(self.save_btn)
        
        self.main_layout.addWidget(content_widget)
        
        # Center the window before it draws
        self._center_window()

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
        self.mod_combo.currentTextChanged.connect(self._on_mod_changed)
        layout.addWidget(self.mod_combo)
        self.left_layout.addLayout(layout)

    def _build_global_settings(self) -> None:
        layout = QFormLayout()
        self.global_cols_spin = self._create_spinbox(1, 100, self._on_global_edited)
        self.global_rows_spin = self._create_spinbox(1, 100, self._on_global_edited)
        
        self.can_fly_check = QCheckBox("Enable Flight (Ignores Gravity)")
        self.can_fly_check.stateChanged.connect(self._on_behavior_edited)
        
        lbl_cols = self._create_info_label(
            "Total Sheet Columns:", "How many columns the entire sprite sheet is divided into evenly."
        )
        lbl_rows = self._create_info_label(
            "Total Sheet Rows:", "How many rows the entire sprite sheet is divided into evenly."
        )
        
        layout.addRow(lbl_cols, self.global_cols_spin)
        layout.addRow(lbl_rows, self.global_rows_spin)
        layout.addRow("", self.can_fly_check)
        self.left_layout.addLayout(layout)

    def _build_state_overrides(self) -> None:
        layout = QHBoxLayout()
        layout.addWidget(QLabel("State Config:"))
        self.state_combo = QComboBox()
        self.state_combo.currentIndexChanged.connect(self._on_state_changed)
        layout.addWidget(self.state_combo)
        
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.clicked.connect(self._on_copy_clicked)
        
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.clicked.connect(self._on_paste_clicked)
        self.paste_btn.setEnabled(False) # Disabled until something is copied

        layout.addWidget(self.copy_btn)
        layout.addWidget(self.paste_btn)
        self.content_layout.addLayout(layout)
        
        swap_layout = QHBoxLayout()
        swap_layout.addWidget(QLabel("Swap Data With:"))
        
        self.swap_combo = QComboBox()
        for state in PetState:
            self.swap_combo.addItem(state.value.capitalize(), userData=state)
            
        self.swap_btn = QPushButton("Swap")
        self.swap_btn.clicked.connect(self._on_swap_clicked)
        
        swap_layout.addWidget(self.swap_combo)
        swap_layout.addWidget(self.swap_btn)
        self.content_layout.addLayout(swap_layout)

        form = QFormLayout()
        self.row_spin = self._create_spinbox(0, 100, self._on_value_edited)
        
        self.start_spin = self._create_spinbox(0, 100, self._on_value_edited)
        self.end_spin = self._create_spinbox(0, 100, self._on_value_edited)
        
        self.loop_check = QCheckBox("Loop Animation")
        self.loop_check.stateChanged.connect(self._on_value_edited)
        
        self.reverse_check = QCheckBox("Play in Reverse")
        self.reverse_check.stateChanged.connect(self._on_value_edited)
        
        self.width_spin = self._create_spinbox(0, 2048, self._on_value_edited)
        self.height_spin = self._create_spinbox(0, 2048, self._on_value_edited)
        self.offset_x_spin = self._create_spinbox(-2048, 2048, self._on_value_edited)
        self.offset_y_spin = self._create_spinbox(-2048, 2048, self._on_value_edited)
        self.fps_spin = self._create_spinbox(1, 60, self._on_value_edited)

        form.addRow(self._create_info_label("Mapped Row Index:", "..."), self.row_spin)
        form.addRow(self._create_info_label(
            "Start Frame Index:", "The column index (from 0) where the animation begins."
        ), self.start_spin)
        form.addRow(self._create_info_label(
            "End Frame Index:", "The column index (from 0) where the animation ends."
        ), self.end_spin)
        form.addRow("", self.loop_check)
        form.addRow("", self.reverse_check)
        form.addRow(self._create_info_label(
            "Override Width (px):", "Set above 0 to manually define this frame's width, ignoring the global grid."
        ), self.width_spin)
        form.addRow(self._create_info_label(
            "Override Height (px):", "Set above 0 to manually define this frame's height, ignoring the global grid."
        ), self.height_spin)
        form.addRow(self._create_info_label(
            "Offset X (px):", "Nudge the frame extraction boundary horizontally."
        ), self.offset_x_spin)
        form.addRow(self._create_info_label(
            "Offset Y (px):", "Nudge the frame extraction boundary vertically."
        ), self.offset_y_spin)
        form.addRow(self._create_info_label(
            "Playback Speed (FPS):", "How fast the animation plays. Higher means faster."
        ), self.fps_spin)
        
        self.right_layout.addLayout(form)

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
        self.restart_btn.clicked.connect(self._restart_preview)
        
        layout.addWidget(title)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.restart_btn)
        self.left_layout.addLayout(layout)

    def _create_spinbox(
        self, min_val: int, max_val: int, callback: Callable, special_text: Optional[str] = None
    ) -> QSpinBox:
        """Factory method to reduce repetitive QSpinBox instantiation logic."""
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.valueChanged.connect(callback)
        if special_text:
            spin.setSpecialValueText(special_text)
        return spin
    
    def _create_info_label(self, text: str, tooltip_text: str) -> QWidget:
        """Creates a row label with an inline info icon and tooltip."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(text)
        icon_lbl = ToolTipLabel(text="[?]", tooltip_text=tooltip_text)
        
        layout.addWidget(lbl)
        layout.addWidget(icon_lbl)
        layout.addStretch() 
        return widget

    # --- Signal Handlers & Logic Delegation ---
    
    def _on_swap_clicked(self, *_) -> None:
        state_a = self.state_combo.currentData()
        state_b = self.swap_combo.currentData()
        
        if not state_a or not state_b or state_a == state_b:
            return
            
        # Fetch both configurations
        meta_a = self.controller.get_meta(state_a)
        meta_b = self.controller.get_meta(state_b)
        
        # Swap them in the controller
        self.controller.update_meta(state_a, meta_b)
        self.controller.update_meta(state_b, meta_a)
        
        # Refresh the UI to show the new mapped rows
        self._refresh_state_dropdown()
        self._on_state_changed()
        
        # Reset preview
        self._preview_frame = -1
        self._update_preview()
    
    def _on_behavior_edited(self, *_) -> None:
        if self._is_updating_ui: return
        self.controller.update_behavior(self.can_fly_check.isChecked())

    def _refresh_state_dropdown(self) -> None:
        # Remember the currently selected state
        current_state = self.state_combo.currentData()
        
        self.state_combo.blockSignals(True)
        self.state_combo.clear()
        
        target_index = 0
        for i, state in enumerate(PetState):
            exists, row = self.controller.has_mapped_row(state)
            row_text = f"[Row {row}]" if exists else "[Missing!]"
            self.state_combo.addItem(f"{state.value.capitalize()} {row_text}", userData=state)
            
            # Find the index of our cached state
            if state == current_state:
                target_index = i
                
        # Restore the selection
        self.state_combo.setCurrentIndex(target_index)
        self.state_combo.blockSignals(False)
    
    def _refresh_dynamic_info(self) -> None:
        """Updates the top banner and injects the calculated auto-grid values into the spinboxes."""
        sw, sh, base_w, base_h = self.controller.get_sheet_info()
        
        # Update Top Banner
        self.sheet_info_label.setText(f"Sheet: {sw} x {sh} px | Base Tile: {base_w} x {base_h} px")
        
        # Update Special Spinbox Text
        self.width_spin.setSpecialValueText(f"0 (Auto: {base_w}px)")
        self.height_spin.setSpecialValueText(f"0 (Auto: {base_h}px)")

    def _on_global_edited(self, *_) -> None:
        if self._is_updating_ui: return
        self.controller.update_global_grid(self.global_cols_spin.value(), self.global_rows_spin.value())
        self._refresh_dynamic_info()
        self._update_preview()

    def _refresh_mod_list(self) -> None:
        self.mod_combo.blockSignals(True)
        self.mod_combo.clear()
        self.mod_combo.addItems(self.controller.get_mod_list())
        self.mod_combo.blockSignals(False)
        
        if self.mod_combo.count() > 0:
            self._on_mod_changed(self.mod_combo.currentText())

    def _on_mod_changed(self, mod_folder: str) -> None:
        if not mod_folder: return
            
        if self.controller.load_mod(mod_folder):
            # Check for legacy versions immediately after loading
            if self.controller.manager.config_version < 2:
                QMessageBox.warning(
                    self,
                    "Legacy Mod Detected",
                    f"'{mod_folder}' is using an older config version.\n\n"
                    f"Saving changes will upgrade it to Version {CURRENT_CONFIG_VERSION} "
                    "to support the newly added states.\n\n"
                    "Please manually back up your 'config.json' file before saving."
                )
                
            self._is_updating_ui = True
            cols, rows = self.controller.get_global_grid()
            self.global_cols_spin.setValue(cols)
            self.global_rows_spin.setValue(rows)
            self.can_fly_check.setChecked(self.controller.get_behavior())
            self._is_updating_ui = False
            
            self._refresh_dynamic_info()
            self._refresh_state_dropdown()
            self._on_state_changed()
        else:
            QMessageBox.warning(self, "Load Error", f"Could not load config or sprites for {mod_folder}.")

    def _on_state_changed(self, *_) -> None:
        raw_state = self.state_combo.currentData()
        if not raw_state: return
        
        current_state = PetState(raw_state)
        meta = self.controller.get_meta(current_state)

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

    def _on_value_edited(self, *_) -> None:
        if self._is_updating_ui: return
        raw_state = self.state_combo.currentData()
        if not raw_state: return
        current_state = PetState(raw_state)
        
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
        
        self.controller.update_meta(current_state, new_meta)
        self._preview_timer.setInterval(1000 // max(1, self.fps_spin.value()))

    def _save_changes(self) -> None:
        mod_folder = self.mod_combo.currentText()
        if not mod_folder: return
            
        self.controller.save_mod(mod_folder)
        QMessageBox.information(self, "Success", f"Saved configuration for {mod_folder}!")
    
    def _update_preview(self) -> None:
        if self.state_combo.count() == 0: return
        
        raw_state = self.state_combo.currentData()
        if not raw_state: return
        current_state = PetState(raw_state)
        
        self._preview_frame += 1
        frame = self.controller.get_frame(current_state, self._preview_frame)
        
        if frame is not None:
            self.preview_label.setPixmap(frame)
        else:
            self.preview_label.setText("No Image Loaded")
    
    def _on_copy_clicked(self) -> None:
        raw_state = self.state_combo.currentData()
        if not raw_state: return

        current_state = PetState(raw_state)
        meta = self.controller.get_meta(current_state)

        # Use replace() to create a safe, disconnected clone
        self._copied_meta = replace(meta)

        self.paste_btn.setEnabled(True)

    def _on_paste_clicked(self) -> None:
        if not self._copied_meta: return

        raw_state = self.state_combo.currentData()
        if not raw_state: return

        current_state = PetState(raw_state)

        # Clone the copied meta again so the user can paste it multiple times safely
        new_meta = replace(self._copied_meta)

        # Update the controller (which automatically flushes the cache)
        self.controller.update_meta(current_state, new_meta)

        # Refresh the spinboxes and dropdown text
        self._refresh_state_dropdown()
        self._on_state_changed()

        # Reset the preview sequence to immediately show the pasted frames
        self._preview_frame = -1
        self._update_preview()
    
    def _restart_preview(self) -> None:
        """Forces the animation sequence to start from the beginning."""
        self._preview_frame = -1
        self._update_preview()
    
    def _center_window(self) -> None:
        """Centers the window on the primary screen."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geom = screen.availableGeometry()
            window_geom = self.frameGeometry()
            window_geom.moveCenter(screen_geom.center())
            self.move(window_geom.topLeft())
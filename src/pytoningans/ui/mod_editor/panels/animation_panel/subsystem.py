from __future__ import annotations

import copy
from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QLabel, QMessageBox
from PySide6.QtCore import QTimer, QRect

from pytoningans.core.constants import (
    EntityState, AnimationMeta, EntityType, StructureState, ItemState
)
from ..base_panel import BasePanel
from .preview_panel import AnimationPreviewPanel
from .settings_panel import GridSettingsPanel, DebugSettingsPanel
from .state_panel import StateConfigPanel

if TYPE_CHECKING:
    from pytoningans.ui.mod_editor.controller import ModEditorController


class AnimationSubsystem(BasePanel):
    """Manages all animation-related UI panels, timers, and state bridging."""

    def __init__(
        self, controller: ModEditorController, dynamic_info_label: QLabel
    ) -> None:
        super().__init__(controller)
        self.info_label: QLabel = dynamic_info_label
        self._is_updating_ui: bool = False
        self._copied_meta: Optional[AnimationMeta] = None
        self._preview_frame: int = 0
        
        self._preview_timer: QTimer = QTimer(self)
        self._preview_timer.timeout.connect(self._update_preview)
        self._preview_timer.setInterval(100)
        
        self._setup_ui()
        self._connect_signals()
        
        self._preview_timer.start()
    
    def _setup_ui(self) -> None:
        self.grid_panel = GridSettingsPanel()
        self.preview_panel = AnimationPreviewPanel()
        self.debug_panel = DebugSettingsPanel()
        self.state_panel = StateConfigPanel()

        # Backward-compatible attribute aliases
        self.cols_spin = self.grid_panel.cols_spin
        self.rows_spin = self.grid_panel.rows_spin
        self.grid_section = self.grid_panel.grid_section

        self.preview_label = self.preview_panel.preview_label
        self.preview_zoom_spin = self.preview_panel.preview_zoom_spin
        self.preview_reset_btn = self.preview_panel.preview_reset_btn
        self.restart_btn = self.preview_panel.restart_btn

        self.debug_section = self.debug_panel.debug_section
        self.borders_check = self.debug_panel.borders_check
        self.range_check = self.debug_panel.range_check

        self.state_section = self.state_panel.state_section
        self.state_combo = self.state_panel.state_combo
        self.copy_btn = self.state_panel.copy_btn
        self.paste_btn = self.state_panel.paste_btn
        self.swap_combo = self.state_panel.swap_combo
        self.swap_btn = self.state_panel.swap_btn
        self.row_spin = self.state_panel.row_spin
        self.start_spin = self.state_panel.start_spin
        self.end_spin = self.state_panel.end_spin
        self.loop_check = self.state_panel.loop_check
        self.reverse_check = self.state_panel.reverse_check
        self.crop_check = self.state_panel.crop_check
        self.apply_all_btn = self.state_panel.apply_all_btn
        self.bake_btn = self.state_panel.bake_btn
        self.width_spin = self.state_panel.width_spin
        self.height_spin = self.state_panel.height_spin
        self.offset_x_spin = self.state_panel.offset_x_spin
        self.offset_y_spin = self.state_panel.offset_y_spin
        self.fps_spin = self.state_panel.fps_spin

    def load_data(self) -> None:
        self._is_updating_ui = True
        cols, rows = self.controller.get_global_grid()
        self.cols_spin.setValue(cols)
        self.rows_spin.setValue(rows)
        
        is_static: bool = self.controller.manager.is_static
        self.grid_section.setVisible(not is_static)
        self.restart_btn.setVisible(not is_static)
        self._is_updating_ui = False
        
        self._refresh_dynamic_info()
        self._refresh_state_dropdown()

    def _connect_signals(self) -> None:
        self.cols_spin.valueChanged.connect(self._on_global_edited)
        self.rows_spin.valueChanged.connect(self._on_global_edited)
        
        self.state_combo.currentIndexChanged.connect(self._on_state_changed)
        self.copy_btn.clicked.connect(self._on_copy)
        self.paste_btn.clicked.connect(self._on_paste)
        self.swap_btn.clicked.connect(self._on_swap)
        self.restart_btn.clicked.connect(self._restart_preview)
        self.preview_zoom_spin.valueChanged.connect(self.preview_label.set_zoom)
        self.preview_label.zoom_changed.connect(self.preview_zoom_spin.setValue)
        self.preview_reset_btn.clicked.connect(self.preview_label.reset_view)
        
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

    def _refresh_state_dropdown(self, selected_state: Optional[str] = None) -> None:
        # Determine previous selection as a raw string
        prev_data = self.state_combo.currentData()
        current_selection: Optional[str] = selected_state or (str(prev_data) if prev_data else None)

        self.state_combo.blockSignals(True)
        self.state_combo.clear()
        
        self.swap_combo.blockSignals(True)
        self.swap_combo.clear()

        if self.controller.manager.entity_type == EntityType.STRUCTURE:
            state_enum = StructureState
        elif self.controller.manager.entity_type == EntityType.ITEM:
            state_enum = ItemState
        else:
            state_enum = EntityState

        target_idx: int = 0
        for i, state in enumerate(state_enum):
            state_val: str = state.value
            exists, row = self.controller.has_mapped_row(state_val)
            display_name: str = (
                f"{state_val.capitalize()} [{'Row ' + str(row) if exists else 'Unmapped'}]"
            )
            
            # Store pure string keys in both combo boxes
            self.state_combo.addItem(display_name, userData=state_val)
            self.swap_combo.addItem(state_val.capitalize(), userData=state_val)
                
            if current_selection and state_val == current_selection:
                target_idx = i

        if self.state_combo.count() > 0:
            self.state_combo.setCurrentIndex(target_idx)
            
        if self.swap_combo.count() > 0:
            # Set swap_combo to a different item by default if possible
            swap_idx = 1 if self.swap_combo.count() > 1 else 0
            self.swap_combo.setCurrentIndex(swap_idx)

        self.state_combo.blockSignals(False)
        self.swap_combo.blockSignals(False)

        # Explicitly reload the data for the active selection
        self._on_state_changed()

    def _on_global_edited(self, *_) -> None:
        if self._is_updating_ui: return
        self.controller.update_global_grid(self.cols_spin.value(), self.rows_spin.value())
        self._refresh_dynamic_info()
        self._update_preview()

    def _on_state_changed(self, *_) -> None:
        state_data = self.state_combo.currentData()
        if state_data is None: return
        
        meta: AnimationMeta = self.controller.get_meta(state_data)
        
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
        state: Optional[str] = self.state_combo.currentData()
        if state is None: return
        
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
        state: Optional[str] = self.state_combo.currentData()
        if state is None: return
        self._copied_meta = copy.deepcopy(self.controller.get_meta(state))
        self.paste_btn.setEnabled(True)

    def _on_paste(self) -> None:
        state: Optional[str] = self.state_combo.currentData()
        if state is None or self._copied_meta is None: return
        self.controller.update_meta(state, copy.deepcopy(self._copied_meta))
        self._refresh_state_dropdown(selected_state=state)
        self._on_state_changed()
        self._restart_preview()

    def _on_swap(self) -> None:
        state_a, state_b = self.state_combo.currentData(), self.swap_combo.currentData()
        if state_a is None or state_b is None or state_a == state_b: return
            
        meta_a: AnimationMeta = copy.deepcopy(self.controller.get_meta(state_a))
        meta_b: AnimationMeta = copy.deepcopy(self.controller.get_meta(state_b))
        self.controller.update_meta(state_a, meta_b)
        self.controller.update_meta(state_b, meta_a)
        self._refresh_state_dropdown(selected_state=state_a)
        self._on_state_changed()
        self._restart_preview()

    def _update_preview(self) -> None:
        state: Optional[str] = self.state_combo.currentData()
        if state is None: return
        
        self._preview_frame += 1
        
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
        state: Optional[str] = self.state_combo.currentData()
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


from typing import Optional
from dataclasses import replace

from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication

from pytoningans.core.mod_manager import ModManager, CURRENT_CONFIG_VERSION
from pytoningans.core.constants import PetState, AnimationMeta
from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.ui import ModEditorUI


class ModEditorWindow(QWidget):
    """The main event hub housing logical operations and timers."""
    
    def __init__(self, mod_manager: ModManager) -> None:
        super().__init__()
        self.controller: ModEditorController = ModEditorController(mod_manager)
        self._is_updating_ui: bool = False
        
        self._preview_frame: int = 0
        self._preview_timer: QTimer = QTimer(self)
        self._preview_timer.timeout.connect(self._update_preview)
        self._preview_timer.setInterval(100)
        
        self._copied_meta: Optional[AnimationMeta] = None
        
        self.ui = ModEditorUI()
        self.ui.setup_ui(self)
        
        self._connect_signals()
        
        self._refresh_mod_list()
        self._preview_timer.start()
        self._center_window()

    def _connect_signals(self) -> None:
        """Centrally binds all UI elements to their logical event handlers."""
        self.ui.mod_combo.currentTextChanged.connect(self._on_mod_changed)
        self.ui.can_fly_check.stateChanged.connect(self._on_behavior_edited)
        self.ui.state_combo.currentIndexChanged.connect(self._on_state_changed)
        
        self.ui.copy_btn.clicked.connect(self._on_copy_clicked)
        self.ui.paste_btn.clicked.connect(self._on_paste_clicked)
        self.ui.swap_btn.clicked.connect(self._on_swap_clicked)
        self.ui.save_btn.clicked.connect(self._save_changes)
        self.ui.restart_btn.clicked.connect(self._restart_preview)
        self.ui.can_fly_check.stateChanged.connect(self._on_behavior_edited)
        
        for stat_spin in (
            self.ui.max_health_spin, self.ui.atk_dmg_spin,
            self.ui.atk_range_spin, self.ui.jump_height_spin
        ):
            stat_spin.valueChanged.connect(self._on_behavior_edited)
        
        for spin in (self.ui.global_cols_spin, self.ui.global_rows_spin):
            spin.valueChanged.connect(self._on_global_edited)
            
        for widget in (
            self.ui.row_spin, self.ui.start_spin, self.ui.end_spin,
            self.ui.width_spin, self.ui.height_spin, self.ui.offset_x_spin, 
            self.ui.offset_y_spin, self.ui.fps_spin
        ):
            widget.valueChanged.connect(self._on_value_edited)
            
        for check in (self.ui.loop_check, self.ui.reverse_check):
            check.stateChanged.connect(self._on_value_edited)

    # --- Signal Handlers & Logic Delegation ---
    
    def _on_swap_clicked(self, *_) -> None:
        state_a = self.ui.state_combo.currentData()
        state_b = self.ui.swap_combo.currentData()
        
        if not state_a or not state_b or state_a == state_b:
            return
            
        meta_a = self.controller.get_meta(state_a)
        meta_b = self.controller.get_meta(state_b)
        
        self.controller.update_meta(state_a, meta_b)
        self.controller.update_meta(state_b, meta_a)
        
        self._refresh_state_dropdown()
        self._on_state_changed()
        
        self._preview_frame = -1
        self._update_preview()
    
    def _on_behavior_edited(self, *_) -> None:
        if self._is_updating_ui: return
        new_stats = {
            "can_fly": self.ui.can_fly_check.isChecked(),
            "max_health": self.ui.max_health_spin.value(),
            "attack_damage": self.ui.atk_dmg_spin.value(),
            "attack_range": self.ui.atk_range_spin.value(),
            "jump_height": self.ui.jump_height_spin.value()
        }
        self.controller.update_behavior_stats(new_stats)

    def _refresh_state_dropdown(self) -> None:
        current_state = self.ui.state_combo.currentData()
        
        self.ui.state_combo.blockSignals(True)
        self.ui.state_combo.clear()
        
        target_index = 0
        for i, state in enumerate(PetState):
            exists, row = self.controller.has_mapped_row(state)
            row_text = f"[Row {row}]" if exists else "[Missing!]"
            self.ui.state_combo.addItem(f"{state.value.capitalize()} {row_text}", userData=state)
            
            if state == current_state:
                target_index = i
                
        self.ui.state_combo.setCurrentIndex(target_index)
        self.ui.state_combo.blockSignals(False)
    
    def _refresh_dynamic_info(self) -> None:
        sw, sh, base_w, base_h = self.controller.get_sheet_info()
        self.ui.sheet_info_label.setText(f"Sheet: {sw} x {sh} px | Base Tile: {base_w} x {base_h} px")
        self.ui.width_spin.setSpecialValueText(f"0 (Auto: {base_w}px)")
        self.ui.height_spin.setSpecialValueText(f"0 (Auto: {base_h}px)")

    def _on_global_edited(self, *_) -> None:
        if self._is_updating_ui: return
        self.controller.update_global_grid(self.ui.global_cols_spin.value(), self.ui.global_rows_spin.value())
        self._refresh_dynamic_info()
        self._update_preview()

    def _refresh_mod_list(self) -> None:
        self.ui.mod_combo.blockSignals(True)
        self.ui.mod_combo.clear()
        self.ui.mod_combo.addItems(self.controller.get_mod_list())
        self.ui.mod_combo.blockSignals(False)
        
        if self.ui.mod_combo.count() > 0:
            self._on_mod_changed(self.ui.mod_combo.currentText())

    def _on_mod_changed(self, mod_folder: str) -> None:
        if not mod_folder: return
            
        if self.controller.load_mod(mod_folder):
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
            self.ui.global_cols_spin.setValue(cols)
            self.ui.global_rows_spin.setValue(rows)
            self.ui.can_fly_check.setChecked(self.controller.get_behavior())
            
            stats = self.controller.get_behavior_stats()
            self.ui.can_fly_check.setChecked(stats["can_fly"])
            self.ui.max_health_spin.setValue(stats["max_health"])
            self.ui.atk_dmg_spin.setValue(stats["attack_damage"])
            self.ui.atk_range_spin.setValue(stats["attack_range"])
            self.ui.jump_height_spin.setValue(stats["jump_height"])
            
            self._is_updating_ui = False
            
            self._refresh_dynamic_info()
            self._refresh_state_dropdown()
            self._on_state_changed()
        else:
            QMessageBox.warning(self, "Load Error", f"Could not load config or sprites for {mod_folder}.")

    def _on_state_changed(self, *_) -> None:
        raw_state = self.ui.state_combo.currentData()
        if not raw_state: return
        
        current_state = PetState(raw_state)
        meta = self.controller.get_meta(current_state)

        self._is_updating_ui = True
        self.ui.row_spin.setValue(meta.row)
        self.ui.start_spin.setValue(meta.start_frame)
        self.ui.end_spin.setValue(meta.end_frame)
        self.ui.loop_check.setChecked(meta.loop)
        self.ui.reverse_check.setChecked(meta.reverse)
        self.ui.width_spin.setValue(meta.override_width)
        self.ui.height_spin.setValue(meta.override_height)
        self.ui.offset_x_spin.setValue(meta.offset_x)
        self.ui.offset_y_spin.setValue(meta.offset_y)
        self.ui.fps_spin.setValue(meta.fps)
        self._is_updating_ui = False
        self._preview_timer.setInterval(1000 // max(1, meta.fps))

    def _on_value_edited(self, *_) -> None:
        if self._is_updating_ui: return
        raw_state = self.ui.state_combo.currentData()
        if not raw_state: return
        current_state = PetState(raw_state)
        
        new_meta = AnimationMeta(
            row=self.ui.row_spin.value(),
            start_frame=self.ui.start_spin.value(),
            end_frame=self.ui.end_spin.value(),
            loop=self.ui.loop_check.isChecked(),
            reverse=self.ui.reverse_check.isChecked(),
            override_width=self.ui.width_spin.value(),
            override_height=self.ui.height_spin.value(),
            offset_x=self.ui.offset_x_spin.value(),
            offset_y=self.ui.offset_y_spin.value(),
            fps=self.ui.fps_spin.value()
        )
        
        self.controller.update_meta(current_state, new_meta)
        self._preview_timer.setInterval(1000 // max(1, self.ui.fps_spin.value()))

    def _save_changes(self) -> None:
        mod_folder = self.ui.mod_combo.currentText()
        if not mod_folder: return
            
        self.controller.save_mod(mod_folder)
        QMessageBox.information(self, "Success", f"Saved configuration for {mod_folder}!")
    
    def _update_preview(self) -> None:
        if self.ui.state_combo.count() == 0: return
        
        raw_state = self.ui.state_combo.currentData()
        if not raw_state: return
        current_state = PetState(raw_state)
        
        self._preview_frame += 1
        frame = self.controller.get_frame(current_state, self._preview_frame)
        
        if frame is not None:
            self.ui.preview_label.setPixmap(frame)
        else:
            self.ui.preview_label.setText("No Image Loaded")
    
    def _on_copy_clicked(self) -> None:
        raw_state = self.ui.state_combo.currentData()
        if not raw_state: return

        current_state = PetState(raw_state)
        meta = self.controller.get_meta(current_state)

        self._copied_meta = replace(meta)
        self.ui.paste_btn.setEnabled(True)

    def _on_paste_clicked(self) -> None:
        if not self._copied_meta: return

        raw_state = self.ui.state_combo.currentData()
        if not raw_state: return

        current_state = PetState(raw_state)
        new_meta = replace(self._copied_meta)

        self.controller.update_meta(current_state, new_meta)

        self._refresh_state_dropdown()
        self._on_state_changed()

        self._preview_frame = -1
        self._update_preview()
    
    def _restart_preview(self) -> None:
        self._preview_frame = -1
        self._update_preview()
    
    def _center_window(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geom = screen.availableGeometry()
            window_geom = self.frameGeometry()
            window_geom.moveCenter(screen_geom.center())
            self.move(window_geom.topLeft())
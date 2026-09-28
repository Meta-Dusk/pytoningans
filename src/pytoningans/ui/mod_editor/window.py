import os, subprocess

from typing import Optional, Dict, Any, List
from dataclasses import replace

from PySide6.QtWidgets import QWidget, QMessageBox, QInputDialog, QListWidgetItem
from PySide6.QtCore import QRect, QTimer, Signal, Qt
from PySide6.QtGui import QGuiApplication, QPixmap, QScreen

from pytoningans.core.mod_manager import ModManager, CURRENT_CONFIG_VERSION
from pytoningans.core.constants import PetState, AnimationMeta, BehaviorType
from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.ui import ModEditorUI, TriggerDialog


class ModEditorWindow(QWidget):
    """The main event hub housing logical operations and timers."""
    mods_updated = Signal()
    
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
        self.ui.behavior_type_combo.currentIndexChanged.connect(self._on_behavior_edited)
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
        
        self.ui.add_script_btn.clicked.connect(self._open_behavior_script)
        self.ui.edit_script_btn.clicked.connect(self._open_behavior_script)
        self.ui.delete_script_btn.clicked.connect(self._delete_behavior)
        
        self.ui.add_plain_btn.clicked.connect(self._on_add_plain_dialogue)
        self.ui.del_plain_btn.clicked.connect(self._on_remove_plain_dialogue)
        self.ui.add_trigger_btn.clicked.connect(self._on_add_window_trigger)
        self.ui.del_trigger_btn.clicked.connect(self._on_remove_window_trigger)
        self.ui.edit_plain_btn.clicked.connect(self._on_edit_plain_dialogue)
        self.ui.edit_trigger_btn.clicked.connect(self._on_edit_window_trigger)

    # --- Signal Handlers & Logic Delegation ---
    
    def _on_swap_clicked(self, *_) -> None:
        state_a = self.ui.state_combo.currentData()
        state_b = self.ui.swap_combo.currentData()
        
        if not state_a or not state_b or state_a == state_b:
            return
            
        meta_a: AnimationMeta = self.controller.get_meta(state_a)
        meta_b: AnimationMeta = self.controller.get_meta(state_b)
        
        self.controller.update_meta(state_a, meta_b)
        self.controller.update_meta(state_b, meta_a)
        
        self._refresh_state_dropdown()
        self._on_state_changed()
        
        self._preview_frame = -1
        self._update_preview()
    
    def _on_behavior_edited(self, *_) -> None:
        if self._is_updating_ui: return
        new_stats: Dict[str, Any] = {
            "type": self.ui.behavior_type_combo.currentData(),
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
        
        target_index: int = 0
        for i, state in enumerate(PetState):
            exists, row = self.controller.has_mapped_row(state)
            row_text = f"[Row {row}]" if exists else "[Missing!]"
            self.ui.state_combo.addItem(f"{state.value.capitalize()} {row_text}", userData=state)
            
            if state == current_state: target_index = i
                
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
            if self.controller.manager.config_version < CURRENT_CONFIG_VERSION:
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
            
            stats: Dict[str, Any] = self.controller.get_behavior_stats()
            self.ui.can_fly_check.setChecked(stats["can_fly"])
            self.ui.max_health_spin.setValue(stats["max_health"])
            self.ui.atk_dmg_spin.setValue(stats["attack_damage"])
            self.ui.atk_range_spin.setValue(stats["attack_range"])
            self.ui.jump_height_spin.setValue(stats["jump_height"])
            
            current_type = stats.get("type", BehaviorType.NEUTRAL)
            target_index: int = self.ui.behavior_type_combo.findData(current_type)
            self.ui.behavior_type_combo.setCurrentIndex(target_index)
            
            self.ui.plain_dialogue_list.clear()
            if hasattr(self.controller.manager, 'plain_dialogue'):
                self.ui.plain_dialogue_list.addItems(self.controller.manager.plain_dialogue)
            
            self.ui.window_triggers_list.clear()
            if hasattr(self.controller.manager, 'window_triggers'):
                for trigger in self.controller.manager.window_triggers:
                    matches: List[str] = trigger.get("title_matches", [])
                    text: str = trigger.get("text", "...")
                    chance: float = trigger.get("chance", 1.0)
                    
                    match_str: str = ", ".join(matches)
                    display_text: str = f"{text} | {match_str} | {int(chance*100)}%"
                    
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, trigger)
                    self.ui.window_triggers_list.addItem(item)
            
            self._is_updating_ui = False
            
            self._refresh_dynamic_info()
            self._refresh_state_dropdown()
            self._on_state_changed()
            self._refresh_script_buttons()
        else:
            QMessageBox.warning(self, "Load Error", f"Could not load config or sprites for {mod_folder}.")

    def _on_state_changed(self, *_) -> None:
        raw_state = self.ui.state_combo.currentData()
        if not raw_state: return
        
        current_state = PetState(raw_state)
        meta: AnimationMeta = self.controller.get_meta(current_state)

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
        mod_folder: str = self.ui.mod_combo.currentText()
        if not mod_folder: return
            
        self.controller.save_mod(mod_folder)
        self.mods_updated.emit()
        QMessageBox.information(self, "Success", f"Saved configuration for {mod_folder}!")
    
    def _update_preview(self) -> None:
        if self.ui.state_combo.count() == 0: return
        
        raw_state = self.ui.state_combo.currentData()
        if not raw_state: return
        current_state = PetState(raw_state)
        
        self._preview_frame += 1
        frame: Optional[QPixmap] = self.controller.get_frame(current_state, self._preview_frame)
        
        if frame is not None:
            self.ui.preview_label.setPixmap(frame)
        else:
            self.ui.preview_label.setText("No Image Loaded")
    
    def _on_copy_clicked(self) -> None:
        raw_state = self.ui.state_combo.currentData()
        if not raw_state: return

        current_state = PetState(raw_state)
        meta: AnimationMeta = self.controller.get_meta(current_state)

        self._copied_meta = replace(meta)
        self.ui.paste_btn.setEnabled(True)

    def _on_paste_clicked(self) -> None:
        if not self._copied_meta: return

        raw_state = self.ui.state_combo.currentData()
        if not raw_state: return

        current_state = PetState(raw_state)
        new_meta: AnimationMeta = replace(self._copied_meta)

        self.controller.update_meta(current_state, new_meta)

        self._refresh_state_dropdown()
        self._on_state_changed()

        self._preview_frame = -1
        self._update_preview()
    
    def _restart_preview(self) -> None:
        self._preview_frame = -1
        self._update_preview()
    
    def _center_window(self) -> None:
        screen: QScreen = QGuiApplication.primaryScreen()
        if not screen: return
        
        screen_geom: QRect = screen.availableGeometry()
        window_geom: QRect = self.frameGeometry()
        window_geom.moveCenter(screen_geom.center())
        self.move(window_geom.topLeft())
    
    def _create_behavior_script(self, mod_path: str) -> None:
        behavior_path: str = os.path.join(mod_path, "behavior.py")
        
        # Create the boilerplate if it doesn't exist
        if os.path.exists(behavior_path): return
        boilerplate = (
            "from api import BasePetBehavior, IPet, Pos2D\n\n"
            "class Behavior(BasePetBehavior):\n"
            "    def on_decision_tick(self, pet: IPet) -> bool:\n"
            "        return False\n"
        )
        with open(behavior_path, "w", encoding="utf-8") as f:
            f.write(boilerplate)
    
    def _open_behavior_script(self) -> None:
        mod_folder: str = self.ui.mod_combo.currentText()
        if not mod_folder: return
        
        mods_dir: str = self.controller.manager.mods_dir
        mod_path: str = os.path.join(mods_dir, mod_folder)
        behavior_path: str = os.path.join(mod_path, "behavior.py")
        
        # Create the boilerplate if it doesn't exist
        if not os.path.exists(behavior_path):
            boilerplate = (
                "from api import BasePetBehavior, IPet, Pos2D\n\n"
                "class Behavior(BasePetBehavior):\n"
                "    def on_decision_tick(self, pet: IPet) -> bool:\n"
                "        return False\n"
            )
            with open(behavior_path, "w", encoding="utf-8") as f:
                f.write(boilerplate)
            
            self._refresh_script_buttons()

        # Attempt to open VS Code with the mods folder as the workspace, 
        # and immediately open the behavior.py file in a tab
        try:
            subprocess.Popen(['code', mods_dir, behavior_path], shell=True)
        except Exception:
            # Fallback: Open with the default OS handler
            os.startfile(behavior_path)
    
    def _delete_behavior(self) -> None:
        mod_folder: str = self.ui.mod_combo.currentText()
        if not mod_folder: return
        
        mod_path: str = os.path.join(self.controller.manager.mods_dir, mod_folder)
        behavior_path: str = os.path.join(mod_path, "behavior.py")
        
        if os.path.exists(behavior_path):
            os.remove(behavior_path)
            # Refresh buttons immediately so 'Edit'/'Delete' disable and 'Add' enables
            self._refresh_script_buttons()
    
    def _refresh_script_buttons(self) -> None:
        mod_folder: str = self.ui.mod_combo.currentText()
        if not mod_folder:
            self.ui.add_script_btn.setEnabled(False)
            self.ui.edit_script_btn.setEnabled(False)
            self.ui.delete_script_btn.setEnabled(False)
            return

        mod_path: str = os.path.join(self.controller.manager.mods_dir, mod_folder)
        behavior_path: str = os.path.join(mod_path, "behavior.py")
        
        script_exists: bool = os.path.exists(behavior_path)
        
        self.ui.add_script_btn.setEnabled(not script_exists)
        self.ui.edit_script_btn.setEnabled(script_exists)
        self.ui.delete_script_btn.setEnabled(script_exists)
    
    def _on_add_plain_dialogue(self) -> None:
        """Opens a popup window to type a new dialogue line."""
        # Using self.ui.plain_dialogue_list as the parent ensures the popup centers correctly
        text, ok = QInputDialog.getText(
            self.ui.plain_dialogue_list, 
            "Add Plain Dialogue", 
            "Enter the dialogue text:"
        )
        
        # If the user clicked OK and didn't leave it blank
        if ok and text.strip():
            self.ui.plain_dialogue_list.addItem(text.strip())
            self._save_dialogue_state()

    def _on_remove_plain_dialogue(self) -> None:
        """Removes the currently selected line from the list."""
        current_row: int = self.ui.plain_dialogue_list.currentRow()
        if current_row >= 0:
            # takeItem removes it from the UI
            self.ui.plain_dialogue_list.takeItem(current_row)
            self._save_dialogue_state()

    def _save_dialogue_state(self) -> None:
        """Extracts all items from the UI list and updates the engine manager."""
        if getattr(self, '_is_updating_ui', False): return
        
        new_dialogue = []
        for i in range(self.ui.plain_dialogue_list.count()):
            new_dialogue.append(self.ui.plain_dialogue_list.item(i).text())
        
        if hasattr(self.controller.manager, 'plain_dialogue'):
            self.controller.manager.plain_dialogue = new_dialogue
    
    def _on_add_window_trigger(self) -> None:
        dialog = TriggerDialog(self.ui.window_triggers_list)
        if dialog.exec():
            data = dialog.get_data()
            if not data["text"] or not data["title_matches"]: return
            
            # Format: "Writing bugs? | vscode, code.exe | 50%"
            match_str = ", ".join(data["title_matches"])
            display_text = f"{data['text']} | {match_str} | {int(data['chance']*100)}%"
            
            item = QListWidgetItem(display_text)
            # Store the raw dictionary silently inside the UI item
            item.setData(Qt.ItemDataRole.UserRole, data) 
            
            self.ui.window_triggers_list.addItem(item)
            self._save_trigger_state()

    def _on_remove_window_trigger(self) -> None:
        current_row = self.ui.window_triggers_list.currentRow()
        if current_row >= 0:
            self.ui.window_triggers_list.takeItem(current_row)
            self._save_trigger_state()

    def _save_trigger_state(self) -> None:
        if getattr(self, '_is_updating_ui', False): return
        
        new_triggers = []
        for i in range(self.ui.window_triggers_list.count()):
            item = self.ui.window_triggers_list.item(i)
            # Extract the raw dictionary back out of the UI item
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                new_triggers.append(data)
                
        self.controller.manager.window_triggers = new_triggers
    
    def _on_edit_plain_dialogue(self) -> None:
        current_item = self.ui.plain_dialogue_list.currentItem()
        if not current_item: return

        text, ok = QInputDialog.getText(
            self.ui.plain_dialogue_list, 
            "Edit Plain Dialogue", 
            "Update the dialogue text:",
            text=current_item.text() # Pre-fill the current text
        )
        
        if ok and text.strip():
            current_item.setText(text.strip())
            self._save_dialogue_state()

    def _on_edit_window_trigger(self) -> None:
        current_item = self.ui.window_triggers_list.currentItem()
        if not current_item: return

        # Extract the hidden dictionary
        current_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not current_data: return

        dialog = TriggerDialog(self.ui.window_triggers_list)
        dialog.set_data(current_data) # Inject the existing data into the UI
        
        if dialog.exec():
            new_data = dialog.get_data()
            if not new_data["text"] or not new_data["title_matches"]: return
            
            match_str = ", ".join(new_data["title_matches"])
            display_text = f"{new_data['text']} | {match_str} | {int(new_data['chance']*100)}%"
            
            # Update the UI display string AND the hidden dictionary
            current_item.setText(display_text)
            current_item.setData(Qt.ItemDataRole.UserRole, new_data) 
            
            self._save_trigger_state()
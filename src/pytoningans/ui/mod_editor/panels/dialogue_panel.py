from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, 
    QInputDialog, QListWidgetItem
)
from PySide6.QtCore import Qt

from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.components import CollapsibleSection
from pytoningans.ui.mod_editor.dialogs import TriggerDialog
from .base_panel import BasePanel

class DialoguePanel(BasePanel):
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__(controller)
        self._is_updating_ui = False
        
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        """Constructs the UI specific to Dialogue and Speech."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.section = CollapsibleSection("Dialogue and Speech")
        sec_layout = QVBoxLayout()
        
        # --- Plain Dialogue UI ---
        self.plain_dialogue_list = QListWidget()
        self.plain_dialogue_list.setMinimumHeight(100)
        sec_layout.addWidget(self.plain_dialogue_list)
        
        plain_btns = QHBoxLayout()
        self.add_plain_btn = QPushButton("+ Add")
        self.edit_plain_btn = QPushButton("✎ Edit")
        self.del_plain_btn = QPushButton("- Remove")
        plain_btns.addWidget(self.add_plain_btn)
        plain_btns.addWidget(self.edit_plain_btn)
        plain_btns.addWidget(self.del_plain_btn)
        sec_layout.addLayout(plain_btns)
        
        # --- Window Triggers UI ---
        sec_layout.addSpacing(10)
        self.window_triggers_list = QListWidget()
        self.window_triggers_list.setMinimumHeight(150)
        sec_layout.addWidget(self.window_triggers_list)
        
        trigger_btns = QHBoxLayout()
        self.add_trigger_btn = QPushButton("+ Add")
        self.edit_trigger_btn = QPushButton("✎ Edit")
        self.del_trigger_btn = QPushButton("- Remove")
        trigger_btns.addWidget(self.add_trigger_btn)
        trigger_btns.addWidget(self.edit_trigger_btn)
        trigger_btns.addWidget(self.del_trigger_btn)
        sec_layout.addLayout(trigger_btns)
        
        self.section.content_layout.addLayout(sec_layout)
        layout.addWidget(self.section)

    def _connect_signals(self) -> None:
        """Binds this panel's buttons to this panel's logic."""
        self.add_plain_btn.clicked.connect(self._on_add_plain_dialogue)
        self.edit_plain_btn.clicked.connect(self._on_edit_plain_dialogue)
        self.del_plain_btn.clicked.connect(self._on_remove_plain_dialogue)
        
        self.add_trigger_btn.clicked.connect(self._on_add_window_trigger)
        self.edit_trigger_btn.clicked.connect(self._on_edit_window_trigger)
        self.del_trigger_btn.clicked.connect(self._on_remove_window_trigger)

    def load_data(self) -> None:
        """Called by the main window whenever a new mod is selected."""
        self._is_updating_ui = True
        
        # Populate Plain Dialogue
        self.plain_dialogue_list.clear()
        if hasattr(self.controller.manager, 'plain_dialogue'):
            self.plain_dialogue_list.addItems(self.controller.manager.plain_dialogue)
            
        # Populate Window Triggers
        self.window_triggers_list.clear()
        if hasattr(self.controller.manager, 'window_triggers'):
            for trigger in self.controller.manager.window_triggers:
                matches = trigger.get("title_matches", [])
                text = trigger.get("text", "...")
                chance = trigger.get("chance", 1.0)
                
                match_str = ", ".join(matches)
                display_text = f"{text} | {match_str} | {int(chance*100)}%"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, trigger)
                self.window_triggers_list.addItem(item)
                
        self._is_updating_ui = False

    def _on_add_plain_dialogue(self) -> None:
        """Opens a popup window to type a new dialogue line."""
        # Using self.plain_dialogue_list as the parent ensures the popup centers correctly
        text, ok = QInputDialog.getText(
            self.plain_dialogue_list, 
            "Add Plain Dialogue", 
            "Enter the dialogue text:"
        )
        
        # If the user clicked OK and didn't leave it blank
        if ok and text.strip():
            self.plain_dialogue_list.addItem(text.strip())
            self._save_dialogue_state()

    def _on_remove_plain_dialogue(self) -> None:
        """Removes the currently selected line from the list."""
        current_row: int = self.plain_dialogue_list.currentRow()
        if current_row >= 0:
            # takeItem removes it from the UI
            self.plain_dialogue_list.takeItem(current_row)
            self._save_dialogue_state()

    def _save_dialogue_state(self) -> None:
        """Extracts all items from the UI list and updates the engine manager."""
        if getattr(self, '_is_updating_ui', False): return
        
        new_dialogue = []
        for i in range(self.plain_dialogue_list.count()):
            new_dialogue.append(self.plain_dialogue_list.item(i).text())
        
        if hasattr(self.controller.manager, 'plain_dialogue'):
            self.controller.manager.plain_dialogue = new_dialogue
    
    def _on_add_window_trigger(self) -> None:
        dialog = TriggerDialog(self.window_triggers_list)
        if dialog.exec():
            data = dialog.get_data()
            if not data["text"] or not data["title_matches"]: return
            
            # Format: "Writing bugs? | vscode, code.exe | 50%"
            match_str = ", ".join(data["title_matches"])
            display_text = f"{data['text']} | {match_str} | {int(data['chance']*100)}%"
            
            item = QListWidgetItem(display_text)
            # Store the raw dictionary silently inside the UI item
            item.setData(Qt.ItemDataRole.UserRole, data) 
            
            self.window_triggers_list.addItem(item)
            self._save_trigger_state()

    def _on_remove_window_trigger(self) -> None:
        current_row = self.window_triggers_list.currentRow()
        if current_row >= 0:
            self.window_triggers_list.takeItem(current_row)
            self._save_trigger_state()

    def _save_trigger_state(self) -> None:
        if getattr(self, '_is_updating_ui', False): return
        
        new_triggers = []
        for i in range(self.window_triggers_list.count()):
            item = self.window_triggers_list.item(i)
            # Extract the raw dictionary back out of the UI item
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                new_triggers.append(data)
                
        self.controller.manager.window_triggers = new_triggers
    
    def _on_edit_plain_dialogue(self) -> None:
        current_item = self.plain_dialogue_list.currentItem()
        if not current_item: return

        text, ok = QInputDialog.getText(
            self.plain_dialogue_list, 
            "Edit Plain Dialogue", 
            "Update the dialogue text:",
            text=current_item.text() # Pre-fill the current text
        )
        
        if ok and text.strip():
            current_item.setText(text.strip())
            self._save_dialogue_state()

    def _on_edit_window_trigger(self) -> None:
        current_item = self.window_triggers_list.currentItem()
        if not current_item: return

        # Extract the hidden dictionary
        current_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not current_data: return

        dialog = TriggerDialog(self.window_triggers_list)
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
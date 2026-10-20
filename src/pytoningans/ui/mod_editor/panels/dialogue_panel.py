from typing import Any, Optional
from PySide6.QtWidgets import (
    QListWidgetItem, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QInputDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QLineEdit
)
from PySide6.QtCore import Qt

from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.components import CollapsibleSection, create_info_label
from pytoningans.ui.mod_editor.dialogs import TriggerDialog
from .base_panel import BasePanel

class DialoguePanel(BasePanel):
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__(controller)
        self._is_updating_ui: bool = False
        
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        """Constructs the UI specific to Dialogue, Speech, and Window Triggers."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.section = CollapsibleSection("Dialogue and Speech")
        sec_layout = QVBoxLayout()
        
        # --- Plain Dialogue UI ---
        sec_layout.addWidget(create_info_label("Plain Dialogue:", "Dialogues randomly spoken while wandering."))
        
        self.plain_filter_input = QLineEdit()
        self.plain_filter_input.setPlaceholderText("Filter plain dialogue...")
        self.plain_filter_input.setClearButtonEnabled(True)
        sec_layout.addWidget(self.plain_filter_input)
        
        self.plain_dialogue_list = QListWidget()
        self.plain_dialogue_list.setMinimumHeight(100)
        sec_layout.addWidget(self.plain_dialogue_list)
        
        plain_btns = QHBoxLayout()
        self.add_plain_btn = QPushButton("(+) Add")
        self.edit_plain_btn = QPushButton("(e) Edit")
        self.del_plain_btn = QPushButton("(-) Remove")
        plain_btns.addWidget(self.add_plain_btn)
        plain_btns.addWidget(self.edit_plain_btn)
        plain_btns.addWidget(self.del_plain_btn)
        sec_layout.addLayout(plain_btns)
        
        # --- Death Dialogue UI ---
        sec_layout.addSpacing(12)
        sec_layout.addWidget(
            create_info_label(
                "Death Dialogue:",
                "Dialogues spoken when the entity dies or takes fatal damage."
            )
        )
        
        self.death_filter_input = QLineEdit()
        self.death_filter_input.setPlaceholderText("Filter death dialogue...")
        self.death_filter_input.setClearButtonEnabled(True)
        sec_layout.addWidget(self.death_filter_input)
        
        self.death_dialogue_list = QListWidget()
        self.death_dialogue_list.setMinimumHeight(100)
        sec_layout.addWidget(self.death_dialogue_list)
        
        death_btns = QHBoxLayout()
        self.add_death_btn = QPushButton("(+) Add")
        self.edit_death_btn = QPushButton("(e) Edit")
        self.del_death_btn = QPushButton("(-) Remove")
        death_btns.addWidget(self.add_death_btn)
        death_btns.addWidget(self.edit_death_btn)
        death_btns.addWidget(self.del_death_btn)
        sec_layout.addLayout(death_btns)
        
        # --- Window Triggers UI (Table Display) ---
        sec_layout.addSpacing(12)
        sec_layout.addWidget(
            create_info_label(
                "Window Triggers:",
                "Dialogues triggered by matching active window titles."
            )
        )
        
        self.trigger_filter_input = QLineEdit()
        self.trigger_filter_input.setPlaceholderText(
            "Filter window triggers by text, window match, chance, or duration..."
        )
        self.trigger_filter_input.setClearButtonEnabled(True)
        sec_layout.addWidget(self.trigger_filter_input)
        
        self.window_triggers_table = QTableWidget()
        self.window_triggers_table.setColumnCount(4)
        self.window_triggers_table.setHorizontalHeaderLabels([
            "Spoken Text", "Window Matches", "Chance", "Duration"
        ])
        
        header: QHeaderView = self.window_triggers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.window_triggers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.window_triggers_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.window_triggers_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.window_triggers_table.setAlternatingRowColors(True)
        self.window_triggers_table.verticalHeader().setVisible(False)
        self.window_triggers_table.setShowGrid(True)
        self.window_triggers_table.setMinimumHeight(160)
        sec_layout.addWidget(self.window_triggers_table)
        
        trigger_btns = QHBoxLayout()
        self.add_trigger_btn = QPushButton("(+) Add")
        self.edit_trigger_btn = QPushButton("(e) Edit")
        self.del_trigger_btn = QPushButton("(-) Remove")
        trigger_btns.addWidget(self.add_trigger_btn)
        trigger_btns.addWidget(self.edit_trigger_btn)
        trigger_btns.addWidget(self.del_trigger_btn)
        sec_layout.addLayout(trigger_btns)
        
        self.section.content_layout.addLayout(sec_layout)
        layout.addWidget(self.section)

    def _connect_signals(self) -> None:
        """Binds this panel's buttons and filter inputs to logic."""
        # Plain dialogue buttons and filter
        self.add_plain_btn.clicked.connect(self._on_add_plain_dialogue)
        self.edit_plain_btn.clicked.connect(self._on_edit_plain_dialogue)
        self.del_plain_btn.clicked.connect(self._on_remove_plain_dialogue)
        self.plain_filter_input.textChanged.connect(self._apply_plain_filter)
        
        # Death dialogue buttons and filter
        self.add_death_btn.clicked.connect(self._on_add_death_dialogue)
        self.edit_death_btn.clicked.connect(self._on_edit_death_dialogue)
        self.del_death_btn.clicked.connect(self._on_remove_death_dialogue)
        self.death_filter_input.textChanged.connect(self._apply_death_filter)
        
        # Window triggers table, buttons and filter
        self.add_trigger_btn.clicked.connect(self._on_add_window_trigger)
        self.edit_trigger_btn.clicked.connect(self._on_edit_window_trigger)
        self.del_trigger_btn.clicked.connect(self._on_remove_window_trigger)
        self.window_triggers_table.cellDoubleClicked.connect(lambda row, col: self._on_edit_window_trigger())
        self.trigger_filter_input.textChanged.connect(self._apply_trigger_filter)

    def load_data(self) -> None:
        """Called by the main window whenever a new mod is selected."""
        self._is_updating_ui = True
        
        # Clear filters on new mod load
        self.plain_filter_input.clear()
        self.death_filter_input.clear()
        self.trigger_filter_input.clear()
        
        # Populate Plain Dialogue
        self.plain_dialogue_list.clear()
        if self.controller.manager.plain_dialogue:
            self.plain_dialogue_list.addItems(self.controller.manager.plain_dialogue)
            
        # Populate Death Dialogue
        self.death_dialogue_list.clear()
        if self.controller.manager.death_dialogue:
            self.death_dialogue_list.addItems(self.controller.manager.death_dialogue)
            
        # Populate Window Triggers Table
        self.window_triggers_table.setRowCount(0)
        if self.controller.manager.window_triggers:
            for trigger in self.controller.manager.window_triggers:
                self._add_trigger_row(trigger)
                
        self._is_updating_ui = False

    def _add_trigger_row(self, trigger: dict[str, Any]) -> None:
        """Inserts a structured row into the Window Triggers table."""
        row: int = self.window_triggers_table.rowCount()
        self.window_triggers_table.insertRow(row)

        text: str = trigger.get("text", "...")
        matches: list[str] = trigger.get("title_matches", [])
        chance: float = float(trigger.get("chance", 1.0))
        duration: int = int(trigger.get("duration", 4000))

        item_text = QTableWidgetItem(text)
        item_text.setData(Qt.ItemDataRole.UserRole, trigger)
        item_text.setToolTip(f"Spoken dialogue: \"{text}\"")

        match_str: str = ", ".join(matches)
        item_matches = QTableWidgetItem(match_str)
        item_matches.setToolTip(f"Matching window titles: {match_str}")

        item_chance = QTableWidgetItem(f"{int(chance * 100)}%")
        item_chance.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_chance.setToolTip(f"Trigger probability: {chance * 100:.1f}%")

        item_duration = QTableWidgetItem(f"{duration}ms")
        item_duration.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_duration.setToolTip(f"Display duration: {duration} ms")

        self.window_triggers_table.setItem(row, 0, item_text)
        self.window_triggers_table.setItem(row, 1, item_matches)
        self.window_triggers_table.setItem(row, 2, item_chance)
        self.window_triggers_table.setItem(row, 3, item_duration)

    # --- Filtering Logic ---
    def _apply_plain_filter(self, filter_text: str) -> None:
        query: str = filter_text.strip().lower()
        for i in range(self.plain_dialogue_list.count()):
            item = self.plain_dialogue_list.item(i)
            item.setHidden(bool(query and query not in item.text().lower()))

    def _apply_death_filter(self, filter_text: str) -> None:
        query: str = filter_text.strip().lower()
        for i in range(self.death_dialogue_list.count()):
            item = self.death_dialogue_list.item(i)
            item.setHidden(bool(query and query not in item.text().lower()))

    def _apply_trigger_filter(self, filter_text: str) -> None:
        query: str = filter_text.strip().lower()
        for row in range(self.window_triggers_table.rowCount()):
            if not query:
                self.window_triggers_table.setRowHidden(row, False)
                continue
            
            cell_0: Optional[QTableWidgetItem] = self.window_triggers_table.item(row, 0)
            cell_1: Optional[QTableWidgetItem] = self.window_triggers_table.item(row, 1)
            cell_2: Optional[QTableWidgetItem] = self.window_triggers_table.item(row, 2)
            cell_3: Optional[QTableWidgetItem] = self.window_triggers_table.item(row, 3)

            combined: str = " ".join([
                cell_0.text() if cell_0 is not None else "",
                cell_1.text() if cell_1 is not None else "",
                cell_2.text() if cell_2 is not None else "",
                cell_3.text() if cell_3 is not None else ""
            ]).lower()

            self.window_triggers_table.setRowHidden(row, query not in combined)

    # --- Plain Dialogue Actions ---
    def _on_add_plain_dialogue(self) -> None:
        """Opens a popup window to type a new plain dialogue line."""
        text, ok = QInputDialog.getText(
            self.plain_dialogue_list, 
            "Add Plain Dialogue", 
            "Enter the dialogue text:"
        )
        if ok and text.strip():
            self.plain_dialogue_list.addItem(text.strip())
            self._save_dialogue_state()
            self._apply_plain_filter(self.plain_filter_input.text())

    def _on_remove_plain_dialogue(self) -> None:
        """Removes the currently selected plain dialogue line from the list."""
        current_row: int = self.plain_dialogue_list.currentRow()
        if current_row >= 0:
            self.plain_dialogue_list.takeItem(current_row)
            self._save_dialogue_state()

    def _on_edit_plain_dialogue(self) -> None:
        current_item: QListWidgetItem = self.plain_dialogue_list.currentItem()
        if not current_item: return

        text, ok = QInputDialog.getText(
            self.plain_dialogue_list, 
            "Edit Plain Dialogue", 
            "Update the dialogue text:",
            text=current_item.text()
        )
        if ok and text.strip():
            current_item.setText(text.strip())
            self._save_dialogue_state()
            self._apply_plain_filter(self.plain_filter_input.text())

    def _save_dialogue_state(self) -> None:
        """Extracts all plain dialogue items and updates the engine manager."""
        if self._is_updating_ui: return
        new_dialogue: list[str] = [
            self.plain_dialogue_list.item(i).text() for i in range(self.plain_dialogue_list.count())
        ]
        self.controller.manager.plain_dialogue = new_dialogue

    # --- Death Dialogue Actions ---
    def _on_add_death_dialogue(self) -> None:
        """Opens a popup window to type a new death dialogue line."""
        text, ok = QInputDialog.getText(
            self.death_dialogue_list,
            "Add Death Dialogue",
            "Enter the death dialogue text:"
        )
        if ok and text.strip():
            self.death_dialogue_list.addItem(text.strip())
            self._save_death_dialogue_state()
            self._apply_death_filter(self.death_filter_input.text())

    def _on_remove_death_dialogue(self) -> None:
        """Removes the currently selected death dialogue line from the list."""
        current_row: int = self.death_dialogue_list.currentRow()
        if current_row >= 0:
            self.death_dialogue_list.takeItem(current_row)
            self._save_death_dialogue_state()

    def _on_edit_death_dialogue(self) -> None:
        current_item = self.death_dialogue_list.currentItem()
        if not current_item: return

        text, ok = QInputDialog.getText(
            self.death_dialogue_list,
            "Edit Death Dialogue",
            "Update the death dialogue text:",
            text=current_item.text()
        )
        if ok and text.strip():
            current_item.setText(text.strip())
            self._save_death_dialogue_state()
            self._apply_death_filter(self.death_filter_input.text())

    def _save_death_dialogue_state(self) -> None:
        """Extracts all death dialogue items and updates the engine manager."""
        if self._is_updating_ui: return
        new_death_dialogue: list[str] = [
            self.death_dialogue_list.item(i).text() for i in range(self.death_dialogue_list.count())
        ]
        self.controller.manager.death_dialogue = new_death_dialogue

    # --- Window Triggers Actions ---
    def _on_add_window_trigger(self) -> None:
        dialog = TriggerDialog(self.window_triggers_table)
        if dialog.exec():
            data: dict[str, Any] = dialog.get_data()
            if not data["text"] or not data["title_matches"]: return
            
            self._add_trigger_row(data)
            new_row: int = self.window_triggers_table.rowCount() - 1
            self.window_triggers_table.selectRow(new_row)
            self._save_trigger_state()
            self._apply_trigger_filter(self.trigger_filter_input.text())

    def _on_remove_window_trigger(self) -> None:
        current_row: int = self.window_triggers_table.currentRow()
        if current_row >= 0:
            self.window_triggers_table.removeRow(current_row)
            self._save_trigger_state()

    def _save_trigger_state(self) -> None:
        """Extracts all trigger dictionaries from the table items and updates the engine manager."""
        if self._is_updating_ui: return
        new_triggers: list[dict[str, Any]] = []
        for row in range(self.window_triggers_table.rowCount()):
            item_0: Optional[QTableWidgetItem] = self.window_triggers_table.item(row, 0)
            if item_0 is None: continue
            data = item_0.data(Qt.ItemDataRole.UserRole)
            if data:
                new_triggers.append(data)
        self.controller.manager.window_triggers = new_triggers

    def _on_edit_window_trigger(self) -> None:
        current_row: int = self.window_triggers_table.currentRow()
        if current_row < 0: return

        item_0: Optional[QTableWidgetItem] = self.window_triggers_table.item(current_row, 0)
        if item_0 is None: return

        current_data: Optional[dict[str, Any]] = item_0.data(Qt.ItemDataRole.UserRole)
        if not current_data: return

        dialog = TriggerDialog(self.window_triggers_table)
        dialog.set_data(current_data)
        
        if dialog.exec():
            new_data: dict[str, Any] = dialog.get_data()
            if not new_data["text"] or not new_data["title_matches"]: return
            
            # Update data and cells for this row
            text = new_data.get("text", "...")
            matches = new_data.get("title_matches", [])
            chance = float(new_data.get("chance", 1.0))
            duration = int(new_data.get("duration", 4000))

            item_0.setText(text)
            item_0.setData(Qt.ItemDataRole.UserRole, new_data)
            item_0.setToolTip(f"Spoken dialogue: \"{text}\"")

            item_1: Optional[QTableWidgetItem] = self.window_triggers_table.item(current_row, 1)
            if item_1 is not None:
                match_str = ", ".join(matches)
                item_1.setText(match_str)
                item_1.setToolTip(f"Matching window titles: {match_str}")

            item2: Optional[QTableWidgetItem] = self.window_triggers_table.item(current_row, 2)
            if item2 is not None:
                item2.setText(f"{int(chance * 100)}%")
                item2.setToolTip(f"Trigger probability: {chance * 100:.1f}%")

            item3: Optional[QTableWidgetItem] = self.window_triggers_table.item(current_row, 3)
            if item3 is not None:
                item3.setText(f"{duration}ms")
                item3.setToolTip(f"Display duration: {duration} ms")

            self._save_trigger_state()
            self._apply_trigger_filter(self.trigger_filter_input.text())

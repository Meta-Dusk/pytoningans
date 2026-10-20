from PySide6.QtWidgets import (
    QListWidgetItem, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QInputDialog,
    QLineEdit, QMessageBox
)

from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.components import CollapsibleSection, create_info_label
from .base_panel import BasePanel

class InstanceNamesPanel(BasePanel):
    """Panel for editing the pool of unique instance names assigned to spawned entities."""
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__(controller)
        self._is_updating_ui: bool = False

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.section = CollapsibleSection("Instance Names Pool")
        sec_layout = QVBoxLayout()

        sec_layout.addWidget(
            create_info_label(
                "Instance Names Pool:",
                "Optional pool of unique names randomly assigned to newly spawned entities of this mod. "
                "If empty, instances default to '<Display Name>', '<Display Name> #2', etc."
            )
        )

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter instance names...")
        self.filter_input.setClearButtonEnabled(True)
        sec_layout.addWidget(self.filter_input)

        self.names_list = QListWidget()
        self.names_list.setMinimumHeight(110)
        sec_layout.addWidget(self.names_list)

        btns_layout = QHBoxLayout()
        self.add_btn = QPushButton("(+) Add")
        self.edit_btn = QPushButton("(e) Edit")
        self.del_btn = QPushButton("(-) Remove")
        self.clear_btn = QPushButton("Clear All")

        self.edit_btn.setEnabled(False)
        self.del_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)

        btns_layout.addWidget(self.add_btn)
        btns_layout.addWidget(self.edit_btn)
        btns_layout.addWidget(self.del_btn)
        btns_layout.addWidget(self.clear_btn)
        sec_layout.addLayout(btns_layout)

        self.section.content_layout.addLayout(sec_layout)
        layout.addWidget(self.section)

    def _connect_signals(self) -> None:
        self.add_btn.clicked.connect(self._on_add_name)
        self.edit_btn.clicked.connect(self._on_edit_name)
        self.del_btn.clicked.connect(self._on_remove_name)
        self.clear_btn.clicked.connect(self._on_clear_all)
        self.names_list.itemDoubleClicked.connect(lambda _: self._on_edit_name())
        self.names_list.itemSelectionChanged.connect(self._update_button_states)
        self.filter_input.textChanged.connect(self._apply_filter)

    def _update_button_states(self) -> None:
        has_sel: bool = len(self.names_list.selectedItems()) > 0
        total_items: int = self.names_list.count()
        self.edit_btn.setEnabled(has_sel)
        self.del_btn.setEnabled(has_sel)
        self.clear_btn.setEnabled(total_items > 0)

    def _update_section_title(self) -> None:
        count: int = self.names_list.count()
        base_title: str = f"Instance Names Pool ({count})"
        self.section.title = base_title
        if self.section.content.isVisible():
            self.section.btn.setText(f"▼  {base_title}")
        else:
            self.section.btn.setText(f"▶  {base_title}")

    def load_data(self) -> None:
        self._is_updating_ui = True
        self.filter_input.clear()
        self.names_list.clear()

        names: list[str] = self.controller.get_instance_names()
        if names: self.names_list.addItems(names)

        self._update_button_states()
        self._update_section_title()
        self._is_updating_ui = False

    def _sync_to_controller(self) -> None:
        if self._is_updating_ui:
            return
        names: list[str] = [
            self.names_list.item(i).text() for i in range(self.names_list.count())
        ]
        self.controller.set_instance_names(names)
        self._update_button_states()
        self._update_section_title()

    def _apply_filter(self, filter_text: str) -> None:
        query: str = filter_text.strip().lower()
        for i in range(self.names_list.count()):
            item: QListWidgetItem = self.names_list.item(i)
            item.setHidden(bool(query and query not in item.text().lower()))

    def _on_add_name(self) -> None:
        text, ok = QInputDialog.getText(
            self,
            "Add Instance Name",
            "Enter entity instance name:"
        )
        if ok and text.strip():
            self.names_list.addItem(text.strip())
            self._sync_to_controller()
            self._apply_filter(self.filter_input.text())

    def _on_edit_name(self) -> None:
        item: QListWidgetItem = self.names_list.currentItem()
        if not item: return
        text, ok = QInputDialog.getText(
            self,
            "Edit Instance Name",
            "Edit entity instance name:",
            text=item.text()
        )
        if ok and text.strip():
            item.setText(text.strip())
            self._sync_to_controller()
            self._apply_filter(self.filter_input.text())

    def _on_remove_name(self) -> None:
        row: int = self.names_list.currentRow()
        if row >= 0:
            self.names_list.takeItem(row)
            self._sync_to_controller()

    def _on_clear_all(self) -> None:
        if self.names_list.count() == 0: return
        reply = QMessageBox.question(
            self,
            "Clear Instance Names",
            "Are you sure you want to clear all instance names for this mod?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.names_list.clear()
            self._sync_to_controller()


from typing import Optional
from PySide6.QtWidgets import (
    QListWidgetItem, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QInputDialog,
    QLineEdit, QMessageBox
)

from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.components import CollapsibleSection, create_info_label
from .base_panel import BasePanel

SUGGESTED_TAGS: list[str] = [
    "consumable",
    "healing",
    "food",
    "potion",
    "weapon",
    "armor",
    "currency",
    "key",
    "equipment",
    "boss",
    "undead",
    "hostile",
    "friendly",
    "passive",
    "structure",
    "portal",
    "interactable",
    "collectible",
]

class TagsPanel(BasePanel):
    """Panel for configuring entity semantic tags used for identification and AI behaviors."""
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__(controller)
        self._is_updating_ui: bool = False

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.section = CollapsibleSection("Entity Tags")
        sec_layout = QVBoxLayout()

        sec_layout.addWidget(
            create_info_label(
                "Entity Tags:",
                "Semantic tags for identifying entity properties, capabilities, or item classifications "
                "(e.g. 'consumable', 'healing', 'weapon', 'boss', 'portal'). "
                "Living entities and AI behaviors can actively seek or react to these tags."
            )
        )

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter tags...")
        self.filter_input.setClearButtonEnabled(True)
        sec_layout.addWidget(self.filter_input)

        self.tags_list = QListWidget()
        self.tags_list.setMinimumHeight(110)
        sec_layout.addWidget(self.tags_list)

        btns_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ Add")
        self.edit_btn = QPushButton("/\\ Edit")
        self.del_btn = QPushButton("- Remove")
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
        self.add_btn.clicked.connect(self._on_add_tag)
        self.edit_btn.clicked.connect(self._on_edit_tag)
        self.del_btn.clicked.connect(self._on_remove_tag)
        self.clear_btn.clicked.connect(self._on_clear_all)
        self.tags_list.itemDoubleClicked.connect(lambda _: self._on_edit_tag())
        self.tags_list.itemSelectionChanged.connect(self._update_button_states)
        self.filter_input.textChanged.connect(self._apply_filter)

    def _update_button_states(self) -> None:
        has_sel: bool = len(self.tags_list.selectedItems()) > 0
        total_items: int = self.tags_list.count()
        self.edit_btn.setEnabled(has_sel)
        self.del_btn.setEnabled(has_sel)
        self.clear_btn.setEnabled(total_items > 0)

    def _update_section_title(self) -> None:
        count: int = self.tags_list.count()
        base_title: str = f"Entity Tags ({count})"
        self.section.title = base_title
        if self.section.content.isVisible():
            self.section.btn.setText(f"▼  {base_title}")
        else:
            self.section.btn.setText(f"▶  {base_title}")

    def load_data(self) -> None:
        self._is_updating_ui = True
        self.filter_input.clear()
        self.tags_list.clear()

        tags: list[str] = self.controller.get_tags()
        if tags:
            self.tags_list.addItems(tags)

        self._update_button_states()
        self._update_section_title()
        self._is_updating_ui = False

    def _sync_to_controller(self) -> None:
        if self._is_updating_ui:
            return
        tags: list[str] = [
            self.tags_list.item(i).text() for i in range(self.tags_list.count())
        ]
        self.controller.set_tags(tags)
        self._update_button_states()
        self._update_section_title()

    def _apply_filter(self, filter_text: str) -> None:
        query: str = filter_text.strip().lower()
        for i in range(self.tags_list.count()):
            item: QListWidgetItem = self.tags_list.item(i)
            item.setHidden(bool(query and query not in item.text().lower()))

    def _on_add_tag(self) -> None:
        text, ok = QInputDialog.getItem(
            self,
            "Add Entity Tag",
            "Select a preset tag or type a custom tag (comma-separated allowed):",
            SUGGESTED_TAGS,
            0,
            True
        )
        if ok and text.strip():
            tokens: list[str] = [t.strip().lower() for t in text.split(",") if t.strip()]
            existing_tags: set[str] = {
                self.tags_list.item(i).text().lower() for i in range(self.tags_list.count())
            }
            added_any: bool = False
            for token in tokens:
                if token not in existing_tags:
                    self.tags_list.addItem(token)
                    existing_tags.add(token)
                    added_any = True

            if added_any:
                self._sync_to_controller()
                self._apply_filter(self.filter_input.text())
            elif tokens:
                QMessageBox.information(
                    self, "Tag Exists", f"Tag(s) already exist: {', '.join(tokens)}"
                )

    def _on_edit_tag(self) -> None:
        item: Optional[QListWidgetItem] = self.tags_list.currentItem()
        if not item:
            return
        text, ok = QInputDialog.getText(
            self,
            "Edit Entity Tag",
            "Edit entity tag:",
            text=item.text()
        )
        if ok and text.strip():
            clean_tag: str = text.strip().lower()
            existing: set[str] = {
                self.tags_list.item(i).text().lower()
                for i in range(self.tags_list.count())
                if self.tags_list.item(i) is not item
            }
            if clean_tag in existing:
                QMessageBox.warning(self, "Duplicate Tag", f"Tag '{clean_tag}' already exists.")
                return
            item.setText(clean_tag)
            self._sync_to_controller()
            self._apply_filter(self.filter_input.text())

    def _on_remove_tag(self) -> None:
        row: int = self.tags_list.currentRow()
        if row >= 0:
            self.tags_list.takeItem(row)
            self._sync_to_controller()

    def _on_clear_all(self) -> None:
        if self.tags_list.count() == 0:
            return
        reply = QMessageBox.question(
            self,
            "Clear Entity Tags",
            "Are you sure you want to clear all tags for this mod?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.tags_list.clear()
            self._sync_to_controller()


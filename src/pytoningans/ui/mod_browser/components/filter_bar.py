"""
PyToNingans Mod Browser - Search and Filter Bar
=============================================
Provides real-time search, category filtering, sorting options,
and installed-only toggle controls for the community catalog.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QComboBox, QCheckBox
)

from pytoningans.core.constants import EntityType


class FilterBarWidget(QWidget):
    """Interactive filtering and sorting bar for the community mod browser."""

    filters_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(8)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search mods by name, author, tag, or pack contents...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(lambda: self.filters_changed.emit())
        layout.addWidget(self.search_input, stretch=3)

        # Category Filter
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", "all")
        self.category_combo.addItem("Local Creations Only", "local")
        self.category_combo.addItem("Modpacks Only", "pack")
        self.category_combo.addItem("Entities Only", EntityType.ENTITY)
        self.category_combo.addItem("Items Only", EntityType.ITEM)
        self.category_combo.addItem("Structures Only", EntityType.STRUCTURE)
        self.category_combo.currentIndexChanged.connect(lambda: self.filters_changed.emit())
        layout.addWidget(self.category_combo, stretch=1)

        # Sort Filter
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Highest Rated", "rating")
        self.sort_combo.addItem("Most Downloaded", "downloads")
        self.sort_combo.addItem("Newest Releases", "newest")
        self.sort_combo.addItem("Alphabetical (A-Z)", "name")
        self.sort_combo.currentIndexChanged.connect(lambda: self.filters_changed.emit())
        layout.addWidget(self.sort_combo, stretch=1)

        # Installed Only Toggle
        self.installed_checkbox = QCheckBox("Installed Only")
        self.installed_checkbox.toggled.connect(lambda: self.filters_changed.emit())
        layout.addWidget(self.installed_checkbox)

    @property
    def query(self) -> str:
        return self.search_input.text().strip()

    @property
    def category(self) -> str:
        return self.category_combo.currentData() or "all"

    @property
    def sort_by(self) -> str:
        return self.sort_combo.currentData() or "rating"

    @property
    def installed_only(self) -> bool:
        return self.installed_checkbox.isChecked()


from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QCheckBox, QSpinBox

from pytoningans.ui.mod_editor.components import (
    CollapsibleSection, create_info_label, create_spinbox
)


class GridSettingsPanel(QWidget):
    """Panel containing the grid extraction column and row settings."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.grid_section = CollapsibleSection("Grid and Extraction Settings")
        form = QFormLayout()
        
        self.cols_spin: QSpinBox = create_spinbox(1, 100)
        self.rows_spin: QSpinBox = create_spinbox(1, 100)
        
        form.addRow(create_info_label("Columns:", "Total columns."), self.cols_spin)
        form.addRow(create_info_label("Rows:", "Total rows."), self.rows_spin)
        self.grid_section.content_layout.addLayout(form)
        layout.addWidget(self.grid_section)


class DebugSettingsPanel(QWidget):
    """Panel containing debug visual toggles (borders, attack range)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.debug_section = CollapsibleSection("Debug Settings")
        sec_layout = QVBoxLayout()
        
        self.borders_check = QCheckBox("Show Sprite Borders (Blue)")
        self.range_check = QCheckBox("Show Attack Range (Red Circle)")
        
        sec_layout.addWidget(self.borders_check)
        sec_layout.addWidget(self.range_check)
        self.debug_section.content_layout.addLayout(sec_layout)
        layout.addWidget(self.debug_section)


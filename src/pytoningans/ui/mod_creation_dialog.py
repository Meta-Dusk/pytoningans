import json, shutil, re
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QSpinBox, QPushButton, QFileDialog, QMessageBox, QWidget
)
from PySide6.QtCore import Qt

from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.tool_tip import ToolTipLabel
from pytoningans.core.config_schema import ModConfig
from pytoningans.core.constants import PetState, AnimationMeta

class ModCreationDialog(QDialog):
    def __init__(self, mods_dir: str | Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.mods_dir: Path = Path(mods_dir)
        self.selected_image_path: Path | None = None
        self.new_mod_folder: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.resize(450, 320)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self, "Create New Mod")
        main_layout.addWidget(self.title_bar)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form = QFormLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("e.g. my_cool_pet")
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. My Cool Pet")
        
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 100)
        self.cols_spin.setValue(4)
        
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 100)
        self.rows_spin.setValue(len(PetState))
        
        form.addRow(self._create_info_label(
            "Internal Folder Name:", 
            "The exact folder name on your drive. Use only letters, numbers, hyphens, and underscores."
        ), self.folder_input)
        
        form.addRow(self._create_info_label(
            "Display Name:", 
            "The human-readable name of the pet shown in the main menu."
        ), self.name_input)
        
        form.addRow(self._create_info_label(
            "Authoring Columns:", 
            "How many columns the sprite sheet is divided into evenly (used to calculate base tile width)."
        ), self.cols_spin)
        
        form.addRow(self._create_info_label(
            "Authoring Rows:", 
            "How many rows the sprite sheet is divided into evenly (used to calculate base tile height)."
        ), self.rows_spin)
        
        layout.addLayout(form)
        
        img_layout = QHBoxLayout()
        self.img_btn = QPushButton("Select Sprite Sheet (.png)")
        self.img_btn.clicked.connect(self._select_image)
        self.img_label = QLabel("No image selected")
        
        img_layout.addWidget(self.img_btn)
        img_layout.addWidget(self.img_label, stretch=1)
        layout.addLayout(img_layout)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Create Mod")
        self.create_btn.clicked.connect(self._create_mod)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.create_btn)
        layout.addLayout(btn_layout)
        
        main_layout.addWidget(content)

    def _create_info_label(self, text: str, tooltip_text: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(text)
        icon_lbl = ToolTipLabel(text="[?]", tooltip_text=tooltip_text)
        
        layout.addWidget(lbl)
        layout.addWidget(icon_lbl)
        layout.addStretch() 
        return widget

    def _select_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Sprite Sheet", "", "Images (*.png)"
        )
        if file_path:
            self.selected_image_path = Path(file_path)
            self.img_label.setText(self.selected_image_path.name)

    def _create_mod(self) -> None:
        folder_name: str = self.folder_input.text().strip()
        display_name: str = self.name_input.text().strip()
        
        if not folder_name or not display_name:
            QMessageBox.warning(self, "Error", "Folder name and display name are required.")
            return
            
        if not re.match(r"^[a-zA-Z0-9_-]+$", folder_name):
            QMessageBox.warning(self, "Error", "Folder name can only contain letters, numbers, hyphens, and underscores.")
            return
            
        if not self.selected_image_path:
            QMessageBox.warning(self, "Error", "Please select a sprite sheet (.png).")
            return
            
        target_dir: Path = self.mods_dir / folder_name
        if target_dir.exists():
            QMessageBox.warning(self, "Error", f"A mod folder named '{folder_name}' already exists.")
            return
            
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(self.selected_image_path, target_dir / "sprite_sheet.png")
            
            # Read user-selected grid dimensions
            cols = self.cols_spin.value()
            rows = self.rows_spin.value()
            
            self._generate_default_config(display_name, target_dir / "config.json", cols=cols, rows=rows)
            self.new_mod_folder = folder_name
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create mod: {str(e)}")
    
    def _generate_default_config(
        self, display_name: str, config_path: Path,
        *, cols: int = 4, rows: int = len(PetState)
    ) -> None:
        # Scale default animations to respect the chosen row/column dimensions
        animations = {
            state.value: AnimationMeta(
                row=min(i, max(0, rows - 1)),
                start_frame=0,
                end_frame=max(0, cols - 1)
            )
            for i, state in enumerate(PetState)
        }

        new_config = ModConfig(
            name=display_name,
            columns=cols,
            rows=rows,
            animations=animations
        )
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(new_config.to_dict(), f, indent=4)
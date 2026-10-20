"""
PyToNingans Mod Creation Dialog
===============================
Provides an interactive creation wizard for standalone entity/item/structure mods,
new modpack containers with shared controllers, and adding child entities into modpacks.
"""
from __future__ import annotations

import json, re, shutil
from pathlib import Path
from typing import Optional, Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
    QWidget, QTextEdit
)

from pytoningans.core.config_schema import ModConfig
from pytoningans.core.constants import (
    AnimationMeta, EntityState, EntityType, ItemState, StructureState
)
from pytoningans.core.mod_manager import get_available_packs, ModPack
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.tool_tip import ToolTipLabel


class ModCreationDialog(QDialog):
    """Wizard for creating standalone mods, new modpack bundles, or child entities in modpacks."""

    def __init__(self, mods_dir: str | Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.mods_dir: Path = Path(mods_dir)
        self.selected_image_path: Optional[Path] = None
        self.new_mod_folder: str = ""
        self.is_pack_creation: bool = False

        self._setup_ui()
        self._on_mode_changed(0)

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.resize(520, 600)
        self.setAcceptDrops(True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, "Create New Mod or Modpack", can_minimize=False, can_maximize=False)
        main_layout.addWidget(self.title_bar)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(10)

        # Creation Mode Selector
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("<b>Creation Target:</b>"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Standalone Mod (Single Object)", userData="standalone")
        self.mode_combo.addItem("New Modpack (Content Bundle)", userData="new_pack")
        self.mode_combo.addItem("Add Object into Existing Modpack", userData="pack_child")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo, stretch=1)
        layout.addLayout(mode_layout)

        form = QFormLayout()

        # Target Pack selector (only shown when adding to existing pack)
        self.pack_selector_combo = QComboBox()
        self.pack_selector_row = self._add_form_row(
            form, "Target Modpack:", self.pack_selector_combo,
            "Select which installed modpack will contain this new entity."
        )

        # Sub-folder category (only shown when adding to existing pack)
        self.sub_cat_combo = QComboBox()
        self.sub_cat_combo.addItem("entities", "entities")
        self.sub_cat_combo.addItem("items", "items")
        self.sub_cat_combo.addItem("structures", "structures")
        self.sub_cat_row = self._add_form_row(
            form, "Category Folder:", self.sub_cat_combo,
            "Subfolder inside the modpack where files will be stored."
        )

        # Common inputs: folder and name
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("e.g. my_cool_entity")
        self.folder_row = self._add_form_row(
            form, "Folder / ID:", self.folder_input,
            "Internal folder name on disk (letters, numbers, hyphens, and underscores only)."
        )

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. My Cool Entity")
        self.name_row = self._add_form_row(
            form, "Display Name:", self.name_input,
            "Human-readable title displayed in menus."
        )

        # Modpack specific fields: Author and Description
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("e.g. YourName")
        self.author_row = self._add_form_row(
            form, "Author Handle:", self.author_input,
            "Your creator handle or username."
        )

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Brief description of the modpack and its contents...")
        self.desc_input.setMaximumHeight(65)
        self.desc_row = self._add_form_row(
            form, "Pack Description:", self.desc_input,
            "Short summary of what this pack provides."
        )

        # Entity specific fields: Grid dimensions and Entity Type
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 100); self.cols_spin.setValue(4)
        self.cols_row = self._add_form_row(
            form, "Authoring Columns:", self.cols_spin,
            "Columns dividing the sprite sheet evenly (used to compute base tile width)."
        )

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 100)
        self.rows_spin.setValue(len(EntityState))
        self.rows_row = self._add_form_row(
            form, "Authoring Rows:", self.rows_spin,
            "Rows dividing the sprite sheet evenly (used to compute base tile height)."
        )

        self.type_combo = QComboBox()
        self.type_combo.addItem("Living Entity", userData=EntityType.ENTITY)
        self.type_combo.addItem("Static Structure (Single Sprite)", userData="static_structure")
        self.type_combo.addItem("Animated Structure (Multi-State)", userData="animated_structure")
        self.type_combo.addItem("Static Item (Single Sprite)", userData="static_item")
        self.type_combo.addItem("Animated Item (Multi-State)", userData="animated_item")
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.type_row = self._add_form_row(form, "Entity Type:", self.type_combo)

        layout.addLayout(form)

        # Sprite Sheet Selection (Entity / Item / Structure only)
        self.sprite_widget = QWidget()
        sprite_box = QVBoxLayout(self.sprite_widget)
        sprite_box.setContentsMargins(0, 0, 0, 0); sprite_box.setSpacing(6)

        img_layout = QHBoxLayout()
        self.img_btn = QPushButton("Select Sprite Sheet (.png)")
        self.img_btn.clicked.connect(self._select_image)
        self.img_label = QLabel("No image selected")
        img_layout.addWidget(self.img_btn)
        img_layout.addWidget(self.img_label, stretch=1)
        sprite_box.addLayout(img_layout)

        # Image Preview Box
        self.preview_label = QLabel("Drag and Drop PNG here\nor use the button above")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 2px dashed #888; color: #888; border-radius: 5px;")
        self.preview_label.setMinimumHeight(150)
        sprite_box.addWidget(self.preview_label)

        layout.addWidget(self.sprite_widget)
        layout.addStretch()

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Create Mod"); self.create_btn.clicked.connect(self._create_mod)
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.create_btn)
        layout.addLayout(btn_layout)

        main_layout.addWidget(content)

    def _add_form_row(
        self, form: QFormLayout, label_text: str, field_widget: QWidget, tooltip: str = ""
    ) -> tuple[QWidget, QWidget]:
        if tooltip:
            lbl = self._create_info_label(label_text, tooltip)
        else:
            lbl = QLabel(label_text)
        form.addRow(lbl, field_widget)
        return lbl, field_widget

    def _set_row_visible(self, row: tuple[QWidget, QWidget], visible: bool) -> None:
        row[0].setVisible(visible)
        row[1].setVisible(visible)

    def _on_mode_changed(self, _: int) -> None:
        mode: str = self.mode_combo.currentData()
        is_pack: bool = mode == "new_pack"
        is_child: bool = mode == "pack_child"

        # Visibility toggles
        self._set_row_visible(self.pack_selector_row, is_child)
        self._set_row_visible(self.sub_cat_row, is_child)
        self._set_row_visible(self.author_row, is_pack)
        self._set_row_visible(self.desc_row, is_pack)
        self._set_row_visible(self.cols_row, not is_pack)
        self._set_row_visible(self.rows_row, not is_pack)
        self._set_row_visible(self.type_row, not is_pack)
        self.sprite_widget.setVisible(not is_pack)

        if is_pack:
            self.create_btn.setText("Create Modpack")
            self.folder_input.setPlaceholderText("e.g. fantasy_creatures_pack")
            self.name_input.setPlaceholderText("e.g. Fantasy Creatures Pack")
        elif is_child:
            self.create_btn.setText("Add to Modpack")
            self.folder_input.setPlaceholderText("e.g. goblin_warrior")
            self.name_input.setPlaceholderText("e.g. Goblin Warrior")
            self._populate_pack_selector()
        else:
            self.create_btn.setText("Create Mod")
            self.folder_input.setPlaceholderText("e.g. my_cool_entity")
            self.name_input.setPlaceholderText("e.g. My Cool Entity")

    def _populate_pack_selector(self) -> None:
        self.pack_selector_combo.clear()
        packs: dict[str, ModPack] = get_available_packs(self.mods_dir)
        for pack_id, pack in packs.items():
            self.pack_selector_combo.addItem(f"{pack.name} ({pack_id})", userData=pack_id)
        if self.pack_selector_combo.count() == 0:
            self.pack_selector_combo.addItem("No existing modpacks found", userData=None)

    def _on_type_changed(self, _: int) -> None:
        selected_type: str = self.type_combo.currentData()
        match selected_type:
            case "static_structure":
                self.cols_spin.setValue(1)
                self.rows_spin.setValue(1)
            case "animated_structure" | EntityType.STRUCTURE:
                self.cols_spin.setValue(4)
                self.rows_spin.setValue(len(StructureState))
            case "static_item":
                self.cols_spin.setValue(1)
                self.rows_spin.setValue(1)
            case "animated_item":
                self.cols_spin.setValue(4)
                self.rows_spin.setValue(len(ItemState))
            case _:
                self.cols_spin.setValue(4)
                self.rows_spin.setValue(len(EntityState))

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

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            url: QUrl = event.mimeData().urls()[0]
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".png"):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        url: QUrl = event.mimeData().urls()[0]
        self._set_image(Path(url.toLocalFile()))
        event.acceptProposedAction()

    def _select_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Sprite Sheet", "", "Images (*.png)"
        )
        if file_path:
            self._set_image(Path(file_path))

    def _set_image(self, path: Path) -> None:
        self.selected_image_path = path
        self.img_label.setText(path.name)
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return
        scaled: QPixmap = pixmap.scaled(
            450, 150,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)
        self.preview_label.setStyleSheet("border: 2px solid #555; border-radius: 5px;")

    def _create_mod(self) -> None:
        mode = self.mode_combo.currentData()
        folder_name: str = self.folder_input.text().strip()
        display_name: str = self.name_input.text().strip()

        if not folder_name or not display_name:
            QMessageBox.warning(self, "Error", "Folder name and display name are required.")
            return

        if not re.match(r"^[a-zA-Z0-9_-]+$", folder_name):
            QMessageBox.warning(
                self, "Error",
                "Folder name can only contain letters, numbers, hyphens, and underscores.",
            )
            return

        if folder_name.lower() in {"api", "__pycache__"}:
            QMessageBox.warning(self, "Error", f"'{folder_name}' is a reserved engine folder name.")
            return

        # Case 1: Create New Modpack Container
        if mode == "new_pack":
            self._create_new_pack(folder_name, display_name)
            return

        # Case 2: Create Child Entity inside Modpack
        if mode == "pack_child":
            self._create_pack_child(folder_name, display_name)
            return

        # Case 3: Create Standalone Mod
        self._create_standalone_mod(folder_name, display_name)

    def _create_new_pack(self, folder_name: str, display_name: str) -> None:
        target_dir: Path = self.mods_dir / folder_name
        if target_dir.exists():
            QMessageBox.warning(self, "Error", f"A folder named '{folder_name}' already exists.")
            return

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "entities").mkdir(exist_ok=True)
            (target_dir / "items").mkdir(exist_ok=True)
            (target_dir / "structures").mkdir(exist_ok=True)

            author: str = (
                self.author_input.text().strip() or "Modder"
            )
            desc: str = (
                self.desc_input.toPlainText().strip() or
                f"Content pack containing multiple mods."
            )

            manifest: dict[str, Any] = {
                "id": folder_name,
                "name": display_name,
                "version": "1.0.0",
                "author": author,
                "description": desc,
                "shared_script": "pack.py",
                "sub_mods": [],
            }
            (target_dir / "pack.json").write_text(
                json.dumps(manifest, indent=4), encoding="utf-8"
            )

            # Scaffold starter pack controller
            pack_script: str = (
                f'"""Shared runtime controller for modpack \'{display_name}\'."""\n'
                "from pytoningans.core.api import BaseModPack, PackMenuAction\n\n\n"
                "class PackController(BaseModPack):\n"
                "    def on_pack_loaded(self) -> None:\n"
                "        # Initialize shared variables across all pack entities\n"
                "        self.shared_state['status'] = 'Active'\n\n"
                "    def on_entity_spawned(self, entity) -> None:\n"
                "        # Called when any entity belonging to this pack spawns\n"
                "        pass\n\n"
                "    def get_context_menu_actions(self, entity) -> list[PackMenuAction]:\n"
                "        # Return custom desktop context menu actions for pack entities\n"
                "        return []\n"
            )
            (target_dir / "pack.py").write_text(pack_script, encoding="utf-8")

            self.new_mod_folder = folder_name
            self.is_pack_creation = True
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create modpack: {str(e)}")

    def _create_pack_child(self, folder_name: str, display_name: str) -> None:
        pack_id: str = self.pack_selector_combo.currentData()
        if not pack_id:
            QMessageBox.warning(self, "Error", "Please select a target modpack.")
            return

        category: str = self.sub_cat_combo.currentData() or "entities"
        target_dir: Path = self.mods_dir / pack_id / category / folder_name

        if target_dir.exists():
            QMessageBox.warning(
                self, "Error",
                f"'{folder_name}' already exists in pack '{pack_id}/{category}'."
            )
            return

        if self.selected_image_path is None:
            QMessageBox.warning(
                self, "Error", "Please select a sprite sheet (.png)."
            )
            return

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(self.selected_image_path, target_dir / "sprite_sheet.png")

            cols: int = self.cols_spin.value()
            rows: int = self.rows_spin.value()
            self._generate_default_config(
                display_name, target_dir / "config.json", cols=cols, rows=rows
            )

            # Update pack.json sub_mods list if present
            pack_json_path: Path = self.mods_dir / pack_id / "pack.json"
            if pack_json_path.exists():
                try:
                    data: dict[str, Any] = json.loads(pack_json_path.read_text(encoding="utf-8"))
                    sub_mods: list[Any] = data.get("sub_mods", [])
                    relative_sub: str = f"{category}/{folder_name}"
                    if relative_sub not in sub_mods:
                        sub_mods.append(relative_sub)
                        data["sub_mods"] = sub_mods
                        pack_json_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
                except Exception:
                    pass

            self.new_mod_folder = f"{pack_id}:{category}/{folder_name}"
            self.is_pack_creation = False
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create pack entity: {str(e)}")

    def _create_standalone_mod(self, folder_name: str, display_name: str) -> None:
        if self.selected_image_path is None:
            QMessageBox.warning(self, "Error", "Please select a sprite sheet (.png).")
            return

        target_dir: Path = self.mods_dir / folder_name
        if target_dir.exists():
            QMessageBox.warning(self, "Error", f"A mod folder named '{folder_name}' already exists.")
            return

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(self.selected_image_path, target_dir / "sprite_sheet.png")

            cols: int = self.cols_spin.value()
            rows: int = self.rows_spin.value()
            self._generate_default_config(display_name, target_dir / "config.json", cols=cols, rows=rows)

            self.new_mod_folder = folder_name
            self.is_pack_creation = False
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create mod: {str(e)}")

    def _generate_default_config(
        self, display_name: str, config_path: Path,
        *, cols: int = 4, rows: int = len(EntityState)
    ) -> None:
        selected_data: str = self.type_combo.currentData()
        is_static: bool = selected_data in ("static_item", "static_structure")
        entity_type: EntityType

        if selected_data in ("static_item", "animated_item", EntityType.ITEM):
            entity_type = EntityType.ITEM
            state_enum = ItemState
        elif selected_data in ("static_structure", "animated_structure", EntityType.STRUCTURE):
            entity_type = EntityType.STRUCTURE
            state_enum = StructureState
        else:
            entity_type = EntityType.ENTITY
            state_enum = EntityState

        if is_static:
            animations = {
                state.value: AnimationMeta(row=0, start_frame=0, end_frame=0, loop=True)
                for state in state_enum
            }
        else:
            animations = {
                state.value: AnimationMeta(
                    row=min(i, max(0, rows - 1)),
                    start_frame=0,
                    end_frame=max(0, cols - 1),
                    loop=True,
                )
                for i, state in enumerate(state_enum)
            }

        new_config = ModConfig(
            name=display_name,
            entity_type=entity_type,
            is_static=is_static,
            columns=cols,
            rows=rows,
            animations=animations,
        )

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(new_config.to_dict(), f, indent=4)
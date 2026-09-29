import os, subprocess
from typing import Dict, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QCheckBox, QPushButton, QFormLayout
)
from pytoningans.core.constants import BehaviorType
from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.components import CollapsibleSection, create_spinbox, create_info_label

class BehaviorStatsPanel(QWidget):
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__()
        self.controller = controller
        self._is_updating_ui = False
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.section = CollapsibleSection("Core Entity Stats")
        form = QFormLayout()
        
        self.can_fly_check = QCheckBox("Enable Flight (Ignores Gravity)")
        self.max_health_spin = create_spinbox(1, 9999)
        self.atk_dmg_spin = create_spinbox(0, 9999)
        self.atk_range_spin = create_spinbox(0, 2000)
        self.jump_height_spin = create_spinbox(0, 100)
        
        self.behavior_type_combo = QComboBox()
        for b_type in BehaviorType:
            self.behavior_type_combo.addItem(b_type.value.capitalize(), userData=b_type)
            
        form.addRow(create_info_label("Behavior Type:", "Determines engine AI logic."), self.behavior_type_combo)
        form.addRow("", self.can_fly_check)
        form.addRow(create_info_label("Max Health:", "Total health points."), self.max_health_spin)
        form.addRow(create_info_label("Attack Damage:", "Damage dealt per hit."), self.atk_dmg_spin)
        form.addRow(create_info_label("Attack Range (px):", "Maximum distance to strike."), self.atk_range_spin)
        form.addRow(create_info_label("Jump Height:", "Initial vertical velocity."), self.jump_height_spin)
        
        self.section.content_layout.addLayout(form)
        layout.addWidget(self.section)

    def _connect_signals(self) -> None:
        self.behavior_type_combo.currentIndexChanged.connect(self._on_edited)
        self.can_fly_check.stateChanged.connect(self._on_edited)
        for spin in (self.max_health_spin, self.atk_dmg_spin, self.atk_range_spin, self.jump_height_spin):
            spin.valueChanged.connect(self._on_edited)

    def _on_edited(self, *_) -> None:
        if self._is_updating_ui: return
        stats: Dict[str, Any] = {
            "type": self.behavior_type_combo.currentData(),
            "can_fly": self.can_fly_check.isChecked(),
            "max_health": self.max_health_spin.value(),
            "attack_damage": self.atk_dmg_spin.value(),
            "attack_range": self.atk_range_spin.value(),
            "jump_height": self.jump_height_spin.value()
        }
        self.controller.update_behavior_stats(stats)

    def load_data(self) -> None:
        self._is_updating_ui = True
        stats = self.controller.get_behavior_stats()
        self.can_fly_check.setChecked(stats["can_fly"])
        self.max_health_spin.setValue(stats["max_health"])
        self.atk_dmg_spin.setValue(stats["attack_damage"])
        self.atk_range_spin.setValue(stats["attack_range"])
        self.jump_height_spin.setValue(stats["jump_height"])
        
        current_type = stats.get("type", BehaviorType.NEUTRAL)
        self.behavior_type_combo.setCurrentIndex(self.behavior_type_combo.findData(current_type))
        self._is_updating_ui = False

class BehaviorScriptPanel(QWidget):
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__()
        self.controller = controller
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.section = CollapsibleSection("Behavior AI Options")
        form = QFormLayout()
        
        self.add_btn = QPushButton("Create Custom AI")
        self.edit_btn = QPushButton("Open in VS Code")
        self.delete_btn = QPushButton("Delete Script")
        
        form.addWidget(self.add_btn)
        form.addWidget(self.edit_btn)
        form.addWidget(self.delete_btn)
        self.section.content_layout.addLayout(form)
        layout.addWidget(self.section)

    def _connect_signals(self) -> None:
        self.add_btn.clicked.connect(self._open_script)
        self.edit_btn.clicked.connect(self._open_script)
        self.delete_btn.clicked.connect(self._delete_script)

    def _get_script_path(self) -> Path:
        return self.controller.manager.current_mod_path / "behavior.py"

    def load_data(self) -> None:
        exists = self._get_script_path().exists()
        self.add_btn.setEnabled(not exists)
        self.edit_btn.setEnabled(exists)
        self.delete_btn.setEnabled(exists)

    def _open_script(self) -> None:
        path = self._get_script_path()
        if not path.exists():
            boilerplate = (
                "from api import BasePetBehavior, IPet, Pos2D\n\n"
                "class Behavior(BasePetBehavior):\n"
                "    def on_decision_tick(self, pet: IPet) -> bool:\n"
                "        return False\n"
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(boilerplate)
            self.load_data()
            
        try:
            # Cast Path objects to strings for the CLI arguments
            subprocess.Popen(['code', str(self.controller.manager.mods_dir), str(path)], shell=True)
        except Exception:
            # os.startfile natively supports Path-like objects in Python 3.8+
            import os
            os.startfile(path)

    def _delete_script(self) -> None:
        path = self._get_script_path()
        if path.exists():
            path.unlink()
            self.load_data()
from typing import Any
from PySide6.QtWidgets import (
    QVBoxLayout, QComboBox, QCheckBox, QPushButton, QFormLayout, QSpacerItem
)

from pytoningans.core.constants import BehaviorType, AttackType, DeathAnimation
from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.components import CollapsibleSection, create_spinbox, create_info_label
from .base_panel import BasePanel, BaseBehaviorPanel

class BehaviorStatsPanel(BasePanel):
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__(controller)
        self._is_updating_ui = False
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.section = CollapsibleSection("Core Entity Stats")
        form = QFormLayout()
        
        self.can_fly_check = QCheckBox("Enable Flight (Ignores Gravity)")
        self.can_climb_walls_check = QCheckBox("Allow Wall Climbing (Runs up Window Sides)")
        self.max_health_spin = create_spinbox(1, 9999)
        self.atk_dmg_spin = create_spinbox(0, 9999)
        self.atk_range_spin = create_spinbox(0, 2000)
        self.jump_height_spin = create_spinbox(0, 100)
        
        self.atk_type_combo = QComboBox()
        for atk_type in AttackType:
            self.atk_type_combo.addItem(atk_type.value.capitalize(), userData=atk_type)
        
        self.behavior_type_combo = QComboBox()
        for b_type in BehaviorType:
            self.behavior_type_combo.addItem(b_type.value.capitalize(), userData=b_type)
            
        form.addRow(create_info_label("Behavior Type:", "Determines engine AI logic."), self.behavior_type_combo)
        form.addRow("", self.can_fly_check)
        form.addRow("", self.can_climb_walls_check)
        form.addRow(create_info_label("Max Health:", "Total health points."), self.max_health_spin)
        form.addRow(create_info_label("Attack Damage:", "Damage dealt per hit."), self.atk_dmg_spin)
        form.addRow(create_info_label("Attack Range (px):", "Maximum distance to strike."), self.atk_range_spin)
        form.addRow(create_info_label("Attack Type:", "How many entities can be damaged."), self.atk_type_combo)
        form.addRow(create_info_label("Jump Height:", "Initial vertical velocity."), self.jump_height_spin)
        
        self.section.content_layout.addLayout(form)
        layout.addWidget(self.section)

    def _connect_signals(self) -> None:
        self.behavior_type_combo.currentIndexChanged.connect(self._on_edited)
        self.can_fly_check.stateChanged.connect(self._on_edited)
        self.can_climb_walls_check.stateChanged.connect(self._on_edited)
        for spin in (self.max_health_spin, self.atk_dmg_spin, self.atk_range_spin, self.jump_height_spin):
            spin.valueChanged.connect(self._on_edited)

    def _on_edited(self, *_) -> None:
        if self._is_updating_ui: return
        stats: dict[str, Any] = {
            "type": self.behavior_type_combo.currentData(),
            "can_fly": self.can_fly_check.isChecked(),
            "can_climb_walls": self.can_climb_walls_check.isChecked(),
            "max_health": self.max_health_spin.value(),
            "attack_damage": self.atk_dmg_spin.value(),
            "attack_range": self.atk_range_spin.value(),
            "jump_height": self.jump_height_spin.value(),
            "attack_type": self.atk_type_combo.currentData(),
        }
        self.controller.update_behavior_stats(stats)

    def load_data(self) -> None:
        self._is_updating_ui = True
        stats = self.controller.get_behavior_stats()
        self.can_fly_check.setChecked(stats.get("can_fly", False))
        self.can_climb_walls_check.setChecked(stats.get("can_climb_walls", False))
        self.max_health_spin.setValue(stats["max_health"])
        self.atk_dmg_spin.setValue(stats["attack_damage"])
        self.atk_range_spin.setValue(stats["attack_range"])
        self.jump_height_spin.setValue(stats["jump_height"])
        
        current_type = stats.get("type", BehaviorType.NEUTRAL)
        self.behavior_type_combo.setCurrentIndex(self.behavior_type_combo.findData(current_type))
        
        atk_type = stats.get("attack_type", AttackType.SINGLE)
        self.atk_type_combo.setCurrentIndex(self.atk_type_combo.findData(atk_type))
        
        self._is_updating_ui = False

class BehaviorScriptPanel(BaseBehaviorPanel):
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__(
            controller, override=True, boilerplate_script=(
                "from api.behaviors import BaseEntityBehavior\n"
                "from api.protocols import IEntity\n\n"
                "class Behavior(BaseEntityBehavior):\n"
                "    def on_spawn(self, entity: IEntity) -> None:\n"
                "        pass\n\n"
                "    def on_update(self, entity: IEntity, dt: int) -> None:\n"
                "        pass\n\n"
                "    def on_decision_tick(self, entity: IEntity) -> bool:\n"
                "        # Return True to override default engine movement/AI\n"
                "        return False\n"
            )
        )
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
        
        self.death_anim_combo = QComboBox()
        self.death_anim_combo.addItem("Sprite Sheet (Default)", DeathAnimation.SPRITE)
        self.death_anim_combo.addItem("Rotate Left 90°", DeathAnimation.ROTATE_LEFT)
        self.death_anim_combo.addItem("Rotate Right 90°", DeathAnimation.ROTATE_RIGHT)
        self.death_anim_combo.addItem("Rotate 90° or -90°", DeathAnimation.ROTATE_LEFT_OR_RIGHT)
        
        self.auto_close_check = QCheckBox("Fade Out and Close on Death")
        
        form.addWidget(self.add_btn)
        form.addWidget(self.edit_btn)
        form.addWidget(self.delete_btn)
        form.addItem(QSpacerItem(0, 16))
        
        form.addRow("Death Animation:", self.death_anim_combo)
        form.addRow(self.auto_close_check)
        
        self.section.content_layout.addLayout(form)
        layout.addWidget(self.section)

    def _connect_signals(self) -> None:
        self.add_btn.clicked.connect(self._create_script)
        self.edit_btn.clicked.connect(self._open_script)
        self.delete_btn.clicked.connect(self._delete_script)
        self.death_anim_combo.currentIndexChanged.connect(self._on_death_anim_changed)
        self.auto_close_check.stateChanged.connect(self._on_auto_close_changed)

    def load_data(self) -> None:
        exists: bool = self._get_script_path().exists()
        self.add_btn.setEnabled(not exists)
        self.edit_btn.setEnabled(exists)
        self.delete_btn.setEnabled(exists)
        
        idx: int = self.death_anim_combo.findData(self.controller.manager.death_animation)
        if idx >= 0: self.death_anim_combo.setCurrentIndex(idx)
            
        self.auto_close_check.setChecked(self.controller.manager.auto_close_on_death)
    
    def _on_death_anim_changed(self) -> None:
        self.controller.manager.death_animation = self.death_anim_combo.currentData()

    def _on_auto_close_changed(self, state: int) -> None:
        self.controller.manager.auto_close_on_death = bool(state)


class StructureBehaviorPanel(BaseBehaviorPanel):
    """Behavior panel for Structure mods, managing custom structure scripts."""
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__(
            controller, section_name="Structure Custom Behavior",
            boilerplate_script=(
                "from api.behaviors import BaseStructureBehavior\n"
                "from api.protocols import IEntity, IStructure\n\n"
                "class Behavior(BaseStructureBehavior):\n"
                "    def on_spawn(self, structure: IStructure) -> None:\n"
                "        # Attach teleportation or configure initial state\n"
                "        pass\n\n"
                "    def on_update(self, structure: IStructure, dt: int) -> None:\n"
                "        pass\n\n"
                "    def on_interact(self, structure: IStructure, entity: IEntity) -> None:\n"
                "        # Triggered when a living entity interacts/overlaps with this structure\n"
                "        pass\n"
            )
        )


class ItemBehaviorPanel(BaseBehaviorPanel):
    """Behavior panel for Item mods, managing custom item scripts."""
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__(
            controller, section_name="Item Custom Behavior",
            boilerplate_script=(
                "from api.behaviors import BaseItemBehavior\n"
                "from api.protocols import IEntity, IItem\n\n"
                "class Behavior(BaseItemBehavior):\n"
                "    def on_spawn(self, item: IItem) -> None:\n"
                "        pass\n\n"
                "    def on_update(self, item: IItem, dt: int) -> None:\n"
                "        pass\n\n"
                "    def on_pickup(self, item: IItem, entity: IEntity) -> bool:\n"
                "        # Return True to allow pickup, False to cancel\n"
                "        return True\n\n"
                "    def on_use(self, item: IItem, entity: IEntity | None) -> bool:\n"
                "        # Return True if consumed/handled\n"
                "        return True\n\n"
                "    def on_drop(self, item: IItem, entity: IEntity | None) -> None:\n"
                "        pass\n\n"
                "    def on_interact(self, item: IItem, entity: IEntity) -> bool:\n"
                "        # Triggered when an entity touches the item on the ground\n"
                "        return False\n"
            )
        )

from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QCheckBox

from ..helpers import create_info_row, create_separator

if TYPE_CHECKING:
    from ..window import EntityContextMenu
    from pytoningans.core.entity.base_item import BaseItem
    from pytoningans.core.entity.living_entity import Entity


def build_item_actions(menu: EntityContextMenu, layout: QVBoxLayout, item: BaseItem) -> None:
    """Builds interactive control buttons and target pickers for an item."""
    # Quick Actions: Use & Drop
    row_quick = QHBoxLayout()
    row_quick.setSpacing(6)

    use_btn = QPushButton("Use Item")
    use_btn.setToolTip("Activate or consume this item immediately.")
    use_btn.clicked.connect(lambda: menu.execute_action(item.use))
    row_quick.addWidget(use_btn)

    if item.is_held:
        drop_btn = QPushButton("Drop Item")
        drop_btn.setToolTip("Drop this item from the current holder's hands.")
        drop_btn.clicked.connect(lambda: menu.execute_action(item.drop))
        row_quick.addWidget(drop_btn)

    layout.addLayout(row_quick)

    # ComboBox Target Action: Give to Entity
    if not item.is_held:
        layout.addWidget(
            create_info_row(
                "Give to Entity:",
                "Assign this item directly to a living entity on desktop."
            )
        )

        alive_entities: list[Entity] = []
        if item.world is not None and getattr(item.world, "active_entities", None):
            alive_entities = [e for e in item.world.active_entities if not e.is_dead]

        target_row = QHBoxLayout()
        target_row.setSpacing(6)

        entity_combo = QComboBox()
        menu.track_combo(entity_combo)
        give_btn = QPushButton("Give")

        if alive_entities:
            for e in alive_entities:
                entity_combo.addItem(f"{e.display_name} (HP: {e.current_health})", userData=e)
            give_btn.setToolTip("Directly place this item into the selected entity's hands.")
            give_btn.clicked.connect(
                lambda: menu.execute_action(lambda: item.pick_up(entity_combo.currentData()))
            )
        else:
            entity_combo.addItem("No entities available")
            entity_combo.setEnabled(False)
            give_btn.setEnabled(False)

        target_row.addWidget(entity_combo, stretch=1)
        target_row.addWidget(give_btn)
        layout.addLayout(target_row)

    # Utility options
    row_util = QHBoxLayout()
    row_util.setSpacing(6)

    flip_btn = QPushButton("Flip Horizontally")
    flip_btn.setToolTip("Mirror the item's sprite horizontally.")
    flip_btn.clicked.connect(lambda: menu.execute_action(item.flip))
    row_util.addWidget(flip_btn)
    layout.addLayout(row_util)

    # Gravity Checkbox
    gravity_check = QCheckBox("Affected by Gravity")
    gravity_check.setChecked(item.is_physics_enabled)
    gravity_check.setToolTip("When checked, this item is affected by gravity and falls to desktop edges.")
    gravity_check.toggled.connect(item.set_physics_enabled)
    layout.addWidget(gravity_check)

    layout.addWidget(create_separator())

    # Destroy item
    destroy_btn = QPushButton("Destroy Item")
    destroy_btn.setObjectName("DangerBtn")
    destroy_btn.setToolTip("Permanently delete and remove this item from the world.")
    destroy_btn.clicked.connect(lambda: menu.execute_and_close(item.destroy))
    layout.addWidget(destroy_btn)


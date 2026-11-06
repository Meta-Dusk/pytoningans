from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QComboBox, QCheckBox

from ..helpers import create_info_row, create_separator

if TYPE_CHECKING:
    from PySide6.QtWidgets import QVBoxLayout
    from ..window import EntityContextMenu
    from pytoningans.core.entity.base_item import BaseItem
    from pytoningans.core.entity.living_entity import Entity
    from pytoningans.core.api.modpack import PackMenuAction


def build_item_actions(menu: EntityContextMenu, layout: QVBoxLayout, item: BaseItem) -> None:
    """Builds interactive control buttons and target pickers for an item."""
    # Quick Actions: Use and Drop
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
        if item.world is not None and item.world.active_entities:
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

    # Debug Visualization Toggle (Hitbox)
    hitbox_btn = QPushButton("Hide Hitbox" if item.is_debug_hitbox_visible else "Show Hitbox")
    hitbox_btn.setToolTip("Toggle on-screen visualization of physics collision hitbox.")
    
    def toggle_hitbox() -> None:
        item.toggle_debug_hitboxes()
        hitbox_btn.setText("Hide Hitbox" if item.is_debug_hitbox_visible else "Show Hitbox")
        
    hitbox_btn.clicked.connect(lambda: menu.execute_action(toggle_hitbox))
    layout.addWidget(hitbox_btn)

    _mod_pack_actions(menu, layout, item)

    layout.addWidget(create_separator())

    # Destroy item
    destroy_btn = QPushButton("Destroy Item")
    destroy_btn.setObjectName("DangerBtn")
    destroy_btn.setToolTip("Permanently delete and remove this item from the world.")
    destroy_btn.clicked.connect(lambda: menu.execute_and_close(item.destroy))
    layout.addWidget(destroy_btn)

def _mod_pack_actions(
    menu: EntityContextMenu, layout: QVBoxLayout, item: BaseItem
) -> None:
    # Pack Actions (if part of a Tier 2 Modpack)
    if item.mod_manager is None or item.mod_manager.pack is None: return
    
    pack_actions: list[PackMenuAction] = item.mod_manager.pack.get_context_menu_actions(item)
    if not pack_actions: return
    
    layout.addWidget(create_info_row(f"{item.mod_manager.pack.name}:", "Pack Actions"))
    for action in pack_actions:
        action_btn = QPushButton(action.label)
        if action.tooltip:
            action_btn.setToolTip(action.tooltip)
        action_btn.clicked.connect(lambda _, cb=action.callback: menu.execute_action(cb))
        layout.addWidget(action_btn)

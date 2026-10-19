from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QComboBox

from ..helpers import create_info_row, create_separator

if TYPE_CHECKING:
    from ..window import EntityContextMenu
    from pytoningans.core.entity.living_entity import Entity
    from pytoningans.core.entity.base_item import BaseItem


def build_living_actions(menu: EntityContextMenu, layout: QVBoxLayout, entity: Entity) -> None:
    """Builds interactive control buttons and target pickers for a living entity."""
    if not entity.is_dead:
        # Action Row 1: Talk & Jump
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        talk_btn = QPushButton("Talk To")
        talk_btn.setToolTip("Prompt the entity to speak a random dialogue line immediately.")
        talk_btn.clicked.connect(lambda: menu.execute_action(entity.force_talk))
        row1.addWidget(talk_btn)
        
        if entity.mod_manager is not None and not entity.mod_manager.can_fly:
            jump_btn = QPushButton("Force Jump")
            jump_btn.setToolTip("Make the entity perform an upward jump.")
            jump_btn.clicked.connect(lambda: menu.execute_action(entity.jump))
            row1.addWidget(jump_btn)

        layout.addLayout(row1)

        # Held Item Interactions
        if entity.held_item is not None:
            row_item = QHBoxLayout()
            row_item.setSpacing(6)

            item_name: str = entity.held_item.display_name
            use_btn = QPushButton("Use Held Item")
            use_btn.setToolTip(f"Activate or consume '{item_name}'.")
            use_btn.clicked.connect(lambda: menu.execute_action(entity.use_item))
            row_item.addWidget(use_btn)

            drop_btn = QPushButton("Drop Item")
            drop_btn.setToolTip(f"Drop '{item_name}' from the entity's hands onto the ground.")
            drop_btn.clicked.connect(lambda: menu.execute_action(entity.drop_item))
            row_item.addWidget(drop_btn)

            layout.addLayout(row_item)
        else:
            # ComboBox Target Action: Pick Up Ground Item
            layout.addWidget(
                create_info_row("Pick Up Item:", "Select an available ground item for this entity to pick up.")
            )

            unheld_items: list[BaseItem] = []
            if entity.world is not None and entity.world.active_items:
                unheld_items = [
                    it for it in entity.world.active_items
                    if it.is_interactable and not it.is_held
                ]

            target_row = QHBoxLayout()
            target_row.setSpacing(6)

            item_combo = QComboBox()
            menu.track_combo(item_combo)
            pickup_btn = QPushButton("Pick Up")

            if unheld_items:
                for it in unheld_items:
                    coords: str = f"x:{int(it.x())}, y:{int(it.y())}"
                    item_combo.addItem(f"{it.display_name} ({coords})", userData=it)
                pickup_btn.setToolTip("Command the entity to take this item.")
                pickup_btn.clicked.connect(
                    lambda: menu.execute_action(lambda: entity.pick_up(item_combo.currentData()))
                )
            else:
                item_combo.addItem("No ground items nearby")
                item_combo.setEnabled(False)
                pickup_btn.setEnabled(False)

            target_row.addWidget(item_combo, stretch=1)
            target_row.addWidget(pickup_btn)
            layout.addLayout(target_row)

        # Kill action
        kill_btn = QPushButton("Kill Entity")
        kill_btn.setObjectName("DangerBtn")
        kill_btn.setToolTip("Trigger entity fatal damage and play its death sequence.")
        kill_btn.clicked.connect(lambda: menu.execute_action(entity.die))
        layout.addWidget(kill_btn)
    else:
        # Revive action
        revive_btn = QPushButton("Revive Entity")
        revive_btn.setToolTip("Bring this entity back to life with full health.")
        revive_btn.clicked.connect(lambda: menu.execute_action(entity.revive))
        # Toggle Window Physics (entity-specific override)
        phys_text: str = "Enable Window Physics" if entity.ignore_window_physics else "Ignore Window Physics"
        phys_tip: str = (
            "Re-enable window collision and platforms for this entity."
            if entity.ignore_window_physics else
            "Make this entity ghost through desktop windows (overrides global setting)."
        )
        win_phys_btn = QPushButton(phys_text)
        win_phys_btn.setToolTip(phys_tip)
        def toggle_win_phys() -> None:
            entity.ignore_window_physics = not entity.ignore_window_physics
        win_phys_btn.clicked.connect(lambda: menu.execute_action(toggle_win_phys))
        layout.addWidget(win_phys_btn)

    # Debug Visualization Toggles (Hitbox & Range)
    row_debug = QHBoxLayout()
    row_debug.setSpacing(6)

    hitbox_btn = QPushButton("Hide Hitbox" if entity.is_debug_hitbox_visible else "Show Hitbox")
    hitbox_btn.setToolTip("Toggle on-screen visualization of physics collision and attack hitboxes.")
    def toggle_hitbox() -> None:
        entity.toggle_debug_hitboxes()
        hitbox_btn.setText("Hide Hitbox" if entity.is_debug_hitbox_visible else "Show Hitbox")
    hitbox_btn.clicked.connect(lambda: menu.execute_action(toggle_hitbox))
    row_debug.addWidget(hitbox_btn)

    range_btn = QPushButton("Hide Range" if entity.is_debug_attack_range_visible else "Show Range")
    range_btn.setToolTip("Toggle on-screen visualization of entity attack / aggro range circle.")
    def toggle_range() -> None:
        entity.toggle_debug_attack_range()
        range_btn.setText("Hide Range" if entity.is_debug_attack_range_visible else "Show Range")
    range_btn.clicked.connect(lambda: menu.execute_action(toggle_range))
    row_debug.addWidget(range_btn)

    layout.addLayout(row_debug)

    # Pack Actions (if part of a Tier 2 Modpack)
    if entity.mod_manager is not None and entity.mod_manager.pack is not None:
        pack_actions = entity.mod_manager.pack.get_context_menu_actions(entity)
        if pack_actions:
            layout.addWidget(create_info_row(f"{entity.mod_manager.pack.name}:", "Pack Actions"))
            for act in pack_actions:
                act_btn = QPushButton(act.label)
                if act.tooltip:
                    act_btn.setToolTip(act.tooltip)
                act_cb = act.callback
                act_btn.clicked.connect(lambda _, c=act_cb: menu.execute_action(c))
                layout.addWidget(act_btn)

    layout.addWidget(create_separator())

    # Close / Despawn
    close_btn = QPushButton("Close Entity")
    close_btn.setObjectName("DangerBtn")
    close_btn.setToolTip("Dismiss and despawn this entity from desktop.")
    close_btn.clicked.connect(lambda: menu.execute_and_close(entity.destroy))
    layout.addWidget(close_btn)


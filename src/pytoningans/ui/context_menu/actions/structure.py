from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QCheckBox

from pytoningans.core.constants import StructureState
from ..helpers import create_info_row, create_separator

if TYPE_CHECKING:
    from ..window import EntityContextMenu
    from pytoningans.core.entity.base_structure import BaseStructure
    from pytoningans.core.components import BaseComponent


def build_structure_actions(menu: EntityContextMenu, layout: QVBoxLayout, structure: BaseStructure) -> None:
    """Builds interactive control buttons and portal link pickers for a structure."""
    status_text: str = (
        "Deactivate" if structure.state == StructureState.ACTIVE.value else "Activate"
    )
    row_quick = QHBoxLayout()
    row_quick.setSpacing(6)

    toggle_btn = QPushButton(f"{status_text} Structure")
    toggle_btn.setToolTip("Toggle the structure between IDLE and ACTIVE operational states.")
    toggle_btn.clicked.connect(lambda: menu.execute_action(structure.toggle_active))
    row_quick.addWidget(toggle_btn)

    flip_btn = QPushButton("Flip Horizontally")
    flip_btn.setToolTip("Mirror the structure's sprite horizontally.")
    flip_btn.clicked.connect(lambda: menu.execute_action(structure.flip))
    row_quick.addWidget(flip_btn)

    layout.addLayout(row_quick)

    # Gravity Checkbox
    gravity_check = QCheckBox("Affected by Gravity")
    gravity_check.setChecked(structure.is_physics_enabled)
    gravity_check.setToolTip("When checked, gravity affects this structure.")
    gravity_check.toggled.connect(structure.set_physics_enabled)
    layout.addWidget(gravity_check)

    # Component Target Action: Linked Portal
    from pytoningans.core.components.teleportation import TeleportationComponent
    teleport_comp: Optional[BaseComponent] = structure.get_component("teleportation")
    if isinstance(teleport_comp, TeleportationComponent):
        layout.addWidget(
            create_info_row(
                "Linked Portal:",
                "Connect this portal to another structure for two-way travel."
            )
        )

        target_row = QHBoxLayout()
        target_row.setSpacing(6)

        portal_combo = QComboBox()
        menu.track_combo(portal_combo)
        portal_combo.addItem("None (Unlinked)", userData=None)

        other_structures: list[BaseStructure] = []
        if structure.world is not None and structure.world.manager is not None:
            other_structures = [
                s for s in structure.world.manager.active_structures if s is not structure
            ]

        current_idx: int = 0
        for idx, other in enumerate(other_structures, start=1):
            other_name: str = other.display_name
            coords: str = f"x:{int(other.x())}, y:{int(other.y())}"
            portal_combo.addItem(f"{other_name} ({coords})", userData=other)
            if teleport_comp.linked_portal is other:
                current_idx = idx

        portal_combo.setCurrentIndex(current_idx)

        link_btn = QPushButton("Link")
        link_btn.setToolTip("Apply the selected portal destination.")
        link_btn.clicked.connect(
            lambda: menu.execute_action(lambda: structure._set_linked_portal(portal_combo.currentData()))
        )

        target_row.addWidget(portal_combo, stretch=1)
        target_row.addWidget(link_btn)
        layout.addLayout(target_row)

        remove_tele_btn = QPushButton("Remove Portal Component")
        remove_tele_btn.setToolTip("Detach the teleportation component from this structure.")
        remove_tele_btn.clicked.connect(
            lambda: menu.execute_action(lambda: structure.remove_component("teleportation"))
        )
        layout.addWidget(remove_tele_btn)
    else:
        add_tele_btn = QPushButton("Enable Portal Component")
        add_tele_btn.setToolTip("Equip this structure with a teleportation portal component.")
        add_tele_btn.clicked.connect(
            lambda: menu.execute_action(structure.attach_teleportation)
        )
        layout.addWidget(add_tele_btn)

    layout.addWidget(create_separator())

    # Close structure
    close_btn = QPushButton("Close Structure")
    close_btn.setObjectName("DangerBtn")
    close_btn.setToolTip("Dismiss and despawn this structure from desktop.")
    close_btn.clicked.connect(lambda: menu.execute_and_close(structure.destroy))
    layout.addWidget(close_btn)


from __future__ import annotations

from typing import Optional, Any, TYPE_CHECKING

from PySide6.QtCore import QRect, Qt, QPoint
from PySide6.QtGui import QGuiApplication, QPixmap, QScreen
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QFrame, QWidget
)

from pytoningans.core.constants import StructureState
from pytoningans.ui.tool_tip import ToolTipLabel

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity
    from pytoningans.core.entity.living_entity import Entity
    from pytoningans.core.entity.base_item import BaseItem
    from pytoningans.core.entity.base_structure import BaseStructure
    from pytoningans.core.components import BaseComponent


def _create_info_row(label_text: str, tooltip_text: str) -> QWidget:
    """Helper creating a compact label with a [?] custom tooltip helper icon."""
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    lbl = QLabel(label_text)
    lbl.setObjectName("ContextMenuSection")
    layout.addWidget(lbl)
    layout.addWidget(ToolTipLabel(text="[?]", tooltip_text=tooltip_text))
    layout.addStretch()
    return widget


def _create_separator() -> QFrame:
    """Creates a standardized theme divider line."""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setObjectName("MenuSeparator")
    return sep


class EntityContextMenu(QDialog):
    """
    Custom card-style context popup window for entities, items, and structures.
    Features detailed context actions, combobox target pickers, tooltips,
    and visual target highlighting.
    """
    def __init__(self, target_entity: BaseEntity, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self.entity: BaseEntity = target_entity
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(280)
        self.setMaximumWidth(340)

        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("ContextMenuCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(8)

        #? Header Bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Avatar thumbnail from entity sprite
        pixmap: QPixmap = self.entity.pixmap()
        if not pixmap.isNull():
            thumb = QLabel()
            thumb.setFixedSize(30, 30)
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scaled = pixmap.scaled(
                28, 28,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            thumb.setPixmap(scaled)
            header_layout.addWidget(thumb)

        # Title and Type Subtitle
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        title_lbl = QLabel(self.entity.display_name)
        title_lbl.setObjectName("ContextMenuTitle")
        text_layout.addWidget(title_lbl)

        subtitle_text: str = self._get_subtitle_text()
        subtitle_lbl = QLabel(subtitle_text)
        subtitle_lbl.setObjectName("ContextMenuSubtitle")
        text_layout.addWidget(subtitle_lbl)

        header_layout.addLayout(text_layout, stretch=1)

        # Close button
        close_btn = QPushButton("[X]")
        close_btn.setObjectName("TitleBarCloseBtn")
        close_btn.setFixedSize(26, 26)
        close_btn.setToolTip("Dismiss this context menu")
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)

        card_layout.addLayout(header_layout)
        card_layout.addWidget(_create_separator())

        #? Entity-Specific Content
        from pytoningans.core.entity.living_entity import Entity
        from pytoningans.core.entity.base_item import BaseItem
        from pytoningans.core.entity.base_structure import BaseStructure
        
        if isinstance(self.entity, Entity):
            self._build_living_entity_ui(card_layout, self.entity)
        elif isinstance(self.entity, BaseItem):
            self._build_item_ui(card_layout, self.entity)
        elif isinstance(self.entity, BaseStructure):
            self._build_structure_ui(card_layout, self.entity)
        else:
            self._build_generic_ui(card_layout)

        root_layout.addWidget(self.card)

    def _get_subtitle_text(self) -> str:
        from pytoningans.core.entity.living_entity import Entity
        from pytoningans.core.entity.base_item import BaseItem
        from pytoningans.core.entity.base_structure import BaseStructure
        
        if isinstance(self.entity, Entity):
            max_hp: int = self.entity.mod_manager.max_health if self.entity.mod_manager else 100
            status: str = "Dead" if self.entity.is_dead else f"HP: {self.entity.current_health}/{max_hp}"
            return f"[Living Entity] • {status}"
        elif isinstance(self.entity, BaseItem):
            tags_str: str = ", ".join(sorted(self.entity.tags)) if self.entity.tags else "None"
            state_str: str = "Held" if self.entity.is_held else "Ground"
            return f"[Item: {state_str}] • Tags: {tags_str}"
        elif isinstance(self.entity, BaseStructure):
            state_str: str = self.entity.state.capitalize()
            return f"[Structure] • State: {state_str}"
        return "[Object]"

    # =========================================================================
    # Living Entity Actions
    # =========================================================================
    def _build_living_entity_ui(self, layout: QVBoxLayout, entity: Entity) -> None:
        if not entity.is_dead:
            # Action Row 1
            row1 = QHBoxLayout()
            row1.setSpacing(6)

            talk_btn = QPushButton("Talk To")
            talk_btn.setToolTip("Prompt the entity to speak a random dialogue line immediately.")
            talk_btn.clicked.connect(lambda: self._execute_and_close(entity.force_talk))
            row1.addWidget(talk_btn)

            jump_btn = QPushButton("Force Jump")
            jump_btn.setToolTip("Make the entity perform an upward jump.")
            jump_btn.clicked.connect(lambda: self._execute_and_close(entity.jump))
            row1.addWidget(jump_btn)

            layout.addLayout(row1)

            # Held Item Interactions
            if entity.held_item is not None:
                row_item = QHBoxLayout()
                row_item.setSpacing(6)

                item_name: str = entity.held_item.display_name
                use_btn = QPushButton("Use Held Item")
                use_btn.setToolTip(f"Activate or consume '{item_name}'.")
                use_btn.clicked.connect(lambda: self._execute_and_close(entity.use_item))
                row_item.addWidget(use_btn)

                drop_btn = QPushButton("Drop Item")
                drop_btn.setToolTip(f"Drop '{item_name}' from the entity's hands onto the ground.")
                drop_btn.clicked.connect(lambda: self._execute_and_close(entity.drop_item))
                row_item.addWidget(drop_btn)

                layout.addLayout(row_item)
            else:
                # ComboBox Target Action: Pick Up Ground Item
                layout.addWidget(
                    _create_info_row("Pick Up Item:", "Select an available ground item for this entity to pick up.")
                )

                unheld_items: list[BaseItem] = []
                if entity.world is not None and getattr(entity.world, "active_items", None):
                    unheld_items = [
                        it for it in entity.world.active_items
                        if it.is_interactable and not it.is_held
                    ]

                target_row = QHBoxLayout()
                target_row.setSpacing(6)

                item_combo = QComboBox()
                pickup_btn = QPushButton("Pick Up")

                if unheld_items:
                    for it in unheld_items:
                        item_combo.addItem(f"{it.display_name} (@ {int(it.x())}, {int(it.y())})", userData=it)
                    pickup_btn.setToolTip("Command the entity to take this item.")
                    pickup_btn.clicked.connect(
                        lambda: self._execute_and_close(lambda: entity.pick_up(item_combo.currentData()))
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
            kill_btn.clicked.connect(lambda: self._execute_and_close(entity.die))
            layout.addWidget(kill_btn)
        else:
            # Revive action
            revive_btn = QPushButton("Revive Entity")
            revive_btn.setToolTip("Bring this entity back to life with full health.")
            revive_btn.clicked.connect(lambda: self._execute_and_close(entity.revive))
            layout.addWidget(revive_btn)

        layout.addWidget(_create_separator())

        # Close / Despawn
        close_btn = QPushButton("Close Entity")
        close_btn.setObjectName("DangerBtn")
        close_btn.setToolTip("Dismiss and despawn this entity from desktop.")
        close_btn.clicked.connect(lambda: self._execute_and_close(entity.destroy))
        layout.addWidget(close_btn)

    # =========================================================================
    # Item Actions
    # =========================================================================
    def _build_item_ui(self, layout: QVBoxLayout, item: BaseItem) -> None:
        # Quick Actions: Use & Drop
        row_quick = QHBoxLayout()
        row_quick.setSpacing(6)

        use_btn = QPushButton("Use Item")
        use_btn.setToolTip("Activate or consume this item immediately.")
        use_btn.clicked.connect(lambda: self._execute_and_close(item.use))
        row_quick.addWidget(use_btn)

        if item.is_held:
            drop_btn = QPushButton("Drop Item")
            drop_btn.setToolTip("Drop this item from the current holder's hands.")
            drop_btn.clicked.connect(lambda: self._execute_and_close(item.drop))
            row_quick.addWidget(drop_btn)

        layout.addLayout(row_quick)

        # ComboBox Target Action: Give to Entity
        if not item.is_held:
            layout.addWidget(
                _create_info_row(
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
            give_btn = QPushButton("Give")

            if alive_entities:
                for e in alive_entities:
                    entity_combo.addItem(f"{e.display_name} (HP: {e.current_health})", userData=e)
                give_btn.setToolTip("Directly place this item into the selected entity's hands.")
                give_btn.clicked.connect(
                    lambda: self._execute_and_close(lambda: item.pick_up(entity_combo.currentData()))
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
        flip_btn.clicked.connect(lambda: self._execute_and_close(item.flip))
        row_util.addWidget(flip_btn)
        layout.addLayout(row_util)

        # Gravity Checkbox
        gravity_check = QCheckBox("Affected by Gravity")
        gravity_check.setChecked(item.is_physics_enabled)
        gravity_check.setToolTip("When checked, this item is affected by gravity and falls to desktop edges.")
        gravity_check.toggled.connect(item.set_physics_enabled)
        layout.addWidget(gravity_check)

        layout.addWidget(_create_separator())

        # Destroy item
        destroy_btn = QPushButton("Destroy Item")
        destroy_btn.setObjectName("DangerBtn")
        destroy_btn.setToolTip("Permanently delete and remove this item from the world.")
        destroy_btn.clicked.connect(lambda: self._execute_and_close(item.destroy))
        layout.addWidget(destroy_btn)

    # =========================================================================
    # Structure Actions
    # =========================================================================
    def _build_structure_ui(self, layout: QVBoxLayout, structure: BaseStructure) -> None:
        status_text: str = (
            "Deactivate" if structure.state == StructureState.ACTIVE.value else "Activate"
        )
        row_quick = QHBoxLayout()
        row_quick.setSpacing(6)

        toggle_btn = QPushButton(f"{status_text} Structure")
        toggle_btn.setToolTip("Toggle the structure between IDLE and ACTIVE operational states.")
        toggle_btn.clicked.connect(lambda: self._execute_and_close(structure.toggle_active))
        row_quick.addWidget(toggle_btn)

        flip_btn = QPushButton("Flip Horizontally")
        flip_btn.setToolTip("Mirror the structure's sprite horizontally.")
        flip_btn.clicked.connect(lambda: self._execute_and_close(structure.flip))
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
                _create_info_row(
                    "Linked Portal:",
                    "Connect this portal to another structure for two-way travel."
                )
            )

            target_row = QHBoxLayout()
            target_row.setSpacing(6)

            portal_combo = QComboBox()
            portal_combo.addItem("None (Unlinked)", userData=None)

            other_structures: list[BaseStructure] = []
            if structure.world is not None and structure.world.manager is not None:
                other_structures = [
                    s for s in structure.world.manager.active_structures if s is not structure
                ]

            current_idx: int = 0
            for idx, other in enumerate(other_structures, start=1):
                other_name: str = other.display_name
                coords: str = f"@{int(other.x())}, {int(other.y())}"
                portal_combo.addItem(f"{other_name} ({coords})", userData=other)
                if teleport_comp.linked_portal is other:
                    current_idx = idx

            portal_combo.setCurrentIndex(current_idx)

            link_btn = QPushButton("Link")
            link_btn.setToolTip("Apply the selected portal destination.")
            link_btn.clicked.connect(
                lambda: self._execute_and_close(lambda: structure._set_linked_portal(portal_combo.currentData()))
            )

            target_row.addWidget(portal_combo, stretch=1)
            target_row.addWidget(link_btn)
            layout.addLayout(target_row)

            remove_tele_btn = QPushButton("Remove Portal Component")
            remove_tele_btn.setToolTip("Detach the teleportation component from this structure.")
            remove_tele_btn.clicked.connect(
                lambda: self._execute_and_close(lambda: structure.remove_component("teleportation"))
            )
            layout.addWidget(remove_tele_btn)
        else:
            add_tele_btn = QPushButton("Enable Portal Component")
            add_tele_btn.setToolTip("Equip this structure with a teleportation portal component.")
            add_tele_btn.clicked.connect(
                lambda: self._execute_and_close(structure.attach_teleportation)
            )
            layout.addWidget(add_tele_btn)

        layout.addWidget(_create_separator())

        # Close structure
        close_btn = QPushButton("Close Structure")
        close_btn.setObjectName("DangerBtn")
        close_btn.setToolTip("Dismiss and despawn this structure from desktop.")
        close_btn.clicked.connect(lambda: self._execute_and_close(structure.destroy))
        layout.addWidget(close_btn)

    def _build_generic_ui(self, layout: QVBoxLayout) -> None:
        close_btn = QPushButton("Close Object")
        close_btn.setObjectName("DangerBtn")
        close_btn.clicked.connect(lambda: self._execute_and_close(self.entity.destroy))
        layout.addWidget(close_btn)

    def _execute_and_close(self, action_fn: Any) -> None:
        """Executes the chosen callback and cleanly dismisses the context menu."""
        try: action_fn()
        finally: self.accept()

    def exec_at(self, screen_pos: QPoint) -> int:
        """Positions the popup at screen_pos with boundary clamping and executes modally."""
        self.adjustSize()
        w: int = max(280, self.sizeHint().width())
        h: int = self.sizeHint().height()

        target_x: int = screen_pos.x() + 8
        target_y: int = screen_pos.y() + 8

        screen: Optional[QScreen] = (
            QGuiApplication.screenAt(screen_pos) or QGuiApplication.primaryScreen()
        )
        if screen is not None:
            geom: QRect = screen.availableGeometry()
            if target_x + w > geom.right() - 8:
                target_x = screen_pos.x() - w - 8
            if target_y + h > geom.bottom() - 8:
                target_y = screen_pos.y() - h - 8
            target_x = max(geom.left() + 8, target_x)
            target_y = max(geom.top() + 8, target_y)

        self.move(target_x, target_y)
        return self.exec()

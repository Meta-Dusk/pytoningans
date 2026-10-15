from __future__ import annotations

from typing import Optional, Any, TYPE_CHECKING

from PySide6.QtCore import QRect, Qt, QPoint
from PySide6.QtGui import QGuiApplication, QPixmap, QScreen, QResizeEvent, QMouseEvent
from PySide6.QtWidgets import (
    QDialog, QLayoutItem, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QFrame, QWidget, QScrollArea, QLayout
)

from pytoningans.core.constants import StructureState
from pytoningans.ui.tool_tip import ToolTipLabel
from pytoningans.ui.mod_editor.components import CustomSizeGrip

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


class ContextMenuHeader(QWidget):
    """
    Draggable header bar for the entity context menu window.
    Clicking and dragging on this header smoothly repositions the window on screen.
    """
    def __init__(self, parent_window: EntityContextMenu) -> None:
        super().__init__(parent_window)
        self.parent_window: EntityContextMenu = parent_window
        self._drag_offset: Optional[QPoint] = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self.parent_window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()


class EntityContextMenu(QDialog):
    """
    Draggable, resizable tool window for entity inspection and control.
    Features detailed context actions, combobox target pickers, tooltips,
    horizontal scrollable tag badges, and stays active until closed via [X].
    """
    _active_menu: Optional[EntityContextMenu] = None

    def __init__(self, target_entity: BaseEntity, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.entity: Optional[BaseEntity] = target_entity
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumSize(280, 200)

        self._drag_offset: Optional[QPoint] = None
        self._combos: list[QComboBox] = []
        self.actions_container: Optional[QWidget] = None
        self.actions_layout: Optional[QVBoxLayout] = None
        self.subtitle_lbl: Optional[QLabel] = None
        self._build_ui()

        self.grip = CustomSizeGrip(self)
        self.grip.setFixedSize(16, 16)

    # --- Window Dragging Logic (Card level) ---
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "grip"):
            self.grip.move(
                self.width() - self.grip.width(),
                self.height() - self.grip.height()
            )
            self.grip.raise_()

    def _build_ui(self) -> None:
        if self.entity is None:
            return

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("ContextMenuCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(8)

        # Draggable Header Bar
        self.header_bar = ContextMenuHeader(self)
        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Avatar thumbnail from entity sprite
        pixmap: QPixmap = self.entity.pixmap()
        if not pixmap.isNull():
            thumb = QLabel()
            thumb.setFixedSize(30, 30)
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
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
        title_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text_layout.addWidget(title_lbl)

        self.subtitle_lbl = QLabel(self._get_subtitle_text())
        self.subtitle_lbl.setObjectName("ContextMenuSubtitle")
        self.subtitle_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text_layout.addWidget(self.subtitle_lbl)

        header_layout.addLayout(text_layout, stretch=1)

        # Close button
        close_btn = QPushButton("[X]")
        close_btn.setObjectName("TitleBarCloseBtn")
        close_btn.setFixedSize(26, 26)
        close_btn.setToolTip("Dismiss this entity window")
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)

        card_layout.addWidget(self.header_bar)

        # Dedicated Horizontal Scrollable Tags Section
        tags_section = self._create_tags_section()
        if tags_section is not None:
            card_layout.addWidget(tags_section)

        card_layout.addWidget(_create_separator())

        # Scrollable Action Area
        self.actions_scroll = QScrollArea()
        self.actions_scroll.setObjectName("ContextMenuScrollArea")
        self.actions_scroll.setWidgetResizable(True)
        self.actions_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.actions_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.actions_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.actions_container = QWidget()
        self.actions_container.setObjectName("ContextMenuActionsContainer")
        self.actions_layout = QVBoxLayout(self.actions_container)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)

        self._populate_actions(self.actions_layout)

        self.actions_scroll.setWidget(self.actions_container)
        card_layout.addWidget(self.actions_scroll, stretch=1)

        root_layout.addWidget(self.card)

    def _populate_actions(self, layout: QVBoxLayout) -> None:
        from pytoningans.core.entity.living_entity import Entity
        from pytoningans.core.entity.base_item import BaseItem
        from pytoningans.core.entity.base_structure import BaseStructure

        if isinstance(self.entity, Entity):
            self._build_living_entity_ui(layout, self.entity)
        elif isinstance(self.entity, BaseItem):
            self._build_item_ui(layout, self.entity)
        elif isinstance(self.entity, BaseStructure):
            self._build_structure_ui(layout, self.entity)
        else:
            self._build_generic_ui(layout)

        layout.addStretch()

    def _refresh_actions(self) -> None:
        """Dynamically refreshes action buttons and subtitle when an action is executed."""
        if self.entity is None or self.actions_layout is None:
            return

        if self.subtitle_lbl is not None:
            self.subtitle_lbl.setText(self._get_subtitle_text())

        for combo in self._combos:
            try: combo.clear()
            except RuntimeError: pass
        self._combos.clear()

        self._clear_layout(self.actions_layout)
        self._populate_actions(self.actions_layout)

    def _clear_layout(self, layout: QLayout) -> None:
        while layout.count():
            item: Optional[QLayoutItem] = layout.takeAt(0)
            if item is None: continue
            w: Optional[QWidget] = item.widget()
            item_layout: Optional[QLayout] = item.layout()
            if w is not None:
                w.deleteLater()
            elif item_layout is not None:
                self._clear_layout(item_layout)

    def _create_tags_section(self) -> Optional[QWidget]:
        """Creates a horizontal scrollable strip of tag badges if tags exist."""
        if not self.entity or not getattr(self.entity, "tags", None):
            return None

        scroll = QScrollArea()
        scroll.setObjectName("ContextMenuTagsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(30)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setObjectName("ContextMenuTagsContainer")
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(4)

        for tag in sorted(self.entity.tags):
            badge = QLabel(f"#{tag}")
            badge.setObjectName("ContextMenuTagBadge")
            c_layout.addWidget(badge)

        c_layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _get_subtitle_text(self) -> str:
        if self.entity is None:
            return "[Object]"

        from pytoningans.core.entity.living_entity import Entity
        from pytoningans.core.entity.base_item import BaseItem
        from pytoningans.core.entity.base_structure import BaseStructure

        if isinstance(self.entity, Entity):
            max_hp: int = self.entity.mod_manager.max_health if self.entity.mod_manager else 100
            status: str = "Dead" if self.entity.is_dead else f"HP: {self.entity.current_health}/{max_hp}"
            return f"[Living Entity] • {status}"
        elif isinstance(self.entity, BaseItem):
            state_str: str = "Held" if self.entity.is_held else "Ground"
            return f"[Item: {state_str}]"
        elif isinstance(self.entity, BaseStructure):
            state_str: str = self.entity.state.capitalize()
            return f"[Structure] • State: {state_str}"
        return "[Object]"

    # =========================================================================
    # Living Entity Actions
    # =========================================================================
    def _build_living_entity_ui(self, layout: QVBoxLayout, entity: Entity) -> None:
        if not entity.is_dead:
            # Action Row 1: Talk & Jump
            row1 = QHBoxLayout()
            row1.setSpacing(6)

            talk_btn = QPushButton("Talk To")
            talk_btn.setToolTip("Prompt the entity to speak a random dialogue line immediately.")
            talk_btn.clicked.connect(lambda: self._execute_action(entity.force_talk))
            row1.addWidget(talk_btn)

            jump_btn = QPushButton("Force Jump")
            jump_btn.setToolTip("Make the entity perform an upward jump.")
            jump_btn.clicked.connect(lambda: self._execute_action(entity.jump))
            row1.addWidget(jump_btn)

            layout.addLayout(row1)

            # Held Item Interactions
            if entity.held_item is not None:
                row_item = QHBoxLayout()
                row_item.setSpacing(6)

                item_name: str = entity.held_item.display_name
                use_btn = QPushButton("Use Held Item")
                use_btn.setToolTip(f"Activate or consume '{item_name}'.")
                use_btn.clicked.connect(lambda: self._execute_action(entity.use_item))
                row_item.addWidget(use_btn)

                drop_btn = QPushButton("Drop Item")
                drop_btn.setToolTip(f"Drop '{item_name}' from the entity's hands onto the ground.")
                drop_btn.clicked.connect(lambda: self._execute_action(entity.drop_item))
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
                self._combos.append(item_combo)
                pickup_btn = QPushButton("Pick Up")

                if unheld_items:
                    for it in unheld_items:
                        item_combo.addItem(f"{it.display_name} (@ {int(it.x())}, {int(it.y())})", userData=it)
                    pickup_btn.setToolTip("Command the entity to take this item.")
                    pickup_btn.clicked.connect(
                        lambda: self._execute_action(lambda: entity.pick_up(item_combo.currentData()))
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
            kill_btn.clicked.connect(lambda: self._execute_action(entity.die))
            layout.addWidget(kill_btn)
        else:
            # Revive action
            revive_btn = QPushButton("Revive Entity")
            revive_btn.setToolTip("Bring this entity back to life with full health.")
            revive_btn.clicked.connect(lambda: self._execute_action(entity.revive))
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
        use_btn.clicked.connect(lambda: self._execute_action(item.use))
        row_quick.addWidget(use_btn)

        if item.is_held:
            drop_btn = QPushButton("Drop Item")
            drop_btn.setToolTip("Drop this item from the current holder's hands.")
            drop_btn.clicked.connect(lambda: self._execute_action(item.drop))
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
            self._combos.append(entity_combo)
            give_btn = QPushButton("Give")

            if alive_entities:
                for e in alive_entities:
                    entity_combo.addItem(f"{e.display_name} (HP: {e.current_health})", userData=e)
                give_btn.setToolTip("Directly place this item into the selected entity's hands.")
                give_btn.clicked.connect(
                    lambda: self._execute_action(lambda: item.pick_up(entity_combo.currentData()))
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
        flip_btn.clicked.connect(lambda: self._execute_action(item.flip))
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
        toggle_btn.clicked.connect(lambda: self._execute_action(structure.toggle_active))
        row_quick.addWidget(toggle_btn)

        flip_btn = QPushButton("Flip Horizontally")
        flip_btn.setToolTip("Mirror the structure's sprite horizontally.")
        flip_btn.clicked.connect(lambda: self._execute_action(structure.flip))
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
            self._combos.append(portal_combo)
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
                lambda: self._execute_action(lambda: structure._set_linked_portal(portal_combo.currentData()))
            )

            target_row.addWidget(portal_combo, stretch=1)
            target_row.addWidget(link_btn)
            layout.addLayout(target_row)

            remove_tele_btn = QPushButton("Remove Portal Component")
            remove_tele_btn.setToolTip("Detach the teleportation component from this structure.")
            remove_tele_btn.clicked.connect(
                lambda: self._execute_action(lambda: structure.remove_component("teleportation"))
            )
            layout.addWidget(remove_tele_btn)
        else:
            add_tele_btn = QPushButton("Enable Portal Component")
            add_tele_btn.setToolTip("Equip this structure with a teleportation portal component.")
            add_tele_btn.clicked.connect(
                lambda: self._execute_action(structure.attach_teleportation)
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
        if self.entity is None:
            return
        close_btn = QPushButton("Close Object")
        close_btn.setObjectName("DangerBtn")
        close_btn.clicked.connect(lambda: self._execute_and_close(self.entity.destroy if self.entity else None))
        layout.addWidget(close_btn)

    # =========================================================================
    # Action Execution & Cleanup
    # =========================================================================
    def _execute_action(self, action_fn: Any) -> None:
        """Executes an action and dynamically updates the UI while keeping the window open."""
        try:
            if action_fn is not None:
                action_fn()
        except Exception as e:
            print(f"Error executing context action: {e}")

        if self.entity is not None:
            self._refresh_actions()

    def _execute_and_close(self, action_fn: Any) -> None:
        """Executes action and closes window (used for entity despawn/destroy)."""
        try:
            if action_fn is not None:
                action_fn()
        except Exception as e:
            print(f"Error executing context action: {e}")
        finally:
            self.close()

    def cleanup(self) -> None:
        """Cleans up internal state and entity references to prevent memory leaks."""
        for combo in self._combos:
            try:
                combo.clear()
            except RuntimeError:
                pass
        self._combos.clear()
        self.entity = None

    def closeEvent(self, event: Any) -> None:
        if self.entity is not None:
            self.entity.set_highlighted(False)
            self.entity.resume_death_animations()
            if self.entity._active_context_menu is self:
                self.entity._active_context_menu = None

        if EntityContextMenu._active_menu is self:
            EntityContextMenu._active_menu = None

        self.cleanup()
        event.accept()

    # =========================================================================
    # Window Spawning & Management
    # =========================================================================
    @classmethod
    def show_for_entity(cls, entity: BaseEntity, click_pos: QPoint) -> EntityContextMenu:
        """
        Creates or shows the inspector window for the entity, positioned near it on screen.
        Only one context menu window is active at a time.
        """
        if cls._active_menu is not None:
            try:
                cls._active_menu.close()
            except RuntimeError:
                pass
            cls._active_menu = None

        menu = cls(entity)
        cls._active_menu = menu
        entity._active_context_menu = menu
        entity.set_highlighted(True)
        entity.pause_death_animations()

        menu.adjustSize()
        w: int = max(300, menu.sizeHint().width())
        h: int = max(240, min(500, menu.sizeHint().height()))
        menu.resize(w, h)

        # Calculate spawn location near entity
        spawn_x: int
        spawn_y: int

        if entity.world is not None and getattr(entity.world, "view", None) is not None:
            entity_rect = entity.sceneBoundingRect()
            top_right_view = entity.world.view.mapFromScene(entity_rect.topRight())
            global_top_right = entity.world.view.mapToGlobal(top_right_view)
            spawn_x = global_top_right.x() + 8
            spawn_y = global_top_right.y()
        else:
            spawn_x = click_pos.x() + 8
            spawn_y = click_pos.y() + 8

        screen: Optional[QScreen] = (
            QGuiApplication.screenAt(QPoint(spawn_x, spawn_y)) or
            QGuiApplication.screenAt(click_pos) or
            QGuiApplication.primaryScreen()
        )
        if screen is not None:
            geom: QRect = screen.availableGeometry()
            # If overflowing on the right, place to the left of the entity
            if spawn_x + w > geom.right() - 8:
                if entity.world is not None and getattr(entity.world, "view", None) is not None:
                    top_left_view = entity.world.view.mapFromScene(entity.sceneBoundingRect().topLeft())
                    global_top_left = entity.world.view.mapToGlobal(top_left_view)
                    spawn_x = global_top_left.x() - w - 8
                else:
                    spawn_x = click_pos.x() - w - 8

            # Clamp inside screen boundaries
            spawn_x = max(geom.left() + 8, min(spawn_x, geom.right() - w - 8))
            spawn_y = max(geom.top() + 8, min(spawn_y, geom.bottom() - h - 8))

        menu.move(spawn_x, spawn_y)
        menu.show()
        menu.raise_()
        menu.activateWindow()
        return menu


from __future__ import annotations

from typing import Optional, Any, TYPE_CHECKING

from PySide6.QtCore import QRect, Qt, QPoint
from PySide6.QtGui import QGuiApplication, QPixmap, QScreen, QResizeEvent, QMouseEvent
from PySide6.QtWidgets import (
    QDialog, QLayoutItem, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QFrame, QWidget, QScrollArea, QLayout
)

from pytoningans.ui.mod_editor.components import CustomSizeGrip
from .header import ContextMenuHeader
from .helpers import create_separator
from .actions import populate_actions

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity


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

    def track_combo(self, combo: QComboBox) -> None:
        """Registers a combobox so its references can be cleanly cleared on refresh/cleanup."""
        self._combos.append(combo)

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

        card_layout.addWidget(create_separator())

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

        populate_actions(self, self.actions_layout)

        self.actions_scroll.setWidget(self.actions_container)
        card_layout.addWidget(self.actions_scroll, stretch=1)

        root_layout.addWidget(self.card)

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
        populate_actions(self, self.actions_layout)

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
    # Action Execution & Cleanup
    # =========================================================================
    def execute_action(self, action_fn: Any) -> None:
        """Executes an action and dynamically updates the UI while keeping the window open."""
        try:
            if action_fn is not None:
                action_fn()
        except Exception as e:
            print(f"Error executing context action: {e}")

        if self.entity is not None:
            self._refresh_actions()

    # Backwards-compatible alias
    _execute_action = execute_action

    def execute_and_close(self, action_fn: Any) -> None:
        """Executes action and closes window (used for entity despawn/destroy)."""
        try:
            if action_fn is not None:
                action_fn()
        except Exception as e:
            print(f"Error executing context action: {e}")
        finally:
            self.close()

    # Backwards-compatible alias
    _execute_and_close = execute_and_close

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
            if getattr(self.entity, "_active_context_menu", None) is self:
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


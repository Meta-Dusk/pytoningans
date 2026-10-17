from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QHBoxLayout
)

if TYPE_CHECKING:
    from pytoningans.core.entity_manager import EntityManager


class LiveControlsPanel(QWidget):
    """Panel displaying active world statistics and providing entity/structure life-cycle controls."""

    def __init__(self, manager: EntityManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.manager: EntityManager = manager
        self._setup_ui()

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("MenuSeparator")
        return sep

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Section Header
        live_label = QLabel("Live Controls:")
        live_label.setObjectName("SectionHeader")
        layout.addWidget(live_label)

        # Row 1: Alive Entities
        alive_frame = QFrame()
        alive_frame.setObjectName("ActionRow")
        alive_layout = QHBoxLayout(alive_frame)
        alive_layout.setContentsMargins(10, 5, 10, 5)
        alive_layout.setSpacing(6)

        self.alive_count_label = QLabel("Alive: 0")
        self.alive_count_label.setObjectName("StatAliveLabel")
        alive_layout.addWidget(self.alive_count_label)
        alive_layout.addStretch()

        self.kill_alive_btn = QPushButton("Kill All")
        self.kill_alive_btn.setObjectName("RowBtn")
        self.kill_alive_btn.setToolTip("Trigger death animation for alive entities")
        self.kill_alive_btn.clicked.connect(self._on_kill_alive_clicked)
        alive_layout.addWidget(self.kill_alive_btn)

        self.close_alive_btn = QPushButton("Close All")
        self.close_alive_btn.setObjectName("RowBtn")
        self.close_alive_btn.setToolTip("Close all alive entities immediately")
        self.close_alive_btn.clicked.connect(self._on_close_alive_clicked)
        alive_layout.addWidget(self.close_alive_btn)

        layout.addWidget(alive_frame)

        # Row 2: Dead Entities
        dead_frame = QFrame()
        dead_frame.setObjectName("ActionRow")
        dead_layout = QHBoxLayout(dead_frame)
        dead_layout.setContentsMargins(10, 5, 10, 5)
        dead_layout.setSpacing(6)

        self.dead_count_label = QLabel("Dead: 0")
        self.dead_count_label.setObjectName("StatDeadLabel")
        dead_layout.addWidget(self.dead_count_label)
        dead_layout.addStretch()

        self.revive_dead_btn = QPushButton("Revive All")
        self.revive_dead_btn.setObjectName("RowBtn")
        self.revive_dead_btn.setToolTip("Revive all dead entities back to life")
        self.revive_dead_btn.clicked.connect(self._on_revive_dead_clicked)
        dead_layout.addWidget(self.revive_dead_btn)

        self.close_dead_btn = QPushButton("Close All")
        self.close_dead_btn.setObjectName("RowBtn")
        self.close_dead_btn.setToolTip("Remove all dead entities from the screen")
        self.close_dead_btn.clicked.connect(self._on_close_dead_clicked)
        dead_layout.addWidget(self.close_dead_btn)

        layout.addWidget(dead_frame)

        # Row 3: Structures
        struct_frame = QFrame()
        struct_frame.setObjectName("ActionRow")
        struct_layout = QHBoxLayout(struct_frame)
        struct_layout.setContentsMargins(10, 5, 10, 5)
        struct_layout.setSpacing(6)

        self.struct_count_label = QLabel("Structures: 0")
        self.struct_count_label.setObjectName("StatStructLabel")
        struct_layout.addWidget(self.struct_count_label)
        struct_layout.addStretch()

        self.close_struct_btn = QPushButton("Close All")
        self.close_struct_btn.setObjectName("RowBtn")
        self.close_struct_btn.setToolTip("Close all active structures")
        self.close_struct_btn.clicked.connect(self._on_close_structures_clicked)
        struct_layout.addWidget(self.close_struct_btn)

        layout.addWidget(struct_frame)

        # Row 4: Items
        item_frame = QFrame()
        item_frame.setObjectName("ActionRow")
        item_layout = QHBoxLayout(item_frame)
        item_layout.setContentsMargins(10, 5, 10, 5)
        item_layout.setSpacing(6)

        self.item_count_label = QLabel("Items: 0")
        self.item_count_label.setObjectName("StatItemLabel")
        item_layout.addWidget(self.item_count_label)
        item_layout.addStretch()

        self.close_item_btn = QPushButton("Close All")
        self.close_item_btn.setObjectName("RowBtn")
        self.close_item_btn.setToolTip("Close all active items")
        self.close_item_btn.clicked.connect(self._on_close_items_clicked)
        item_layout.addWidget(self.close_item_btn)

        layout.addWidget(item_frame)

        layout.addWidget(self._create_separator())

        # Global Actions Section
        global_label = QLabel("Global Actions:")
        global_label.setObjectName("SectionHeader")
        layout.addWidget(global_label)

        global_layout = QHBoxLayout()
        global_layout.setSpacing(8)

        self.close_all_entities_btn = QPushButton("Close All Entities")
        self.close_all_entities_btn.setToolTip("Close all entities regardless of alive/dead state")
        self.close_all_entities_btn.clicked.connect(self._on_close_all_entities_clicked)

        self.close_all_objects_btn = QPushButton("Close All Objects")
        self.close_all_objects_btn.setToolTip("Close all entities and structures on all screens")
        self.close_all_objects_btn.clicked.connect(self._on_close_all_objects_clicked)

        global_layout.addWidget(self.close_all_entities_btn, stretch=1)
        global_layout.addWidget(self.close_all_objects_btn, stretch=1)
        layout.addLayout(global_layout)

        self.update_stats()

    def update_stats(self) -> None:
        """Refreshes live entity counts and updates button enabled states."""
        total_entities: int = len(self.manager.active_entities)
        dead_entities: int = sum(1 for p in self.manager.active_entities if p.is_dead)
        alive_entities: int = total_entities - dead_entities
        total_structs: int = len(self.manager.active_structures)
        total_items: int = len(self.manager.active_items)

        self.alive_count_label.setText(f"Alive: {alive_entities}")
        self.dead_count_label.setText(f"Dead: {dead_entities}")
        self.struct_count_label.setText(f"Structures: {total_structs}")
        self.item_count_label.setText(f"Items: {total_items}")

        self.kill_alive_btn.setEnabled(alive_entities > 0)
        self.close_alive_btn.setEnabled(alive_entities > 0)

        self.revive_dead_btn.setEnabled(dead_entities > 0)
        self.close_dead_btn.setEnabled(dead_entities > 0)

        self.close_struct_btn.setEnabled(total_structs > 0)
        self.close_item_btn.setEnabled(total_items > 0)

        self.close_all_entities_btn.setEnabled(total_entities > 0)
        self.close_all_objects_btn.setEnabled(
            total_entities > 0 or total_structs > 0 or total_items > 0
        )

    def _on_kill_alive_clicked(self) -> None:
        """Triggers the death state/animation for all currently alive entities."""
        for entity in list(self.manager.active_entities):
            if not entity.is_dead:
                entity.die()

    def _on_close_alive_clicked(self) -> None:
        """Immediately destroys all currently alive entities."""
        for entity in list(self.manager.active_entities):
            if not entity.is_dead:
                entity.destroy()

    def _on_revive_dead_clicked(self) -> None:
        """Revives all dead entities."""
        for entity in list(self.manager.active_entities):
            if entity.is_dead:
                entity.revive()

    def _on_close_dead_clicked(self) -> None:
        """Immediately destroys all dead entities."""
        for entity in list(self.manager.active_entities):
            if entity.is_dead:
                entity.destroy()

    def _on_close_structures_clicked(self) -> None:
        """Destroys all active structures."""
        for struct in list(self.manager.active_structures):
            struct.destroy()

    def _on_close_items_clicked(self) -> None:
        """Destroys all active items."""
        for item in list(self.manager.active_items):
            item.destroy()

    def _on_close_all_entities_clicked(self) -> None:
        """Destroys all entities regardless of alive/dead state."""
        for entity in list(self.manager.active_entities):
            entity.destroy()

    def _on_close_all_objects_clicked(self) -> None:
        """Destroys all entities, structures, and items across all worlds."""
        for entity in list(self.manager.active_entities):
            entity.destroy()
        for struct in list(self.manager.active_structures):
            struct.destroy()
        for item in list(self.manager.active_items):
            item.destroy()


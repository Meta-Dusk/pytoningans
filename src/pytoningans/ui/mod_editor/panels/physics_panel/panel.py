from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QSpinBox, QLabel,
    QPushButton, QMessageBox, QCheckBox, QSpacerItem
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QPoint, QRect

from pytoningans.core.constants import (
    AnimationMeta, EntityType, StructureState, EntityState, ItemState
)
from pytoningans.ui.mod_editor.components import CollapsibleSection, create_info_label, VerticalResizeHandle
from ..base_panel import BasePanel
from .canvas import PhysicsCanvas

if TYPE_CHECKING:
    from pytoningans.ui.mod_editor.controller import ModEditorController


class PhysicsPanel(BasePanel):
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__(controller)
        self._is_loading: bool = False
        self._copied_physics: dict[str, Any] = {}
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        section = CollapsibleSection("Physics and Alignment")
        
        # Top Controls (organized in 2 clean rows to prevent horizontal overflow)
        top_controls_layout = QVBoxLayout()
        top_controls_layout.setSpacing(6)

        row_1 = QHBoxLayout()
        self.state_label = QLabel("State:")
        self.state_combo = QComboBox()
        self.frame_spin = QSpinBox()
        self.frame_spin.setPrefix("Frame: "); self.frame_spin.setMinimum(0)
        self.copy_btn = QPushButton("Copy")
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setEnabled(False)
        self.static_indicator = QLabel("Static Collision (Shared)")
        self.static_indicator.setStyleSheet("color: #60a5fa; font-weight: bold; font-size: 11px;")
        self.static_indicator.hide()

        row_1.addWidget(self.state_label)
        row_1.addWidget(self.state_combo)
        row_1.addWidget(self.frame_spin)
        row_1.addWidget(self.copy_btn)
        row_1.addWidget(self.paste_btn)
        row_1.addWidget(self.static_indicator)
        row_1.addStretch()

        row_2 = QHBoxLayout()
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setPrefix("Zoom: "); self.zoom_spin.setSuffix("x")
        self.zoom_spin.setRange(1, 20)
        self.reset_view_btn = QPushButton("Reset View")
        self.expand_canvas_btn = QPushButton("⤢ Expand")
        self.expand_canvas_btn.setToolTip("Quickly toggle between standard (340px) and large (520px) canvas height")
        self.expand_canvas_btn.clicked.connect(self._toggle_canvas_expand)

        row_2.addWidget(self.zoom_spin)
        row_2.addWidget(self.reset_view_btn)
        row_2.addWidget(self.expand_canvas_btn)
        row_2.addStretch()

        top_controls_layout.addLayout(row_1)
        top_controls_layout.addLayout(row_2)

        # Canvas and Form Controls
        editor_layout = QHBoxLayout()
        
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)

        self.canvas = PhysicsCanvas()
        self.canvas.setFixedHeight(340)
        self.canvas_handle = VerticalResizeHandle(
            self.canvas, default_height=340, min_height=180, max_height=800
        )
        self.canvas_handle.height_changed.connect(self._on_canvas_height_changed)
        canvas_layout.addWidget(self.canvas)
        canvas_layout.addWidget(self.canvas_handle)

        editor_layout.addWidget(canvas_container, stretch=1)
        self.zoom_spin.setValue(self.canvas.zoom)
        
        form_flags: Qt.AlignmentFlag = (
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignRight
        )
        self.form = QFormLayout(labelAlignment=form_flags, horizontalSpacing=8)
        self.ax_spin = QSpinBox(); self.ax_spin.setRange(0, 999)
        self.ay_spin = QSpinBox(); self.ay_spin.setRange(0, 999)
        self.hx_spin = QSpinBox(); self.hx_spin.setRange(-999, 999)
        self.hy_spin = QSpinBox(); self.hy_spin.setRange(-999, 999)
        self.hw_spin = QSpinBox(); self.hw_spin.setRange(1, 999)
        self.hh_spin = QSpinBox(); self.hh_spin.setRange(1, 999)
        
        self.form.addRow(create_info_label("Anchor", "Animation anchor point."))
        self.form.addRow("X:", self.ax_spin)
        self.form.addRow("Y:", self.ay_spin)
        self.form.addItem(QSpacerItem(0, 16))
        
        self.form.addRow(create_info_label("Hitbox", "Used for collision detection."))
        self.form.addRow("X:", self.hx_spin)
        self.form.addRow("Y:", self.hy_spin)
        self.form.addRow("Width:", self.hw_spin)
        self.form.addRow("Height:", self.hh_spin)
        self.form.addItem(QSpacerItem(0, 16))

        # Hold Anchor controls (living entities only)
        self.hold_header = create_info_label(
            "Item Hold Anchor",
            "Custom point where this entity holds items.\n"
            "If unchecked, default top-of-head holding is used."
        )
        self.hold_check = QCheckBox("Enable Custom Hold Point")
        self.hold_check.setStyleSheet("color: #fbbf24; font-weight: bold;")
        self.hold_x_spin = QSpinBox(); self.hold_x_spin.setRange(-999, 999)
        self.hold_y_spin = QSpinBox(); self.hold_y_spin.setRange(-999, 999)
        self.hold_lbl_x = QLabel("Hold X:")
        self.hold_lbl_y = QLabel("Hold Y:")

        self.form.addRow(self.hold_header)
        self.form.addRow(self.hold_check)
        self.form.addRow(self.hold_lbl_x, self.hold_x_spin)
        self.form.addRow(self.hold_lbl_y, self.hold_y_spin)
        self.form.addItem(QSpacerItem(0, 16))
        
        # Combat widgets (hidden for structures)
        self.attack_frame_check = QCheckBox("Is Attack Frame")
        self.attack_frame_check.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.attack_frame_check.setToolTip("If checked, deals damage on this frame.")
        
        self.show_range_check = QCheckBox("Show Aggro Range (Red Circle)")
        
        self.atkx_spin = QSpinBox(); self.atkx_spin.setRange(-999, 999)
        self.atky_spin = QSpinBox(); self.atky_spin.setRange(-999, 999)
        self.atkw_spin = QSpinBox(); self.atkw_spin.setRange(0, 999)
        self.atkh_spin = QSpinBox(); self.atkh_spin.setRange(0, 999)
        
        self.attack_header = create_info_label("Attack Hitbox", "Used for dealing damage.")
        self.atk_lbl_x = QLabel("X:")
        self.atk_lbl_y = QLabel("Y:")
        self.atk_lbl_w = QLabel("Width:")
        self.atk_lbl_h = QLabel("Height:")

        self.form.addRow(self.attack_frame_check)
        self.form.addRow(self.show_range_check)
        self.form.addRow(self.attack_header)
        self.form.addRow(self.atk_lbl_x, self.atkx_spin)
        self.form.addRow(self.atk_lbl_y, self.atky_spin)
        self.form.addRow(self.atk_lbl_w, self.atkw_spin)
        self.form.addRow(self.atk_lbl_h, self.atkh_spin)
        self.form.addItem(QSpacerItem(0, 16))
        
        self.apply_base_btn = QPushButton("Apply to Entire Animation")
        self.form.addRow(self.apply_base_btn)
        
        self.magic_btn = QPushButton("Magic Propagate Hitbox")
        self.magic_btn.setStyleSheet(
            "color: #a855f7; font-weight: bold; font-family: 'Pixel Code', monospace;"
        )
        self.magic_btn.setToolTip(
            "Applies the current Hitbox's Width and Height to all frames, "
            "keeping them bottom-centered on each frame's Anchor."
        )
        self.form.addRow(self.magic_btn)

        editor_layout.addLayout(self.form)
        
        section.content_layout.addLayout(top_controls_layout)
        section.content_layout.addLayout(editor_layout)
        layout.addWidget(section)

    def _connect_signals(self) -> None:
        self.state_combo.currentIndexChanged.connect(self._on_state_combo_changed)
        self.frame_spin.valueChanged.connect(self.load_data)
        self.zoom_spin.valueChanged.connect(self.canvas.set_zoom)
        self.canvas.zoom_changed.connect(self.zoom_spin.setValue)
        self.reset_view_btn.clicked.connect(self.canvas.reset_view)
        
        self.copy_btn.clicked.connect(self._on_copy)
        self.paste_btn.clicked.connect(self._on_paste)
        
        self.canvas.physics_changed.connect(self._on_canvas_dragged)
        self.apply_base_btn.clicked.connect(self._apply_to_base)
        self.hold_check.stateChanged.connect(self._on_hold_check_toggled)
        self.hold_x_spin.valueChanged.connect(self._on_spinbox_changed)
        self.hold_y_spin.valueChanged.connect(self._on_spinbox_changed)
        self.attack_frame_check.stateChanged.connect(self._on_attack_frame_toggled)
        self.show_range_check.stateChanged.connect(self._on_show_range_toggled)
        self.magic_btn.clicked.connect(self._on_magic_propagate)
        
        for spin in [
            self.ax_spin, self.ay_spin, self.hx_spin, self.hy_spin,
            self.hw_spin, self.hh_spin, self.atkx_spin, self.atky_spin,
            self.atkw_spin, self.atkh_spin
        ]:
            spin.valueChanged.connect(self._on_spinbox_changed)

    def _update_attack_hitbox_visibility(self) -> None:
        is_combat_entity: bool = self.controller.manager.entity_type not in (
            EntityType.STRUCTURE, EntityType.ITEM
        )
        show_attack: bool = is_combat_entity and self.attack_frame_check.isChecked()
        self.attack_header.setVisible(show_attack)
        self.atk_lbl_x.setVisible(show_attack)
        self.atkx_spin.setVisible(show_attack)
        self.atk_lbl_y.setVisible(show_attack)
        self.atky_spin.setVisible(show_attack)
        self.atk_lbl_w.setVisible(show_attack)
        self.atkw_spin.setVisible(show_attack)
        self.atk_lbl_h.setVisible(show_attack)
        self.atkh_spin.setVisible(show_attack)

    def _on_attack_frame_toggled(self, state: int) -> None:
        is_checked: bool = bool(state)
        self._update_attack_hitbox_visibility()
        if not self._is_loading:
            if is_checked and self.atkw_spin.value() == 0 and self.atkh_spin.value() == 0:
                self.atkx_spin.setValue(self.hx_spin.value())
                self.atky_spin.setValue(self.hy_spin.value())
                self.atkw_spin.setValue(max(10, self.hw_spin.value()))
                self.atkh_spin.setValue(max(10, self.hh_spin.value()))
            self._on_spinbox_changed()

    def _update_hold_anchor_visibility(self) -> None:
        is_living: bool = self.controller.manager.entity_type == EntityType.ENTITY
        show_hold: bool = is_living and self.hold_check.isChecked()
        self.hold_header.setVisible(is_living)
        self.hold_check.setVisible(is_living)
        self.hold_lbl_x.setVisible(show_hold)
        self.hold_x_spin.setVisible(show_hold)
        self.hold_lbl_y.setVisible(show_hold)
        self.hold_y_spin.setVisible(show_hold)

    def _on_hold_check_toggled(self, state: int) -> None:
        is_checked: bool = bool(state)
        self._update_hold_anchor_visibility()
        if not self._is_loading:
            if (
                is_checked and self.hold_x_spin.value() == 0 and
                self.hold_y_spin.value() == 0
            ):
                pixmap: QPixmap = self.canvas.frame_pixmap
                if not pixmap.isNull():
                    self.hold_x_spin.setValue(pixmap.width() // 2)
                    self.hold_y_spin.setValue(max(0, int(pixmap.height() * 0.2)))
            self._on_spinbox_changed()

    def _sync_states_dropdown(self) -> None:
        """Populates the combo box from the active animations dictionary keys."""
        prev_data = self.state_combo.currentData()
        current_selection: Optional[str] = str(prev_data) if prev_data else None
        
        self.state_combo.blockSignals(True)
        self.state_combo.clear()
        
        if self.controller.manager.entity_type == EntityType.STRUCTURE.value:
            state_enum = StructureState
        elif self.controller.manager.entity_type == EntityType.ITEM.value:
            state_enum = ItemState
        else:
            state_enum = EntityState
        
        target_idx: int = 0
        for i, state in enumerate(state_enum):
            state_val: str = str(state.value)
            self.state_combo.addItem(state_val.capitalize(), userData=state_val)
            if current_selection and state_val == current_selection:
                target_idx = i
                
        if self.state_combo.count() > 0:
            self.state_combo.setCurrentIndex(target_idx)
        
        self._update_hold_anchor_visibility()
        self._update_attack_hitbox_visibility()
            
        self.state_combo.blockSignals(False)

    def _on_state_combo_changed(self) -> None:
        self.frame_spin.setValue(0)
        self.load_data()

    def load_data(self) -> None:
        if not self.controller.manager.current_mod_folder: return
        self._is_loading = True
        
        # Ensure dropdown options match the currently loaded mod states
        available_keys: list[str] = list(self.controller.manager.animations.keys())
        combo_keys: list[Any] = [self.state_combo.itemData(i) for i in range(self.state_combo.count())]
        if combo_keys != available_keys:
            self._sync_states_dropdown()
            
        state: Optional[str] = self.state_combo.currentData()
        if not state:
            self._is_loading = False
            return
            
        is_combat_entity: bool = self.controller.manager.entity_type not in (
            EntityType.STRUCTURE, EntityType.ITEM
        )
        is_living: bool = self.controller.manager.entity_type == EntityType.ENTITY
        is_static: bool = self.controller.manager.is_static
        
        # Toggle static indicators vs per-state controls
        self.state_label.setVisible(not is_static)
        self.state_combo.setVisible(not is_static)
        self.frame_spin.setVisible(not is_static)
        self.copy_btn.setVisible(not is_static)
        self.paste_btn.setVisible(not is_static)
        self.paste_btn.setEnabled(bool(self._copied_physics))
        self.apply_base_btn.setVisible(not is_static)
        self.magic_btn.setVisible(not is_static)
        self.static_indicator.setVisible(is_static)
        
        # Toggle hold inputs
        self.hold_header.setVisible(is_living)
        self.hold_check.setVisible(is_living)

        # Toggle combat inputs according to entity type
        self.attack_frame_check.setVisible(is_combat_entity)
        self.show_range_check.setVisible(is_combat_entity)

        frame_idx: int = self.frame_spin.value()
        is_attack: bool = False
        atk_hitbox: QRect = QRect(0, 0, 0, 0)
        has_hold: bool = False
        hold_x: int = 0
        hold_y: int = 0
        
        meta: Optional[AnimationMeta] = self.controller.manager.animations.get(state)
        if meta is not None:
            has_hold = meta.has_hold_point
            hold_x = meta.hold_x
            hold_y = meta.hold_y
            total_frames: int = max(1, (meta.end_frame - meta.start_frame) + 1)
            self.frame_spin.setMaximum(total_frames - 1)
            self.frame_spin.setSuffix(f"/{total_frames - 1}")
            
            mapped_index: int = frame_idx % total_frames if meta.loop else min(frame_idx, total_frames - 1)
            if meta.reverse: mapped_index = (total_frames - 1) - mapped_index
            
            frame_key: str = str(mapped_index)
            if frame_key in meta.frame_overrides:
                overrides: dict[str, Any] = meta.frame_overrides[frame_key]
                is_attack = overrides.get("is_attack_frame", False)
                atk_hitbox = QRect(
                    overrides.get("attack_x", 0),
                    overrides.get("attack_y", 0),
                    overrides.get("attack_w", 0),
                    overrides.get("attack_h", 0)
                )
                if "has_hold_point" in overrides:
                    has_hold = bool(overrides["has_hold_point"])
                hold_x = overrides.get("hold_x", hold_x)
                hold_y = overrides.get("hold_y", hold_y)
        
        pixmap: Optional[QPixmap] = self.controller.manager.get_frame(state, frame_idx)
        if pixmap is None:
            self._is_loading = False
            return
            
        anchor, hitbox = self.controller.manager.get_frame_physics(state, frame_idx)
        
        self.ax_spin.setValue(anchor.x())
        self.ay_spin.setValue(anchor.y())
        
        self.hx_spin.setValue(hitbox.x())
        self.hy_spin.setValue(hitbox.y())
        self.hw_spin.setValue(hitbox.width())
        self.hh_spin.setValue(hitbox.height())
        
        self.atkx_spin.setValue(atk_hitbox.x())
        self.atky_spin.setValue(atk_hitbox.y())
        self.atkw_spin.setValue(atk_hitbox.width())
        self.atkh_spin.setValue(atk_hitbox.height())

        self.hold_check.blockSignals(True)
        self.hold_check.setChecked(has_hold)
        self.hold_check.blockSignals(False)
        self.hold_x_spin.setValue(hold_x)
        self.hold_y_spin.setValue(hold_y)
        self._update_hold_anchor_visibility()
        
        self.attack_frame_check.blockSignals(True)
        self.attack_frame_check.setChecked(is_attack)
        self.attack_frame_check.blockSignals(False)
        self._update_attack_hitbox_visibility()
        self.canvas.attack_range = self.controller.manager.attack_range if is_combat_entity else 0
        
        self.canvas.update_data(
            pixmap,
            anchor,
            hitbox,
            atk_hitbox if is_combat_entity else QRect(),
            QPoint(hold_x, hold_y) if is_living else None,
            has_hold if is_living else False,
            is_attack_frame=is_attack if is_combat_entity else False
        )
        self._is_loading = False

    def _on_canvas_dragged(
        self,
        anchor: QPoint,
        hitbox: QRect,
        atk_hitbox: QRect,
        hold_anchor: QPoint,
        has_hold_point: bool
    ) -> None:
        self._is_loading = True
        self.ax_spin.setValue(anchor.x())
        self.ay_spin.setValue(anchor.y())
        
        self.hx_spin.setValue(hitbox.x())
        self.hy_spin.setValue(hitbox.y())
        
        self.atkx_spin.setValue(atk_hitbox.x())
        self.atky_spin.setValue(atk_hitbox.y())

        self.hold_check.setChecked(has_hold_point)
        self.hold_x_spin.setValue(hold_anchor.x())
        self.hold_y_spin.setValue(hold_anchor.y())
        self._update_hold_anchor_visibility()
        self._is_loading = False
        
        self._save_to_override()

    def _on_spinbox_changed(self) -> None:
        if self._is_loading: return
        
        anchor = QPoint(self.ax_spin.value(), self.ay_spin.value())
        hitbox = QRect(
            self.hx_spin.value(), self.hy_spin.value(),
            self.hw_spin.value(), self.hh_spin.value()
        )
        is_structure: bool = self.controller.manager.entity_type == EntityType.STRUCTURE.value
        is_living: bool = self.controller.manager.entity_type == EntityType.ENTITY
        atk_hitbox = QRect(0, 0, 0, 0) if is_structure else QRect(
            self.atkx_spin.value(), self.atky_spin.value(),
            self.atkw_spin.value(), self.atkh_spin.value()
        )
        has_hold: bool = self.hold_check.isChecked() if is_living else False
        hold_anchor = QPoint(self.hold_x_spin.value(), self.hold_y_spin.value()) if is_living else QPoint(0, 0)
        is_attack: bool = self.attack_frame_check.isChecked() and not is_structure

        self.canvas.update_data(
            self.canvas.frame_pixmap,
            anchor,
            hitbox,
            atk_hitbox,
            hold_anchor,
            has_hold,
            is_attack_frame=is_attack
        )
        self._save_to_override()
        self._update_hold_anchor_visibility()
        self._update_attack_hitbox_visibility()

    def _save_to_override(self) -> None:
        is_living: bool = self.controller.manager.entity_type == EntityType.ENTITY
        if self.controller.manager.is_static:
            ax: int = self.ax_spin.value()
            ay: int = self.ay_spin.value()
            hx: int = self.hx_spin.value()
            hy: int = self.hy_spin.value()
            hw: int = self.hw_spin.value()
            hh: int = self.hh_spin.value()
            has_hold: bool = self.hold_check.isChecked() if is_living else False
            hold_x: int = self.hold_x_spin.value()
            hold_y: int = self.hold_y_spin.value()
            for static_meta in self.controller.manager.animations.values():
                static_meta.anchor_x = ax
                static_meta.anchor_y = ay
                static_meta.hitbox_x = hx
                static_meta.hitbox_y = hy
                static_meta.hitbox_w = hw
                static_meta.hitbox_h = hh
                static_meta.has_hold_point = has_hold
                static_meta.hold_x = hold_x
                static_meta.hold_y = hold_y
                static_meta.frame_overrides.clear()
            self.controller.manager._static_physics_cache = None
            return

        state: Optional[str] = self.state_combo.currentData()
        if not state: return
        
        meta: Optional[AnimationMeta] = self.controller.manager.animations.get(state)
        if meta is None: return
        
        tick_index: int = self.frame_spin.value()
        total_play_frames: int = max(1, (meta.end_frame - meta.start_frame) + 1)
        
        mapped_index: int = (
            tick_index % total_play_frames
            if meta.loop else
            min(tick_index, total_play_frames - 1)
        )
        if meta.reverse:
            mapped_index = (total_play_frames - 1) - mapped_index
            
        frame_key: str = str(mapped_index)

        override_dict: dict[str, Any] = {
            "anchor_x": self.ax_spin.value(),
            "anchor_y": self.ay_spin.value(),
            "hitbox_x": self.hx_spin.value(),
            "hitbox_y": self.hy_spin.value(),
            "hitbox_w": self.hw_spin.value(),
            "hitbox_h": self.hh_spin.value(),
            "is_attack_frame": self.attack_frame_check.isChecked(),
            "attack_x": self.atkx_spin.value(),
            "attack_y": self.atky_spin.value(),
            "attack_w": self.atkw_spin.value(),
            "attack_h": self.atkh_spin.value(),
        }
        if is_living:
            override_dict["has_hold_point"] = self.hold_check.isChecked()
            override_dict["hold_x"] = self.hold_x_spin.value()
            override_dict["hold_y"] = self.hold_y_spin.value()

        meta.frame_overrides[frame_key] = override_dict

    def _apply_to_base(self) -> None:
        is_living: bool = self.controller.manager.entity_type == EntityType.ENTITY
        if self.controller.manager.is_static:
            ax: int = self.ax_spin.value()
            ay: int = self.ay_spin.value()
            hx: int = self.hx_spin.value()
            hy: int = self.hy_spin.value()
            hw: int = self.hw_spin.value()
            hh: int = self.hh_spin.value()
            has_hold: bool = self.hold_check.isChecked() if is_living else False
            hold_x: int = self.hold_x_spin.value()
            hold_y: int = self.hold_y_spin.value()
            for static_meta in self.controller.manager.animations.values():
                static_meta.anchor_x = ax
                static_meta.anchor_y = ay
                static_meta.hitbox_x = hx
                static_meta.hitbox_y = hy
                static_meta.hitbox_w = hw
                static_meta.hitbox_h = hh
                static_meta.has_hold_point = has_hold
                static_meta.hold_x = hold_x
                static_meta.hold_y = hold_y
                static_meta.frame_overrides.clear()
            self.controller.manager._static_physics_cache = None
            self.load_data()
            return

        state: Optional[str] = self.state_combo.currentData()
        if not state: return
        
        meta: Optional[AnimationMeta] = self.controller.manager.animations.get(state)
        if meta is None: return
        
        meta.anchor_x = self.ax_spin.value()
        meta.anchor_y = self.ay_spin.value()
        meta.hitbox_x = self.hx_spin.value()
        meta.hitbox_y = self.hy_spin.value()
        meta.hitbox_w = self.hw_spin.value()
        meta.hitbox_h = self.hh_spin.value()
        if is_living:
            meta.has_hold_point = self.hold_check.isChecked()
            meta.hold_x = self.hold_x_spin.value()
            meta.hold_y = self.hold_y_spin.value()
        meta.frame_overrides.clear()

        self.load_data()
    
    def _on_copy(self) -> None:
        self._copied_physics = {
            "ax": self.ax_spin.value(),
            "ay": self.ay_spin.value(),
            "hx": self.hx_spin.value(),
            "hy": self.hy_spin.value(),
            "hw": self.hw_spin.value(),
            "hh": self.hh_spin.value(),
            "atk_frame": self.attack_frame_check.isChecked(),
            "atk_x": self.atkx_spin.value(),
            "atk_y": self.atky_spin.value(),
            "atk_w": self.atkw_spin.value(),
            "atk_h": self.atkh_spin.value(),
            "has_hold": self.hold_check.isChecked(),
            "hold_x": self.hold_x_spin.value(),
            "hold_y": self.hold_y_spin.value(),
        }
        self.paste_btn.setEnabled(True)

    def _on_paste(self) -> None:
        if not self._copied_physics: return
        self.ax_spin.setValue(self._copied_physics["ax"])
        self.ay_spin.setValue(self._copied_physics["ay"])
        self.hx_spin.setValue(self._copied_physics["hx"])
        self.hy_spin.setValue(self._copied_physics["hy"])
        self.hw_spin.setValue(self._copied_physics["hw"])
        self.hh_spin.setValue(self._copied_physics["hh"])
        self.attack_frame_check.setChecked(self._copied_physics["atk_frame"])
        self.atkx_spin.setValue(self._copied_physics["atk_x"])
        self.atky_spin.setValue(self._copied_physics["atk_y"])
        self.atkw_spin.setValue(self._copied_physics["atk_w"])
        self.atkh_spin.setValue(self._copied_physics["atk_h"])
        if "has_hold" in self._copied_physics:
            self.hold_check.setChecked(self._copied_physics["has_hold"])
            self.hold_x_spin.setValue(self._copied_physics["hold_x"])
            self.hold_y_spin.setValue(self._copied_physics["hold_y"])
        self._update_hold_anchor_visibility()
        self._update_attack_hitbox_visibility()
    
    def _on_magic_propagate(self) -> None:
        state: Optional[str] = self.state_combo.currentData()
        if not state: return
        
        meta: Optional[AnimationMeta] = self.controller.manager.animations.get(state)
        if not meta: return
        
        target_hw: int = self.hw_spin.value()
        target_hh: int = self.hh_spin.value()
        
        def calc_pos(ax: int, ay: int) -> tuple[int, int]:
            return ax - (target_hw // 2), ay - target_hh

        meta.hitbox_w = target_hw
        meta.hitbox_h = target_hh
        meta.hitbox_x, meta.hitbox_y = calc_pos(meta.anchor_x, meta.anchor_y)
        
        for _, override in meta.frame_overrides.items():
            ax: int = override.get("anchor_x", meta.anchor_x)
            ay: int = override.get("anchor_y", meta.anchor_y)
            hx, hy = calc_pos(ax, ay)
            
            override["hitbox_w"] = target_hw
            override["hitbox_h"] = target_hh
            override["hitbox_x"] = hx
            override["hitbox_y"] = hy
            
        self.load_data()
        
        QMessageBox.information(
            self, "Magic Propagate",
            f"Hitbox ({target_hw}x{target_hh}) propagated to all frames!\n\n"
            "Each hitbox is now bottom-centered on its frame anchor."
        )
    
    def _on_show_range_toggled(self, state: int) -> None:
        self.canvas.show_attack_range = bool(state)
        self.canvas.update()

    def _toggle_canvas_expand(self) -> None:
        if self.canvas.height() >= 460:
            self.canvas.setFixedHeight(340)
            self.expand_canvas_btn.setText("⤢ Expand")
        else:
            self.canvas.setFixedHeight(520)
            self.expand_canvas_btn.setText("⤡ Compact")

    def _on_canvas_height_changed(self, height: int) -> None:
        if height >= 460:
            self.expand_canvas_btn.setText("⤡ Compact")
        else:
            self.expand_canvas_btn.setText("⤢ Expand")

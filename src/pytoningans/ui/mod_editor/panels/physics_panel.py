from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QSpinBox, QLabel,
    QPushButton, QMessageBox, QCheckBox, QSpacerItem
)
from PySide6.QtGui import (
    QPaintEvent, QPainter, QColor, QMouseEvent, QPixmap, QPen
)
from PySide6.QtCore import Qt, QPoint, QRect, Signal, QPointF

from pytoningans.core.constants import AnimationMeta, EntityType, StructureState, EntityState
from pytoningans.ui.mod_editor.components import CollapsibleSection, create_info_label
from .base_panel import BasePanel

if TYPE_CHECKING:
    from pytoningans.ui.mod_editor.controller import ModEditorController

class PhysicsCanvas(QWidget):
    physics_changed = Signal(QPoint, QRect, QRect)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(300, 300)
        self.setMouseTracking(True)
        self.zoom: int = 4
        
        self.frame_pixmap: QPixmap = QPixmap()
        self.anchor: QPoint = QPoint(0, 0)
        self.hitbox: QRect = QRect(0, 0, 0, 0)
        self.atk_hitbox: QRect = QRect(0, 0, 0, 0)
        
        self._dragging_anchor: bool = False
        self._dragging_hitbox: bool = False
        self._dragging_attack: bool = False
        self._drag_offset: QPoint = QPoint()
        
        self.attack_range: int = 0
        self.show_attack_range: bool = False

    def update_data(
        self, pixmap: QPixmap, anchor: QPoint,
        hitbox: QRect, atk_hitbox: QRect
    ) -> None:
        self.frame_pixmap = pixmap
        self.anchor = anchor
        self.hitbox = hitbox
        self.atk_hitbox = atk_hitbox
        self.setMinimumSize(
            max(300, self.frame_pixmap.width() * self.zoom),
            max(300, self.frame_pixmap.height() * self.zoom)
        )
        self.update()
    
    def paintEvent(self, _: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().base().color())
        
        painter.setPen(self.palette().shadow().color())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        
        if self.frame_pixmap.isNull():
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Frame Loaded")
            return

        scaled_w: int = self.frame_pixmap.width() * self.zoom
        scaled_h: int = self.frame_pixmap.height() * self.zoom
        painter.drawPixmap(0, 0, scaled_w, scaled_h, self.frame_pixmap)

        # Hitbox (Red)
        scaled_hitbox = QRect(
            self.hitbox.x() * self.zoom, self.hitbox.y() * self.zoom,
            self.hitbox.width() * self.zoom, self.hitbox.height() * self.zoom
        )
        painter.setPen(Qt.GlobalColor.red)
        painter.setBrush(QColor(255, 0, 0, 60))
        painter.drawRect(scaled_hitbox)
        
        # Attack Hitbox (Orange) - only when enabled
        if not self.atk_hitbox.isNull() and self.atk_hitbox.width() > 0:
            scaled_attack = QRect(
                self.atk_hitbox.x() * self.zoom, self.atk_hitbox.y() * self.zoom,
                self.atk_hitbox.width() * self.zoom, self.atk_hitbox.height() * self.zoom
            )
            painter.setPen(QColor("#ffa500"))
            painter.setBrush(QColor(255, 165, 0, 80))
            painter.drawRect(scaled_attack)

        # Anchor (Cyan Crosshair)
        ax: int = self.anchor.x() * self.zoom
        ay: int = self.anchor.y() * self.zoom
        painter.setPen(Qt.GlobalColor.cyan)
        painter.drawLine(ax - 10, ay, ax + 10, ay)
        painter.drawLine(ax, ay - 10, ax, ay + 10)
        
        # Aggro Range
        if self.show_attack_range and self.attack_range > 0 and not self.hitbox.isEmpty():
            center_x: float = (self.hitbox.x() + self.hitbox.width() / 2.0) * self.zoom
            center_y: float = (self.hitbox.y() + self.hitbox.height() / 2.0) * self.zoom
            scaled_radius: int = self.attack_range * self.zoom
            
            pen = QPen(QColor(255, 50, 50, 180), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(center_x, center_y), scaled_radius, scaled_radius)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.frame_pixmap.isNull(): return
        
        click_x: int = event.pos().x() // self.zoom
        click_y: int = event.pos().y() // self.zoom
        click_pos = QPoint(click_x, click_y)

        if (abs(click_x - self.anchor.x()) <= 2 and abs(click_y - self.anchor.y()) <= 2):
            self._dragging_anchor = True
        elif self.atk_hitbox.contains(click_pos):
            self._dragging_attack = True
            self._drag_offset = click_pos - self.atk_hitbox.topLeft()
        elif self.hitbox.contains(click_pos):
            self._dragging_hitbox = True
            self._drag_offset = click_pos - self.hitbox.topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (self._dragging_anchor or self._dragging_hitbox or self._dragging_attack): return
        
        new_x: int = max(0, min(event.pos().x() // self.zoom, self.frame_pixmap.width()))
        new_y: int = max(0, min(event.pos().y() // self.zoom, self.frame_pixmap.height()))

        if self._dragging_anchor:
            self.anchor = QPoint(new_x, new_y)
        elif self._dragging_attack:
            self.atk_hitbox.moveTo(new_x - self._drag_offset.x(), new_y - self._drag_offset.y())
        elif self._dragging_hitbox:
            self.hitbox.moveTo(new_x - self._drag_offset.x(), new_y - self._drag_offset.y())
            
        self.physics_changed.emit(self.anchor, self.hitbox, self.atk_hitbox)
        self.update()

    def mouseReleaseEvent(self, _: QMouseEvent) -> None:
        self._dragging_anchor = False
        self._dragging_hitbox = False
        self._dragging_attack = False
    
    def set_zoom(self, zoom: int) -> None:
        self.zoom = zoom
        if not self.frame_pixmap.isNull():
            self.setMinimumSize(
                max(300, self.frame_pixmap.width() * self.zoom),
                max(300, self.frame_pixmap.height() * self.zoom)
            )
        self.update()


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
        
        # Top Controls
        top_layout = QHBoxLayout()
        self.state_combo = QComboBox()
            
        self.frame_spin = QSpinBox()
        self.frame_spin.setPrefix("Frame: ")
        self.frame_spin.setMinimum(0)
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setPrefix("Zoom: ")
        self.zoom_spin.setSuffix("x")
        self.zoom_spin.setRange(1, 20)
        
        self.copy_btn = QPushButton("Copy")
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setEnabled(False)
        
        top_layout.addWidget(QLabel("State:"))
        top_layout.addWidget(self.state_combo)
        top_layout.addWidget(self.frame_spin)
        top_layout.addWidget(self.copy_btn)
        top_layout.addWidget(self.paste_btn)
        top_layout.addWidget(self.zoom_spin)
        top_layout.addStretch()

        # Canvas and Form Controls
        editor_layout = QHBoxLayout()
        self.canvas = PhysicsCanvas()
        editor_layout.addWidget(self.canvas, stretch=1)
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
        
        self.apply_base_btn = QPushButton("Apply to Entire Animation")
        self.form.addRow(self.apply_base_btn)
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
        
        section.content_layout.addLayout(top_layout)
        section.content_layout.addLayout(editor_layout)
        layout.addWidget(section)

    def _connect_signals(self) -> None:
        self.state_combo.currentIndexChanged.connect(self._on_state_combo_changed)
        self.frame_spin.valueChanged.connect(self.load_data)
        self.zoom_spin.valueChanged.connect(self.canvas.set_zoom)
        
        self.copy_btn.clicked.connect(self._on_copy)
        self.paste_btn.clicked.connect(self._on_paste)
        
        self.canvas.physics_changed.connect(self._on_canvas_dragged)
        self.apply_base_btn.clicked.connect(self._apply_to_base)
        self.attack_frame_check.stateChanged.connect(self._on_spinbox_changed)
        self.show_range_check.stateChanged.connect(self._on_show_range_toggled)
        self.magic_btn.clicked.connect(self._on_magic_propagate)
        
        for spin in [
            self.ax_spin, self.ay_spin, self.hx_spin, self.hy_spin,
            self.hw_spin, self.hh_spin, self.atkx_spin, self.atky_spin,
            self.atkw_spin, self.atkh_spin
        ]:
            spin.valueChanged.connect(self._on_spinbox_changed)

    def _sync_states_dropdown(self) -> None:
        """Populates the combo box from the active animations dictionary keys."""
        prev_data = self.state_combo.currentData()
        current_selection: Optional[str] = str(prev_data) if prev_data else None
        
        self.state_combo.blockSignals(True)
        self.state_combo.clear()
        
        is_structure: bool = self.controller.manager.entity_type == EntityType.STRUCTURE.value
        state_enum = StructureState if is_structure else EntityState
        
        target_idx: int = 0
        for i, state in enumerate(state_enum):
            state_val: str = str(state.value)
            self.state_combo.addItem(state_val.capitalize(), userData=state_val)
            if current_selection and state_val == current_selection:
                target_idx = i
                
        if self.state_combo.count() > 0:
            self.state_combo.setCurrentIndex(target_idx)
            
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
            
        is_structure: bool = self.controller.manager.entity_type == EntityType.STRUCTURE.value
        
        # Toggle combat inputs according to entity type
        combat_visible = not is_structure
        self.attack_frame_check.setVisible(combat_visible)
        self.show_range_check.setVisible(combat_visible)
        self.attack_header.setVisible(combat_visible)
        self.atk_lbl_x.setVisible(combat_visible); self.atkx_spin.setVisible(combat_visible)
        self.atk_lbl_y.setVisible(combat_visible); self.atky_spin.setVisible(combat_visible)
        self.atk_lbl_w.setVisible(combat_visible); self.atkw_spin.setVisible(combat_visible)
        self.atk_lbl_h.setVisible(combat_visible); self.atkh_spin.setVisible(combat_visible)

        frame_idx: int = self.frame_spin.value()
        is_attack: bool = False
        atk_hitbox: QRect = QRect(0, 0, 0, 0)
        
        meta: Optional[AnimationMeta] = self.controller.manager.animations.get(state)
        if meta is not None:
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
        
        self.attack_frame_check.blockSignals(True)
        self.attack_frame_check.setChecked(is_attack)
        self.attack_frame_check.blockSignals(False)
        self.canvas.attack_range = 0 if is_structure else self.controller.manager.attack_range
        
        self.canvas.update_data(pixmap, anchor, hitbox, QRect() if is_structure else atk_hitbox)
        self._is_loading = False

    def _on_canvas_dragged(
        self, anchor: QPoint, hitbox: QRect, atk_hitbox: QRect
    ) -> None:
        self._is_loading = True
        self.ax_spin.setValue(anchor.x())
        self.ay_spin.setValue(anchor.y())
        
        self.hx_spin.setValue(hitbox.x())
        self.hy_spin.setValue(hitbox.y())
        
        self.atkx_spin.setValue(atk_hitbox.x())
        self.atky_spin.setValue(atk_hitbox.y())
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
        atk_hitbox = QRect(0, 0, 0, 0) if is_structure else QRect(
            self.atkx_spin.value(), self.atky_spin.value(),
            self.atkw_spin.value(), self.atkh_spin.value()
        )
        self.canvas.update_data(self.canvas.frame_pixmap, anchor, hitbox, atk_hitbox)
        self._save_to_override()

    def _save_to_override(self) -> None:
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

        meta.frame_overrides[frame_key] = {
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
            "attack_h": self.atkh_spin.value()
        }

    def _apply_to_base(self) -> None:
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
            "atk_h": self.atkh_spin.value()
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
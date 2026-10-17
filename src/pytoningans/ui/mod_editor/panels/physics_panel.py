from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QSpinBox, QLabel,
    QPushButton, QMessageBox, QCheckBox, QSpacerItem
)
from PySide6.QtGui import (
    QPaintEvent, QPainter, QColor, QMouseEvent, QPixmap, QPen, QWheelEvent
)
from PySide6.QtCore import Qt, QPoint, QRect, Signal, QPointF

from pytoningans.core.constants import (
    AnimationMeta, EntityType, StructureState, EntityState, ItemState
)
from pytoningans.ui.mod_editor.components import CollapsibleSection, create_info_label
from .base_panel import BasePanel

if TYPE_CHECKING:
    from pytoningans.ui.mod_editor.controller import ModEditorController

# TODO: Refactor; make it modular
class PhysicsCanvas(QWidget):
    physics_changed = Signal(QPoint, QRect, QRect, QPoint, bool)
    zoom_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)
        self.zoom: int = 4
        self.pan_offset: QPoint = QPoint(0, 0)
        self._is_panning: bool = False
        self._pan_start: QPoint = QPoint()
        self._first_load: bool = True

        self.frame_pixmap: QPixmap = QPixmap()
        self.anchor: QPoint = QPoint(0, 0)
        self.atk_hitbox: QRect = QRect(0, 0, 0, 0)
        self.is_attack_frame: bool = False
        self.hold_anchor: QPoint = QPoint(0, 0)
        self.has_hold_point: bool = False

        self._dragging_anchor: bool = False
        self._dragging_hitbox: bool = False
        self._dragging_attack: bool = False
        self._dragging_hold: bool = False
        self._drag_offset: QPoint = QPoint()

        self.attack_range: int = 0
        self.show_attack_range: bool = False

    def update_data(
        self, pixmap: QPixmap, anchor: QPoint,
        hitbox: QRect, atk_hitbox: QRect,
        hold_anchor: Optional[QPoint] = None,
        has_hold_point: bool = False,
        is_attack_frame: bool = False
    ) -> None:
        was_null: bool = self.frame_pixmap.isNull()
        self.frame_pixmap = pixmap
        self.anchor = anchor
        self.hitbox = hitbox
        self.atk_hitbox = atk_hitbox
        self.is_attack_frame = is_attack_frame
        self.hold_anchor = hold_anchor if hold_anchor is not None else QPoint(0, 0)
        self.has_hold_point = has_hold_point

        if (was_null or self._first_load) and not self.frame_pixmap.isNull():
            self._first_load = False
            self.reset_view()
        self.update()

    def reset_view(self) -> None:
        """Centers the frame pixmap in the canvas viewport."""
        if not self.frame_pixmap.isNull():
            sw: int = self.frame_pixmap.width() * self.zoom
            sh: int = self.frame_pixmap.height() * self.zoom
            self.pan_offset = QPoint((self.width() - sw) // 2, (self.height() - sh) // 2)
        else:
            self.pan_offset = QPoint(0, 0)
        self.update()

    def _to_screen(self, pt: QPoint) -> QPoint:
        return QPoint(
            pt.x() * self.zoom + self.pan_offset.x(),
            pt.y() * self.zoom + self.pan_offset.y()
        )

    def _to_screen_rect(self, rect: QRect) -> QRect:
        return QRect(
            rect.x() * self.zoom + self.pan_offset.x(),
            rect.y() * self.zoom + self.pan_offset.y(),
            rect.width() * self.zoom,
            rect.height() * self.zoom
        )

    def _to_frame(self, screen_pt: QPoint) -> QPoint:
        return QPoint(
            int((screen_pt.x() - self.pan_offset.x()) / self.zoom),
            int((screen_pt.y() - self.pan_offset.y()) / self.zoom)
        )

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

        painter.setClipRect(self.rect())

        pan_x: int = self.pan_offset.x()
        pan_y: int = self.pan_offset.y()
        scaled_w: int = self.frame_pixmap.width() * self.zoom
        scaled_h: int = self.frame_pixmap.height() * self.zoom

        # Draw frame pixmap
        painter.drawPixmap(pan_x, pan_y, scaled_w, scaled_h, self.frame_pixmap)

        # Subtle frame cell outline
        painter.setPen(QPen(QColor(120, 120, 120, 120), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(pan_x, pan_y, scaled_w - 1, scaled_h - 1)

        # Hitbox (Red)
        scaled_hitbox = self._to_screen_rect(self.hitbox)
        painter.setPen(Qt.GlobalColor.red)
        painter.setBrush(QColor(255, 0, 0, 60))
        painter.drawRect(scaled_hitbox)

        # Attack Hitbox (Orange) - only when configured and marked as attack frame
        if self.is_attack_frame and not self.atk_hitbox.isNull() and self.atk_hitbox.width() > 0:
            scaled_attack = self._to_screen_rect(self.atk_hitbox)
            painter.setPen(QColor("#ffa500"))
            painter.setBrush(QColor(255, 165, 0, 80))
            painter.drawRect(scaled_attack)

        # Primary Anchor (Cyan Crosshair)
        anchor_s: QPoint = self._to_screen(self.anchor)
        ax: int = anchor_s.x()
        ay: int = anchor_s.y()
        painter.setPen(QPen(Qt.GlobalColor.cyan, 2))
        painter.drawLine(ax - 10, ay, ax + 10, ay)
        painter.drawLine(ax, ay - 10, ax, ay + 10)

        # Item Hold Anchor (Gold Crosshair)
        if self.has_hold_point:
            hold_s: QPoint = self._to_screen(self.hold_anchor)
            hx: int = hold_s.x()
            hy: int = hold_s.y()
            painter.setPen(QPen(QColor("#fbbf24"), 2))
            painter.drawLine(hx - 8, hy, hx + 8, hy)
            painter.drawLine(hx, hy - 8, hx, hy + 8)
            painter.setBrush(QColor(251, 191, 36, 120))
            painter.drawRect(hx - 3, hy - 3, 6, 6)
            painter.setPen(QColor("#fbbf24"))
            painter.setFont(self.font())
            painter.drawText(hx + 7, hy - 5, "Hold")

        # Aggro Range Circle
        if self.show_attack_range and self.attack_range > 0 and not self.hitbox.isEmpty():
            center_x: float = (self.hitbox.x() + self.hitbox.width() / 2.0) * self.zoom + pan_x
            center_y: float = (self.hitbox.y() + self.hitbox.height() / 2.0) * self.zoom + pan_y
            scaled_radius: int = self.attack_range * self.zoom

            pen = QPen(QColor(255, 50, 50, 180), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(center_x, center_y), scaled_radius, scaled_radius)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.frame_pixmap.isNull(): return

        # Middle or Right mouse button drag pans the viewport
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            click_pos: QPoint = self._to_frame(event.pos())
            click_x: int = click_pos.x()
            click_y: int = click_pos.y()

            # Priority 1: Hold anchor drag
            if self.has_hold_point and (
                abs(click_x - self.hold_anchor.x()) <= 4 and
                abs(click_y - self.hold_anchor.y()) <= 4
            ):
                self._dragging_hold = True
            # Priority 2: Standard anchor drag
            elif abs(click_x - self.anchor.x()) <= 4 and abs(click_y - self.anchor.y()) <= 4:
                self._dragging_anchor = True
            # Priority 3: Attack hitbox drag (only if attack frame)
            elif self.is_attack_frame and self.atk_hitbox.contains(click_pos):
                self._dragging_attack = True
                self._drag_offset = click_pos - self.atk_hitbox.topLeft()
            # Priority 4: Hitbox drag
            elif self.hitbox.contains(click_pos):
                self._dragging_hitbox = True
                self._drag_offset = click_pos - self.hitbox.topLeft()
            elif event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
                self._is_panning = True
                self._pan_start = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_panning:
            delta: QPoint = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.pan_offset += delta
            self.update()
            return

        if not (self._dragging_anchor or self._dragging_hitbox or self._dragging_attack or self._dragging_hold):
            return

        frame_pos: QPoint = self._to_frame(event.pos())
        new_x: int = frame_pos.x()
        new_y: int = frame_pos.y()

        if self._dragging_hold:
            self.hold_anchor = QPoint(new_x, new_y)
        elif self._dragging_anchor:
            self.anchor = QPoint(
                max(0, min(new_x, self.frame_pixmap.width())),
                max(0, min(new_y, self.frame_pixmap.height()))
            )
        elif self._dragging_attack:
            self.atk_hitbox.moveTo(new_x - self._drag_offset.x(), new_y - self._drag_offset.y())
        elif self._dragging_hitbox:
            self.hitbox.moveTo(new_x - self._drag_offset.x(), new_y - self._drag_offset.y())

        self.physics_changed.emit(self.anchor, self.hitbox, self.atk_hitbox, self.hold_anchor, self.has_hold_point)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton) or self._is_panning:
            self._is_panning = False
            self.unsetCursor()
        self._dragging_anchor = False
        self._dragging_hitbox = False
        self._dragging_attack = False
        self._dragging_hold = False

    def wheelEvent(self, event: QWheelEvent) -> None:
        angle: int = event.angleDelta().y()
        if angle == 0: return
        old_zoom: int = self.zoom
        delta: int = 1 if angle > 0 else -1
        new_zoom: int = max(1, min(20, self.zoom + delta))
        if new_zoom != old_zoom:
            cursor_pos: QPoint = event.position().toPoint()
            fx: float = (cursor_pos.x() - self.pan_offset.x()) / float(old_zoom)
            fy: float = (cursor_pos.y() - self.pan_offset.y()) / float(old_zoom)
            self.zoom = new_zoom
            self.pan_offset = QPoint(
                int(cursor_pos.x() - fx * new_zoom),
                int(cursor_pos.y() - fy * new_zoom)
            )
            self.zoom_changed.emit(self.zoom)
            self.update()

    def set_zoom(self, zoom: int) -> None:
        if self.zoom == zoom: return
        old_zoom: int = self.zoom
        center_x: float = self.width() / 2.0
        center_y: float = self.height() / 2.0
        fx: float = (center_x - self.pan_offset.x()) / float(old_zoom)
        fy: float = (center_y - self.pan_offset.y()) / float(old_zoom)
        self.zoom = zoom
        self.pan_offset = QPoint(
            int(center_x - fx * self.zoom),
            int(center_y - fy * self.zoom)
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
        self.state_label = QLabel("State:")
        self.state_combo = QComboBox()
            
        self.frame_spin = QSpinBox()
        self.frame_spin.setPrefix("Frame: "); self.frame_spin.setMinimum(0)
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setPrefix("Zoom: "); self.zoom_spin.setSuffix("x")
        self.zoom_spin.setRange(1, 20)
        
        self.copy_btn = QPushButton("Copy")
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setEnabled(False)
        
        self.static_indicator = QLabel("Static Collision (Shared across all states)")
        self.static_indicator.setStyleSheet("color: #60a5fa; font-weight: bold; font-size: 11px;")
        self.static_indicator.hide()

        self.reset_view_btn = QPushButton("Reset View")

        top_layout.addWidget(self.state_label)
        top_layout.addWidget(self.state_combo)
        top_layout.addWidget(self.frame_spin)
        top_layout.addWidget(self.copy_btn)
        top_layout.addWidget(self.paste_btn)
        top_layout.addWidget(self.static_indicator)
        top_layout.addWidget(self.zoom_spin)
        top_layout.addWidget(self.reset_view_btn)
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
        
        section.content_layout.addLayout(top_layout)
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
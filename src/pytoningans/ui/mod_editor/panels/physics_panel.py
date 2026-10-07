from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QSpinBox, QLabel,
    QPushButton, QMessageBox, QCheckBox, QSpacerItem
)
from PySide6.QtGui import (
    QPaintEvent, QPainter, QColor, QMouseEvent, QPixmap, QPen
)
from PySide6.QtCore import Qt, QPoint, QRect, Signal

from pytoningans.core.constants import AnimationMeta, EntityState
from pytoningans.ui.mod_editor.components import CollapsibleSection, create_info_label

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
        
        # Fill Background
        painter.fillRect(self.rect(), self.palette().base().color())
        
        # Draw border around the canvas bounds
        painter.setPen(self.palette().shadow().color())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Subtract 1 from width/height so the border renders entirely inside the widget
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        
        if self.frame_pixmap.isNull():
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Frame Loaded")
            return

        # Draw scaled sprite
        scaled_w: int = self.frame_pixmap.width() * self.zoom
        scaled_h: int = self.frame_pixmap.height() * self.zoom
        painter.drawPixmap(0, 0, scaled_w, scaled_h, self.frame_pixmap)

        # Draw Hitbox (Red)
        scaled_hitbox = QRect(
            self.hitbox.x() * self.zoom, self.hitbox.y() * self.zoom,
            self.hitbox.width() * self.zoom, self.hitbox.height() * self.zoom
        )
        painter.setPen(Qt.GlobalColor.red)
        painter.setBrush(QColor(255, 0, 0, 60))
        painter.drawRect(scaled_hitbox)
        
        # Draw Attack Hitbox (Orange)
        if not self.atk_hitbox.isNull() and self.atk_hitbox.width() > 0:
            scaled_attack = QRect(
                self.atk_hitbox.x() * self.zoom, self.atk_hitbox.y() * self.zoom,
                self.atk_hitbox.width() * self.zoom, self.atk_hitbox.height() * self.zoom
            )
            painter.setPen(QColor("#ffa500"))
            painter.setBrush(QColor(255, 165, 0, 80))
            painter.drawRect(scaled_attack)

        # Draw Anchor (Blue Crosshair)
        ax: int = self.anchor.x() * self.zoom
        ay: int = self.anchor.y() * self.zoom
        painter.setPen(Qt.GlobalColor.cyan)
        painter.drawLine(ax - 10, ay, ax + 10, ay)
        painter.drawLine(ax, ay - 10, ax, ay + 10)
        
        # Draw Aggro Range (Dashed Red Circle)
        if self.show_attack_range and self.attack_range > 0 and not self.hitbox.isEmpty():
            # The AI measures distance from the center of the physical hitbox
            center_x: float = (self.hitbox.x() + self.hitbox.width() / 2.0) * self.zoom
            center_y: float = (self.hitbox.y() + self.hitbox.height() / 2.0) * self.zoom
            scaled_radius: int = self.attack_range * self.zoom
            
            pen = QPen(QColor(255, 50, 50, 180), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            from PySide6.QtCore import QPointF
            painter.drawEllipse(QPointF(center_x, center_y), scaled_radius, scaled_radius)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.frame_pixmap.isNull(): return
        
        # Convert screen click to pixel-art coordinates
        click_x: int = event.pos().x() // self.zoom
        click_y: int = event.pos().y() // self.zoom
        click_pos = QPoint(click_x, click_y)

        # Check if clicking near the anchor
        if (abs(click_x - self.anchor.x()) <= 2 and abs(click_y - self.anchor.y()) <= 2):
            self._dragging_anchor = True
            
        # Prioritize dragging attack box if overlapping
        elif self.atk_hitbox.contains(click_pos):
            self._dragging_attack = True
            self._drag_offset = click_pos - self.atk_hitbox.topLeft()
            
        # Check if clicking inside the hitbox
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


class PhysicsPanel(QWidget):
    def __init__(self, controller: ModEditorController) -> None:
        super().__init__()
        self.controller: ModEditorController = controller
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
        for state in EntityState:
            self.state_combo.addItem(state.value.capitalize(), userData=state)
            
        self.frame_spin = QSpinBox(); self.frame_spin.setPrefix("Frame: ")
        self.frame_spin.setMinimum(0)
        self.zoom_spin = QSpinBox();
        self.zoom_spin.setPrefix("Zoom: "); self.zoom_spin.setSuffix("x")
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

        # Canvas and Spinboxes
        editor_layout = QHBoxLayout()
        self.canvas = PhysicsCanvas()
        editor_layout.addWidget(self.canvas, stretch=1)
        self.zoom_spin.setValue(self.canvas.zoom)
        
        form_flags: Qt.AlignmentFlag = (
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignRight
        )
        form = QFormLayout(labelAlignment=form_flags, horizontalSpacing=8)
        self.ax_spin = QSpinBox(); self.ax_spin.setRange(0, 999)
        self.ay_spin = QSpinBox(); self.ay_spin.setRange(0, 999)
        self.hx_spin = QSpinBox(); self.hx_spin.setRange(-999, 999)
        self.hy_spin = QSpinBox(); self.hy_spin.setRange(-999, 999)
        self.hw_spin = QSpinBox(); self.hw_spin.setRange(1, 999)
        self.hh_spin = QSpinBox(); self.hh_spin.setRange(1, 999)
        
        form.addRow(create_info_label("Anchor", "Animation anchor point."))
        form.addRow("X:", self.ax_spin)
        form.addRow("Y:", self.ay_spin)
        form.addItem(QSpacerItem(0, 16))
        
        form.addRow(create_info_label("Hitbox", "Used for collision detection."))
        form.addRow("X:", self.hx_spin)
        form.addRow("Y:", self.hy_spin)
        form.addRow("Width:", self.hw_spin)
        form.addRow("Height:", self.hh_spin)
        
        self.apply_base_btn = QPushButton("Apply to Entire Animation")
        form.addRow(self.apply_base_btn)
        form.addItem(QSpacerItem(0, 16))
        
        self.attack_frame_check = QCheckBox("Is Attack Frame")
        self.attack_frame_check.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.attack_frame_check.setToolTip("If checked, the pet will deal damage on this exact animation frame.")
        form.addRow(self.attack_frame_check)
        
        self.show_range_check = QCheckBox("Show Aggro Range (Red Circle)")
        form.addRow(self.show_range_check)
        
        self.atkx_spin = QSpinBox(); self.atkx_spin.setRange(-999, 999)
        self.atky_spin = QSpinBox(); self.atky_spin.setRange(-999, 999)
        self.atkw_spin = QSpinBox(); self.atkw_spin.setRange(0, 999)
        self.atkh_spin = QSpinBox(); self.atkh_spin.setRange(0, 999)
        
        form.addRow(create_info_label("Attack Hitbox", "Used for dealing damage via collision detection."))
        form.addRow("X:", self.atkx_spin)
        form.addRow("Y:", self.atky_spin)
        form.addRow("Width:", self.atkw_spin)
        form.addRow("Height:", self.atkh_spin)
        form.addItem(QSpacerItem(0, 16))
        
        self.magic_btn = QPushButton("Magic Propagate Hitbox")
        self.magic_btn.setStyleSheet(
            "color: #a855f7; font-weight: bold; font-family: 'Pixel Code', monospace;"
        )
        self.magic_btn.setToolTip(
            "Applies the current Hitbox's Width and Height to all frames, "
            "keeping them bottom-centered on each frame's Anchor."
        )
        form.addRow(self.magic_btn)

        editor_layout.addLayout(form)
        
        # Mount layouts inside the collapsible section
        section.content_layout.addLayout(top_layout)
        section.content_layout.addLayout(editor_layout)
        layout.addWidget(section)

    def _connect_signals(self) -> None:
        self.state_combo.currentIndexChanged.connect(self.load_data)
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

    def load_data(self) -> None:
        if not self.controller.manager.current_mod_folder: return
        self._is_loading = True
        
        state: EntityState = self.state_combo.currentData()
        frame_idx: int = self.frame_spin.value()
        is_attack: bool = False
        
        # Default attack values
        atk_hitbox: QRect = QRect(0, 0, 0, 0)
        
        # Bound the frame spinbox based on the animation meta
        meta: Optional[AnimationMeta] = self.controller.manager.animations.get(state)
        if meta is not None:
            total_frames: int = max(1, (meta.end_frame - meta.start_frame) + 1)
            self.frame_spin.setMaximum(total_frames - 1)
            self.frame_spin.setSuffix(f"/{total_frames - 1}")
            
            # Calculate the mapped index to look up the override dictionary
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
        self.canvas.attack_range = self.controller.manager.attack_range
        
        self.canvas.update_data(pixmap, anchor, hitbox, atk_hitbox)
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
        atk_hitbox = QRect(
            self.atkx_spin.value(), self.atky_spin.value(),
            self.atkw_spin.value(), self.atkh_spin.value()
        )
        self.canvas.update_data(self.canvas.frame_pixmap, anchor, hitbox, atk_hitbox)
        self._save_to_override()

    def _save_to_override(self) -> None:
        state: EntityState = self.state_combo.currentData()
        meta: Optional[AnimationMeta] = self.controller.manager.animations.get(state)
        
        if meta is None: return
        
        # Calculate the exact frame mapping exactly like the engine does
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

        # Save the physics data to the correctly mapped key
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
        """Saves current physics as the baseline for the entire animation state."""
        state: EntityState = self.state_combo.currentData()
        meta: Optional[AnimationMeta] = self.controller.manager.animations.get(state)
        if meta is None: return
        
        meta.anchor_x = self.ax_spin.value()
        meta.anchor_y = self.ay_spin.value()
        meta.hitbox_x = self.hx_spin.value()
        meta.hitbox_y = self.hy_spin.value()
        meta.hitbox_w = self.hw_spin.value()
        meta.hitbox_h = self.hh_spin.value()
        meta.frame_overrides.clear() # Clear overrides since base is updated
        self.load_data()
    
    def _on_copy(self) -> None:
        """Stores the current frame's physics values in memory."""
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
        """Applies the copied physics values to the current frame."""
        if not self._copied_physics: return
        
        # Setting these values automatically triggers _on_spinbox_changed,
        # which instantly updates the canvas and saves to the engine override.
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
        state: EntityState = self.state_combo.currentData()
        meta: Optional[AnimationMeta] = self.controller.manager.animations.get(state)
        if not meta: return
        
        target_hw: int = self.hw_spin.value()
        target_hh: int = self.hh_spin.value()
        
        def calc_pos(ax: int, ay: int) -> tuple[int, int]:
            return ax - (target_hw // 2), ay - target_hh

        # Update the base baseline physics
        meta.hitbox_w = target_hw
        meta.hitbox_h = target_hh
        meta.hitbox_x, meta.hitbox_y = calc_pos(meta.anchor_x, meta.anchor_y)
        
        # Update all custom frame overrides
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
            "Each hitbox is now perfectly bottom-centered on its frame's respective anchor."
        )
    
    def _on_show_range_toggled(self, state: int) -> None:
        self.canvas.show_attack_range = bool(state)
        self.canvas.update()
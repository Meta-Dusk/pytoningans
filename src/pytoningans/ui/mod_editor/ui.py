from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QSpinBox,
    QPushButton, QFormLayout, QFrame, QCheckBox, QScrollArea, QSizeGrip,
    QListWidget, QDialog, QLineEdit, QDoubleSpinBox, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPaintEvent, QPainter, QPen, QColor

from pytoningans.core.constants import PetState, BehaviorType
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.tool_tip import ToolTipLabel

class TriggerDialog(QDialog):
    """A custom popup form to gather all window trigger variables."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Window Trigger")
        layout = QFormLayout(self)
        
        self.text_input = QLineEdit()
        
        self.matches_input = QLineEdit()
        self.matches_input.setPlaceholderText("vscode, code.exe, visual studio")
        
        self.chance_spin = QDoubleSpinBox()
        self.chance_spin.setRange(0.01, 1.0)
        self.chance_spin.setSingleStep(0.1)
        self.chance_spin.setValue(0.5)
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(500, 20000)
        self.duration_spin.setValue(4000)
        
        layout.addRow("Spoken Text:", self.text_input)
        layout.addRow("Window Matches (comma-separated):", self.matches_input)
        layout.addRow("Trigger Chance (0.01 to 1.0):", self.chance_spin)
        layout.addRow("Duration (ms):", self.duration_spin)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self) -> dict:
        # Clean up the comma-separated string into a proper list
        matches = [m.strip() for m in self.matches_input.text().split(",") if m.strip()]
        return {
            "text": self.text_input.text().strip(),
            "title_matches": matches,
            "chance": self.chance_spin.value(),
            "duration": self.duration_spin.value()
        }
    
    def set_data(self, data: dict) -> None:
        """Pre-fills the form fields for editing an existing trigger."""
        self.text_input.setText(data.get("text", ""))
        
        matches = data.get("title_matches", [])
        self.matches_input.setText(", ".join(matches))
        
        self.chance_spin.setValue(data.get("chance", 1.0))
        self.duration_spin.setValue(data.get("duration", 4000))

class CollapsibleSection(QWidget):
    """A reusable UI component that expands and collapses its contents."""
    def __init__(self, title: str, checked: bool = False):
        super().__init__()
        self.title = title
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.btn = QPushButton(f"▼  {title}")
        self.btn.setCheckable(True)
        self.btn.setChecked(True)
        self.btn.toggled.connect(self._on_toggle)
        self.btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                font-size: 16px;
                font-family: 'Pixel Code', monospace;
                padding: 6px; background-color: rgba(150, 150, 150, 40);
                border-radius: 4px;
            }
            QPushButton:hover { background-color: rgba(150, 150, 150, 80); }
        """)
        
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(10, 10, 10, 15)
        
        layout.addWidget(self.btn)
        layout.addWidget(self.content)
        self._on_toggle(checked)
        
    def _on_toggle(self, checked: bool) -> None:
        self.content.setVisible(checked)
        self.btn.setText(f"▼  {self.title}" if checked else f"▶  {self.title}")

class CustomSizeGrip(QSizeGrip):
    """A foolproof size grip that manually paints its own diagonal lines."""
    def paintEvent(self, _: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor("#888888")) 
        pen.setWidth(2)
        painter.setPen(pen)
        
        w, h = self.width(), self.height()
        
        # Draw two diagonal lines in the bottom right corner
        painter.drawLine(w - 12, h, w, h - 12)
        painter.drawLine(w - 6, h, w, h - 6)

class ModEditorUI:
    """Handles ONLY visual drawing and layout structuring."""
    
    def setup_ui(self, window: QWidget) -> None:
        window.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        window.resize(880, 620)
        
        self.main_layout = QVBoxLayout(window)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(window, "Mod Editor")
        self.main_layout.addWidget(self.title_bar)
        
        content_widget = QWidget(window)
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(20, 15, 20, 5)
        self.content_layout.setSpacing(10)

        self._build_header()
        
        self.sheet_info_label = QLabel("Sheet: -- x -- px | Base Tile: -- x -- px")
        self.sheet_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sheet_info_label.setObjectName("BannerText")
        self.content_layout.addWidget(self.sheet_info_label)

        split_layout = QHBoxLayout()
        
        # --- LEFT SCROLL AREA ---
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll_content = QWidget()
        
        self.left_layout = QVBoxLayout(left_scroll_content)
        self.left_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Packs elements at the top
        left_scroll.setWidget(left_scroll_content)
        
        # --- RIGHT SCROLL AREA ---
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll_content = QWidget()
        
        self.right_layout = QVBoxLayout(right_scroll_content)
        self.right_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Packs elements at the top
        right_scroll.setWidget(right_scroll_content)
        
        split_layout.addWidget(left_scroll, stretch=1)
        split_layout.addWidget(right_scroll, stretch=1)
        
        self.content_layout.addLayout(split_layout)

        # Build elements inside the layouts
        self._build_mod_selection()
        self._build_preview_area()
        self._build_global_settings()
        self._build_behavior_settings()
        self._build_state_overrides()
        self._build_behavior_options()
        self._build_dialogue_settings()

        self.main_layout.addWidget(content_widget, stretch=1)
        
        # --- FOOTER & SAVE BUTTON ---
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(20, 10, 0, 15) 
        
        self.save_btn = QPushButton("Save config.json")
        self.save_btn.setMinimumWidth(200)
        self.save_btn.setMinimumHeight(35)
        
        # Adding stretches on BOTH sides perfectly centers the button at the bottom
        footer_layout.addStretch()
        footer_layout.addWidget(self.save_btn)
        footer_layout.addStretch()
        
        size_grip = CustomSizeGrip(window)
        size_grip.setFixedSize(16, 16)
        footer_layout.addWidget(size_grip)
        
        self.main_layout.addLayout(footer_layout)

    def _build_header(self) -> None:
        info_label = QLabel(
            "Grid automatically splits your sprite sheet.\n"
            "Ensure every state is mapped to a valid row.",
            alignment=Qt.AlignmentFlag.AlignCenter
        )
        info_label.setObjectName("HelperText")
        self.content_layout.addWidget(info_label)

    def _build_mod_selection(self) -> None:
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Target Mod:"))
        self.mod_combo = QComboBox()
        layout.addWidget(self.mod_combo)
        self.left_layout.addLayout(layout)

    def _build_global_settings(self) -> None:
        section = CollapsibleSection("Grid & Extraction Settings")
        layout = QFormLayout()
        
        self.global_cols_spin = self._create_spinbox(1, 100)
        self.global_rows_spin = self._create_spinbox(1, 100)
        
        lbl_cols = self._create_info_label("Authoring Columns:", "Total columns across the full sheet.")
        lbl_rows = self._create_info_label("Authoring Rows:", "Total rows across the full sheet.")
        
        layout.addRow(lbl_cols, self.global_cols_spin)
        layout.addRow(lbl_rows, self.global_rows_spin)
        
        section.content_layout.addLayout(layout)
        self.left_layout.addWidget(section)

    def _build_behavior_settings(self) -> None:
        section = CollapsibleSection("Core Entity Stats")
        layout = QFormLayout()
        
        self.can_fly_check = QCheckBox("Enable Flight (Ignores Gravity)")
        
        self.max_health_spin = self._create_spinbox(1, 9999)
        self.atk_dmg_spin = self._create_spinbox(0, 9999)
        self.atk_range_spin = self._create_spinbox(0, 2000)
        self.jump_height_spin = self._create_spinbox(0, 100)
        
        self.behavior_type_combo = QComboBox()
        for b_type in BehaviorType:
            self.behavior_type_combo.addItem(b_type.value.capitalize(), userData=b_type)
            
        layout.addRow(self._create_info_label("Behavior Type:", "Determines engine-level AI logic."), self.behavior_type_combo)
        
        layout.addRow("", self.can_fly_check)
        layout.addRow(self._create_info_label("Max Health:", "The total health points of the pet."), self.max_health_spin)
        layout.addRow(self._create_info_label("Attack Damage:", "How much damage this pet deals."), self.atk_dmg_spin)
        layout.addRow(self._create_info_label("Attack Range (px):", "Maximum distance to engage targets."), self.atk_range_spin)
        layout.addRow(self._create_info_label("Jump Height:", "Initial vertical velocity when jumping."), self.jump_height_spin)
        
        section.content_layout.addLayout(layout)
        self.left_layout.addWidget(section)

    def _build_state_overrides(self) -> None:
        section = CollapsibleSection("Animation State Config")
        
        # State Config
        layout = QHBoxLayout()
        layout.addWidget(QLabel("State Config:"))
        self.state_combo = QComboBox()
        layout.addWidget(self.state_combo)
        
        self.copy_btn = QPushButton("Copy")
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setEnabled(False) 

        layout.addWidget(self.copy_btn)
        layout.addWidget(self.paste_btn)
        section.content_layout.addLayout(layout) 
        
        # Swap Data
        swap_layout = QHBoxLayout()
        swap_layout.addWidget(QLabel("Swap Data With:"))
        self.swap_combo = QComboBox()
        for state in PetState:
            self.swap_combo.addItem(state.value.capitalize(), userData=state)
            
        self.swap_btn = QPushButton("Swap")
        swap_layout.addWidget(self.swap_combo)
        swap_layout.addWidget(self.swap_btn)
        section.content_layout.addLayout(swap_layout) 

        # Spinboxes Form
        form = QFormLayout()
        self.row_spin = self._create_spinbox(0, 100)
        self.start_spin = self._create_spinbox(0, 100)
        self.end_spin = self._create_spinbox(0, 100)
        
        self.loop_check = QCheckBox("Loop Animation")
        self.reverse_check = QCheckBox("Play in Reverse")
        
        self.width_spin = self._create_spinbox(0, 2048)
        self.height_spin = self._create_spinbox(0, 2048)
        self.offset_x_spin = self._create_spinbox(-2048, 2048)
        self.offset_y_spin = self._create_spinbox(-2048, 2048)
        self.fps_spin = self._create_spinbox(1, 60)

        form.addRow(self._create_info_label(
            "Mapped Row Index:", "The row index (from 0) where the animation frames are sourced from."), self.row_spin)
        form.addRow(self._create_info_label(
            "Start Frame Index:", "The column index (from 0) where the animation begins."), self.start_spin)
        form.addRow(self._create_info_label(
            "End Frame Index:", "The column index (from 0) where the animation ends."), self.end_spin)
        form.addRow("", self.loop_check)
        form.addRow("", self.reverse_check)
        form.addRow(self._create_info_label(
            "Override Width (px):", "Set above 0 to manually define this frame's width, ignoring the global grid."), self.width_spin)
        form.addRow(self._create_info_label(
            "Override Height (px):", "Set above 0 to manually define this frame's height, ignoring the global grid."), self.height_spin)
        form.addRow(self._create_info_label(
            "Offset X (px):", "Nudge the frame extraction boundary horizontally."), self.offset_x_spin)
        form.addRow(self._create_info_label(
            "Offset Y (px):", "Nudge the frame extraction boundary vertically."), self.offset_y_spin)
        form.addRow(self._create_info_label(
            "Playback Speed (FPS):", "How fast the animation plays. Higher means faster."), self.fps_spin)
        
        section.content_layout.addLayout(form)
        
        self.right_layout.addWidget(section)

    def _build_preview_area(self) -> None:
        layout = QVBoxLayout()
        title = QLabel("Live Animation Preview")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PreviewTitle")
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(150)
        self.preview_label.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        
        self.restart_btn = QPushButton("Restart Animation")
        
        layout.addWidget(title)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.restart_btn)
        self.left_layout.addLayout(layout)
    
    def _build_behavior_options(self) -> None:
        section = CollapsibleSection("Behavior AI Options")
        layout = QFormLayout()
        
        self.add_script_btn = QPushButton("Create Custom AI")
        self.edit_script_btn = QPushButton("Open in VS Code")
        self.delete_script_btn = QPushButton("Delete Script")
        
        layout.addWidget(self.add_script_btn)
        layout.addWidget(self.edit_script_btn)
        layout.addWidget(self.delete_script_btn)
        section.content_layout.addLayout(layout)
        self.right_layout.addWidget(section)
    
    def _build_dialogue_settings(self) -> None:
        section = CollapsibleSection("Dialogue & Speech")
        layout = QVBoxLayout()
        
        # --- Plain Dialogue UI ---
        layout.addWidget(self._create_info_label(
            "Plain Dialogue:", "Randomly spoken, or triggered via 'Talk To'."
        ))
        self.plain_dialogue_list = QListWidget()
        self.plain_dialogue_list.setMinimumHeight(100)
        layout.addWidget(self.plain_dialogue_list)
        
        plain_btn_layout = QHBoxLayout()
        self.add_plain_btn = QPushButton("+ Add Line")
        self.edit_plain_btn = QPushButton("✎ Edit")
        self.del_plain_btn = QPushButton("- Remove Line")
        plain_btn_layout.addWidget(self.add_plain_btn)
        plain_btn_layout.addWidget(self.edit_plain_btn)
        plain_btn_layout.addWidget(self.del_plain_btn)
        layout.addLayout(plain_btn_layout)
        
        # --- Window Triggers UI ---
        layout.addSpacing(10)
        layout.addWidget(self._create_info_label(
            "Window Triggers:", "Displays as: Text | Matches | Chance (%)"
        ))
        self.window_triggers_list = QListWidget()
        self.window_triggers_list.setMinimumHeight(150)
        layout.addWidget(self.window_triggers_list)
        
        trigger_btn_layout = QHBoxLayout()
        self.add_trigger_btn = QPushButton("+ Add Trigger")
        self.edit_trigger_btn = QPushButton("✎ Edit")
        self.del_trigger_btn = QPushButton("- Remove Trigger")
        trigger_btn_layout.addWidget(self.add_trigger_btn)
        trigger_btn_layout.addWidget(self.edit_trigger_btn)
        trigger_btn_layout.addWidget(self.del_trigger_btn)
        layout.addLayout(trigger_btn_layout)
        
        section.content_layout.addLayout(layout)
        self.right_layout.addWidget(section)
    
    def _create_spinbox(self, min_val: int, max_val: int, special_text: Optional[str] = None) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        if special_text:
            spin.setSpecialValueText(special_text)
        return spin
    
    def _create_info_label(self, text: str, tooltip_text: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(text)
        icon_lbl = ToolTipLabel(text="[?]", tooltip_text=tooltip_text)
        
        layout.addWidget(lbl)
        layout.addWidget(icon_lbl)
        layout.addStretch() 
        return widget

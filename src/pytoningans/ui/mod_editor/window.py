from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QScrollArea, QFrame,
    QMessageBox, QLabel, QLineEdit, QFileDialog
)
from PySide6.QtCore import QRect, Qt, Signal, QUrl, QTimer
from PySide6.QtGui import QGuiApplication, QResizeEvent, QDesktopServices, QScreen

from pytoningans.core.mod_manager import ModManager, CURRENT_CONFIG_VERSION
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.mod_editor.components import CustomSizeGrip
from pytoningans.ui.mod_editor.controller import ModEditorController
from pytoningans.ui.mod_editor.panels.dialogue_panel import DialoguePanel
from pytoningans.ui.mod_editor.panels.behavior_panel import BehaviorStatsPanel, BehaviorScriptPanel
from pytoningans.ui.mod_editor.panels.animation_panel import AnimationSubsystem
from pytoningans.ui.mod_editor.panels.physics_panel import PhysicsPanel
from pytoningans.utils.assets import get_main_icon

class ModEditorWindow(QWidget):
    mods_updated = Signal()
    
    def __init__(self, mod_manager: ModManager) -> None:
        super().__init__(
            windowTitle="Mod Editor",
            windowIcon=get_main_icon()
        )
        self.controller = ModEditorController(mod_manager)
        self._current_loaded_mod: Optional[str] = None
        
        self._setup_ui()
        self._connect_signals()
        
        # Silently hydrate the combo box to prevent premature load events
        self.mod_combo.blockSignals(True)
        for folder, name in self.controller.get_mod_list().items():
            self.mod_combo.addItem(name, userData=folder)
        self.mod_combo.blockSignals(False)
        
        # Wait for the ModManagerHub to finish passing the target index, 
        # then guarantee the mod is loaded exactly once.
        QTimer.singleShot(0, self._check_initial_load)
            
        self._center_window()
    
    def _check_initial_load(self) -> None:
        """
        Fallback loader if the Hub opens the window to the first item (index 0),
        which doesn't trigger an index change.
        """
        if self._current_loaded_mod is None and self.mod_combo.count() > 0:
            self._on_mod_changed(self.mod_combo.currentData())

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(880, 620)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(CustomTitleBar(self, "Mod Editor"))
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 15, 20, 5)
        
        # Header Info
        header_lbl = QLabel("Grid automatically splits your sprite sheet.\nEnsure every state is mapped.")
        header_lbl.setObjectName("HelperText")
        header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(header_lbl)
        
        self.sheet_info_label = QLabel()
        self.sheet_info_label.setObjectName("BannerText")
        self.sheet_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.sheet_info_label)
        
        # Instantiate Subsystems
        self.dialogue_panel = DialoguePanel(self.controller)
        self.behavior_stats = BehaviorStatsPanel(self.controller)
        self.behavior_script = BehaviorScriptPanel(self.controller)
        self.anim_sys = AnimationSubsystem(self.controller, self.sheet_info_label)
        self.physics_panel = PhysicsPanel(self.controller)
        
        self.panels = [
            self.dialogue_panel, self.behavior_stats, self.behavior_script, self.anim_sys,
            self.physics_panel
        ]

        # Scroll Areas
        split_layout = QHBoxLayout()
        
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_content = QWidget()
        self.left_layout = QVBoxLayout(left_content)
        self.left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_content = QWidget()
        self.right_layout = QVBoxLayout(right_content)
        self.right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Build Top Mod Selection
        mod_layout = QHBoxLayout()
        mod_layout.addWidget(QLabel("Target Mod:"))
        self.mod_combo = QComboBox()
        mod_layout.addWidget(self.mod_combo)
        
        # Version indicator
        self.version_label = QLabel("v?")
        self.version_label.setStyleSheet("color: gray; font-style: italic;")
        mod_layout.addWidget(self.version_label)
        mod_layout.addStretch() # Push everything to the left
        
        self.left_layout.addLayout(mod_layout)
        
        # Display Name Editor
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Display Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. My Cool Pet")
        name_layout.addWidget(self.name_input)
        self.left_layout.addLayout(name_layout)
        
        # Replace Sprite Sheet Button
        sheet_layout = QHBoxLayout()
        self.change_sheet_btn = QPushButton("Replace Sprite Sheet")
        sheet_layout.addWidget(self.change_sheet_btn)
        sheet_layout.addStretch()
        self.left_layout.addLayout(sheet_layout)
        
        # Mount the Domain Panels
        self.left_layout.addWidget(self.anim_sys.preview_panel)
        self.left_layout.addWidget(self.anim_sys.grid_panel)
        self.left_layout.addWidget(self.behavior_stats)
        self.left_layout.addWidget(self.anim_sys.debug_panel)
        
        self.right_layout.addWidget(self.anim_sys.state_panel)
        self.right_layout.addWidget(self.physics_panel)
        self.right_layout.addWidget(self.behavior_script)
        self.right_layout.addWidget(self.dialogue_panel)
        
        left_scroll.setWidget(left_content)
        right_scroll.setWidget(right_content)
        split_layout.addWidget(left_scroll, stretch=1)
        split_layout.addWidget(right_scroll, stretch=1)
        content_layout.addLayout(split_layout)
        main_layout.addWidget(content_widget, stretch=1)
        
        # Footer
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(20, 10, 0, 15)
        
        self.open_folder_btn = QPushButton("Open Mod Folder")
        self.open_folder_btn.setMinimumSize(150, 35)
        
        self.reload_btn = QPushButton("Discard Unsaved Changes")
        self.reload_btn.setMinimumSize(200, 35)
         
        self.save_btn = QPushButton("Save config.json")
        self.save_btn.setMinimumSize(200, 35)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.open_folder_btn)
        footer_layout.addStretch()
        footer_layout.addWidget(self.reload_btn)
        footer_layout.addSpacing(35)
        footer_layout.addWidget(self.save_btn)
        footer_layout.addStretch()
        
        self.grip = CustomSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        main_layout.addLayout(footer_layout)

    def _connect_signals(self) -> None:
        self.mod_combo.currentIndexChanged.connect(self._on_combo_index_changed)
        self.name_input.textChanged.connect(self._on_name_changed)
        self.save_btn.clicked.connect(self._save_changes)
        self.reload_btn.clicked.connect(self._on_reload_clicked)
        self.open_folder_btn.clicked.connect(self._on_open_folder_clicked)
        self.change_sheet_btn.clicked.connect(self._on_change_sheet_clicked)
    
    def _on_combo_index_changed(self, index: int) -> None:
        if index < 0: return
        mod_folder = self.mod_combo.itemData(index)
        self._on_mod_changed(mod_folder)

    def _on_mod_changed(self, mod_folder: str) -> None:
        if not mod_folder: return
        
        # Block duplicate load events caused by UI initialization triggers
        if getattr(self, "_current_loaded_mod", None) == mod_folder:
            return
        
        self._current_loaded_mod = mod_folder
            
        if self.controller.load_mod(mod_folder):
            current_v: int = self.controller.get_config_version()
            self.version_label.setText(f"v{current_v}")
            
            if current_v < CURRENT_CONFIG_VERSION:
                # Add a visual warning color for outdated mods
                self.version_label.setStyleSheet("color: #d97706; font-weight: bold;")
                QMessageBox.warning(
                    self, "Legacy Mod",
                    f"Saving will upgrade config to v{CURRENT_CONFIG_VERSION}."
                )
            else:
                self.version_label.setStyleSheet("color: gray; font-style: italic;")
            
            # Fill the Display Name box without triggering an edit event
            self.name_input.blockSignals(True)
            self.name_input.setText(self.controller.get_mod_name())
            self.name_input.blockSignals(False)
                
            for panel in self.panels:
                panel.load_data()
        else:
            QMessageBox.warning(self, "Load Error", f"Could not load {mod_folder}.")

    def _save_changes(self) -> None:
        mod_folder: str = self.mod_combo.currentData()
        if not mod_folder: return
        
        self.controller.save_mod(mod_folder)
        
        # Update the editor's combo box and version label
        current_idx: int = self.mod_combo.currentIndex()
        new_name: str = self.controller.get_mod_name()
        self.mod_combo.setItemText(current_idx, new_name)
        
        new_v: int = self.controller.get_config_version()
        self.version_label.setText(f"v{new_v}")
        self.version_label.setStyleSheet("color: gray; font-style: italic;")
        
        self.mods_updated.emit()
        QMessageBox.information(self, "Success", f"Saved configuration for {mod_folder}!")
            
    def _center_window(self) -> None:
        screen: QScreen = QGuiApplication.primaryScreen()
        if not screen: return
        geom: QRect = self.frameGeometry()
        geom.moveCenter(screen.availableGeometry().center())
        self.move(geom.topLeft())
    
    def _on_reload_clicked(self) -> None:
        mod_folder: str = self.mod_combo.currentData()
        if not mod_folder: return
        
        reply: QMessageBox.StandardButton = QMessageBox.question(
            self, "Discard Changes",
            "This will wipe all unsaved tweaks (including cropping boundaries)"
            " and reload the last saved config.json.\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._current_loaded_mod = None
            # Re-triggering this method flushes the engine's memory cache,
            # reads the disk files again, and forces every panel to update its UI.
            self._on_mod_changed(mod_folder)
            
            # Explicitly kill crop mode in the animation panel
            self.anim_sys.crop_check.setChecked(False)
    
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        # Move the grip to the absolute bottom-right corner
        self.grip.move(
            self.width() - self.grip.width(),
            self.height() - self.grip.height()
        )
    
    def _on_open_folder_clicked(self) -> None:
        mod_folder: str = self.mod_combo.currentData()
        if not mod_folder: return
        
        target_dir: Path = self.controller.manager.mods_dir / mod_folder
        if not target_dir.exists(): return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_dir.resolve())))
    
    def _on_name_changed(self, text: str) -> None:
        if not text.strip(): return
        self.controller.update_mod_name(text.strip())
    
    def _on_change_sheet_clicked(self) -> None:
        mod_folder: str = self.mod_combo.currentData()
        if not mod_folder: return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select New Sprite Sheet", "", "Images (*.png)"
        )
        if not file_path: return
        
        reply: QMessageBox.StandardButton = QMessageBox.question(
            self, "Confirm Replacement", 
            "This will overwrite the current sprite_sheet.png for this mod. Continue?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.replace_sprite_sheet(mod_folder, file_path)
            self._current_loaded_mod = None
            self._on_mod_changed(mod_folder) # Force full reload to refresh the live preview panels
            QMessageBox.information(self, "Success", "Sprite sheet updated successfully!")
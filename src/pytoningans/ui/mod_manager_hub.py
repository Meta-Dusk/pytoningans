import shutil
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QListWidgetItem, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QGuiApplication, QDesktopServices

from pytoningans.core.mod_manager import ModManager
from pytoningans.ui.title_bar import CustomTitleBar
from pytoningans.ui.mod_creation_dialog import ModCreationDialog
from pytoningans.ui.mod_editor import ModEditorWindow
from pytoningans.utils.assets import get_main_icon

class ModManagerHub(QWidget):
    mods_updated = Signal()
    
    def __init__(self, mod_manager: ModManager) -> None:
        super().__init__(
            windowTitle="Mod Manager Hub",
            windowIcon=get_main_icon()
        )
        self.mod_manager = mod_manager
        self.editor_window: Optional[ModEditorWindow] = None
        
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(450, 300)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self, "Mod Manager Hub")
        main_layout.addWidget(self.title_bar)
        
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)
        
        list_layout = QVBoxLayout()
        list_layout.addWidget(QLabel("Installed Mods:"))
        
        self.mod_list = QListWidget()
        list_layout.addWidget(self.mod_list)
        
        content_layout.addLayout(list_layout, stretch=2)
        
        btn_layout = QVBoxLayout()
        
        self.create_btn = QPushButton("Create New Mod")
        self.edit_btn = QPushButton("Edit Selected")
        self.open_folder_btn = QPushButton("Open Folder")
        self.delete_btn = QPushButton("Delete Selected")
        
        self.edit_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        
        self.create_btn.clicked.connect(self._on_create_clicked)
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        self.open_folder_btn.clicked.connect(self._on_open_folder_clicked)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.mod_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        
        content_layout.addLayout(btn_layout, stretch=1)
        main_layout.addWidget(content_widget)
        
        self._center_window()

    def _center_window(self) -> None:
        screen = QGuiApplication.primaryScreen()
        screen_geom = screen.availableGeometry()
        window_geom = self.frameGeometry()
        window_geom.moveCenter(screen_geom.center())
        self.move(window_geom.topLeft())

    def _refresh_list(self) -> None:
        self.mod_list.clear()
        self.mod_list.addItems(self.mod_manager.get_available_mods())

    def _on_create_clicked(self) -> None:
        dialog = ModCreationDialog(self.mod_manager.mods_dir, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._refresh_list()
            self.mods_updated.emit()
            self._open_editor(dialog.new_mod_folder)

    def _on_edit_clicked(self) -> None:
        selected: List[QListWidgetItem] = self.mod_list.selectedItems()
        if not selected: return
        self._open_editor(selected[0].text())

    def _open_editor(self, mod_folder: str) -> None:
        if self.editor_window is None or not self.editor_window.isVisible():
            self.editor_window = ModEditorWindow(self.mod_manager)
            self.editor_window.mods_updated.connect(self.mods_updated.emit)
            self.editor_window.show()
        else:
            self.editor_window.activateWindow()
            
        self.editor_window.mod_combo.setCurrentText(mod_folder)

    def _on_delete_clicked(self) -> None:
        selected: List[QListWidgetItem] = self.mod_list.selectedItems()
        if not selected: return
        mod_folder: str = selected[0].text()
        
        reply: QMessageBox.StandardButton = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to permanently delete the '{mod_folder}' "
            "mod?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            target_dir: Path = self.mod_manager.mods_dir / mod_folder
            try:
                shutil.rmtree(target_dir)
                self._refresh_list()
                self.mods_updated.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete mod: {str(e)}")
    
    def _on_selection_changed(self) -> None:
        has_selection: bool = len(self.mod_list.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.open_folder_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def _on_open_folder_clicked(self) -> None:
        selected: List[QListWidgetItem] = self.mod_list.selectedItems()
        if not selected: return
        mod_folder: str = selected[0].text()
        
        target_dir: Path = self.mod_manager.mods_dir / mod_folder
        if target_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_dir.resolve())))
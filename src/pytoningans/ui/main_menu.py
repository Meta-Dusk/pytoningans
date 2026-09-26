import random

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from typing import Optional

from pytoningans.core.constants import MENU_CFG
from pytoningans.core.pet_manager import PetManager
from pytoningans.ui.mod_editor import ModEditorWindow

class MainMenu(QWidget):
    def __init__(self, manager: PetManager) -> None:
        super().__init__()
        self.manager: PetManager = manager
        self.editor_window: Optional[ModEditorWindow] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle(MENU_CFG.title)
        self.resize(MENU_CFG.width, MENU_CFG.height)
        
        layout: QVBoxLayout = QVBoxLayout(self)
        
        self.spawn_btn: QPushButton = QPushButton(MENU_CFG.spawn_btn_text, self)
        self.spawn_btn.clicked.connect(self._on_spawn_clicked)
        
        self.edit_btn: QPushButton = QPushButton("Open Mod Editor", self)
        self.edit_btn.clicked.connect(self._open_editor)
        
        layout.addWidget(self.spawn_btn)
        layout.addWidget(self.edit_btn)

    def _on_spawn_clicked(self) -> None:
        # Spawn new pets at random coordinates near the center of a typical 1080p screen
        random_x: int = random.randint(300, 1500)
        random_y: int = random.randint(200, 800)
        self.manager.spawn_pet(random_x, random_y)
    
    def _open_editor(self) -> None:
        if self.editor_window is None:
            self.editor_window = ModEditorWindow(self.manager.mod_manager)
        self.editor_window.showNormal()
        self.editor_window.activateWindow()
import random

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QApplication
from PySide6.QtCore import Qt
from typing import Optional

from pytoningans.core.pet_manager import PetManager
from pytoningans.ui.mod_editor import ModEditorWindow
from pytoningans.ui.theme import LIGHT_THEME, DARK_THEME
from pytoningans.ui.title_bar import CustomTitleBar

class MainMenu(QWidget):
    def __init__(self, manager: PetManager) -> None:
        super().__init__()
        self.manager: PetManager = manager
        self.editor_window: Optional[ModEditorWindow] = None
        self._is_dark_mode: bool = True
        self._setup_ui()

    def _setup_ui(self) -> None:
        # Strip the OS window frame
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(300, 150)
        
        # The main layout gets 0 margins so the title bar touches the edges
        main_layout: QVBoxLayout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar: CustomTitleBar = CustomTitleBar(self, "Control Panel")
        main_layout.addWidget(self.title_bar)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        self.spawn_btn: QPushButton = QPushButton("Spawn Pet", self)
        self.spawn_btn.clicked.connect(self._on_spawn_clicked)
        
        self.edit_btn: QPushButton = QPushButton("Open Mod Editor", self)
        self.edit_btn.clicked.connect(self._open_editor)

        self.theme_btn: QPushButton = QPushButton("Switch to Light Mode", self)
        self.theme_btn.clicked.connect(self._toggle_theme)
        
        content_layout.addWidget(self.spawn_btn)
        content_layout.addWidget(self.edit_btn)
        content_layout.addWidget(self.theme_btn)
        content_layout.addStretch()
        
        main_layout.addWidget(content_widget)

    def _toggle_theme(self) -> None:
        self._is_dark_mode = not self._is_dark_mode
        app = QApplication.instance()
        
        if not isinstance(app, QApplication): return
        if self._is_dark_mode:
            app.setStyleSheet(DARK_THEME)
            self.theme_btn.setText("Switch to Light Mode")
        else:
            app.setStyleSheet(LIGHT_THEME)
            self.theme_btn.setText("Switch to Dark Mode")

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
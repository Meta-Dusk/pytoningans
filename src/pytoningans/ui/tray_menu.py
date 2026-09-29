from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction

from pytoningans.ui.main_menu import MainMenu
from pytoningans.core.constants import APP_CFG
from pytoningans.utils.paths import get_asset_path

class AppTray(QSystemTrayIcon):
    def __init__(self, main_menu: MainMenu, icon_path: str = "assets/ui/teto.png") -> None:
        # Create the icon, falling back to a default empty one if the PNG is missing
        icon: QIcon = QIcon(get_asset_path(icon_path).as_posix())
        super().__init__(icon)
        
        self.main_menu: MainMenu = main_menu
        self.setToolTip(APP_CFG.app_name)
        self._setup_menu()

    def _setup_menu(self) -> None:
        menu: QMenu = QMenu()
        
        show_action: QAction = QAction("Show Control Panel", menu)
        show_action.triggered.connect(self._show_menu)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        quit_action: QAction = QAction("Quit Tetoningans", menu)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)

    def _show_menu(self) -> None:
        self.main_menu.showNormal()
        self.main_menu.activateWindow()
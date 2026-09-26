import sys, signal

from PySide6.QtWidgets import QApplication

from pytoningans.core.constants import APP_CFG
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.pet_manager import PetManager
from pytoningans.ui.main_menu import MainMenu
from pytoningans.ui.tray_menu import AppTray
from pytoningans.ui.theme import DARK_THEME
from pytoningans.utils.paths import get_mods_directory, setup_default_mod

def main() -> None:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app: QApplication = QApplication(sys.argv)
    app.setApplicationName(APP_CFG.app_name)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(DARK_THEME)
    
    # Setup external directory and ensure the default mod exists
    mods_dir: str = get_mods_directory()
    setup_default_mod(mods_dir)
    
    # Initialize Mod Manager
    mod_manager: ModManager = ModManager(mods_dir)
    
    available_mods = mod_manager.get_available_mods()
    if available_mods:
        # Load the default_pet (or whatever the first item is)
        mod_manager.load_mod(available_mods[0])
        
    # Initialize UI
    pet_manager: PetManager = PetManager(mod_manager)
    menu: MainMenu = MainMenu(pet_manager)
    menu.show()
    
    tray: AppTray = AppTray(menu)
    tray.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
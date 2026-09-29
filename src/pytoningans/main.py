import sys, signal, os
from typing import List

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFontDatabase, QFont
from PySide6.QtCore import Qt

from pytoningans.core.constants import APP_CFG
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.pet_manager import PetManager
from pytoningans.ui.main_menu import MainMenu
from pytoningans.ui.tray_menu import AppTray
from pytoningans.ui.theme import DARK_THEME
from pytoningans.utils.paths import get_mods_directory, setup_default_mod, get_asset_path

def main() -> None:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app: QApplication = QApplication(sys.argv)
    app.setApplicationName(APP_CFG.app_name)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(DARK_THEME)
    app.setWindowIcon(QIcon("assets/ui/teto.ico"))
    
    font_path: str = get_asset_path("assets/ui/PixelCode.otf").as_posix()
    font_id: int = QFontDatabase.addApplicationFont(font_path)
    
    if font_id < 0:
        print(f"Warning: Failed to load custom font from {font_path}")
    else:
        font_families: List[str] = QFontDatabase.applicationFontFamilies(font_id)
        
        default_font = QFont(font_families[0])
        default_font.setStyleStrategy(
            QFont.StyleStrategy.PreferQuality | QFont.StyleStrategy.PreferAntialias)
        default_font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        
        # Apply the crisp font settings to the entire application
        app.setFont(default_font)
    
    # Setup external directory and ensure the default mod exists
    mods_dir = get_mods_directory()
    setup_default_mod(mods_dir)
    
    # Initialize Mod Manager
    mod_manager: ModManager = ModManager(mods_dir.as_posix())
    
    available_mods: List[str] = mod_manager.get_available_mods()
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
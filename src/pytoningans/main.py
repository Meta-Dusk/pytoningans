from pathlib import Path
import sys, signal, os

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFontDatabase, QFont
from PySide6.QtCore import Qt

from pytoningans.core.constants import APP_CFG, EntityType
from pytoningans.core.mod_manager import ModManager
from pytoningans.core.entity_manager import EntityManager
from pytoningans.ui.main_menu import MainMenu
from pytoningans.ui.tray_menu import AppTray
from pytoningans.ui.theme import DARK_THEME
from pytoningans.utils.paths import get_mods_directory, get_asset_path

def main() -> None:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app: QApplication = QApplication(sys.argv)
    app.setApplicationName(APP_CFG.app_name)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(DARK_THEME)
    window_icon = QIcon(get_asset_path("assets/icon.ico").as_posix())
    app.setWindowIcon(window_icon)
    
    font_path: str = get_asset_path("assets/ui/PixelCode.otf").as_posix()
    font_id: int = QFontDatabase.addApplicationFont(font_path)
    
    if font_id < 0:
        print(f"Warning: Failed to load custom font from {font_path}")
    else:
        font_families: list[str] = QFontDatabase.applicationFontFamilies(font_id)
        
        default_font = QFont(font_families[0])
        default_font.setStyleStrategy(
            QFont.StyleStrategy.PreferQuality | QFont.StyleStrategy.PreferAntialias)
        default_font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        
        # Apply the crisp font settings to the entire application
        app.setFont(default_font)
    
    # Initialize Mod Manager
    mods_dir: Path = get_mods_directory()
    mod_manager: ModManager = ModManager(mods_dir.as_posix())
    
    available_mods: dict[str, tuple[str, str]] = mod_manager.get_available_mods_with_type()
    if available_mods:
        # Prefer loading a pet mod on launch if available; fallback to the first entry
        initial_mod: str = next(
            (
                folder for folder,
                (_, entity_type) in available_mods.items()
                if entity_type == EntityType.PET.value
            ),
            next(iter(available_mods))
        )
        mod_manager.load_mod(initial_mod)
        
    # Initialize UI
    pet_manager: EntityManager = EntityManager(mod_manager)
    menu: MainMenu = MainMenu(pet_manager)
    menu.show()
    
    tray: AppTray = AppTray(menu)
    tray.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
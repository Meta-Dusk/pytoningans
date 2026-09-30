import sys
from pathlib import Path
from PySide6.QtCore import QStandardPaths

from pytoningans.core.constants import APP_CFG

def is_compiled() -> bool:
    """Detects if the app is packaged via pyside6-deploy (Nuitka) or PyInstaller."""
    return getattr(sys, 'frozen', False) or "__compiled__" in globals()

def get_base_path() -> Path:
    """
    Returns the absolute root path.
    - pyside6-deploy (Nuitka): The .dist folder containing the .exe
    - PyInstaller: The temporary _MEIPASS folder
    - Source: The project root directory
    """
    if hasattr(sys, '_MEIPASS'):
        return Path(getattr(sys, '_MEIPASS'))
        
    if is_compiled():
        return Path(sys.executable).parent
        
    # If running from source, go up 4 levels (src/pytoningans/utils/paths.py -> root)
    return Path(__file__).resolve().parents[3]

def get_asset_path(relative_path: str) -> Path:
    """Helper to safely resolve asset paths using pathlib."""
    return get_base_path() / relative_path

def get_mods_directory() -> Path:
    """Safely resolves and creates the Documents/PyToNingans/mods folder."""
    docs_path = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation))
    
    # Resolves to Documents/PyToNingans/mods
    mods_dir = docs_path / APP_CFG.app_name / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)
    
    return mods_dir

import sys, os, shutil

from PySide6.QtCore import QStandardPaths

from pytoningans.core.constants import APP_CFG

def get_mods_directory() -> str:
    """Safely resolves and creates the Documents/PyToNingans/mods folder."""
    docs_path: str = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    mods_dir: str = os.path.join(docs_path, APP_CFG.app_name, "mods")
    os.makedirs(mods_dir, exist_ok=True)
    return mods_dir

def get_asset_path(relative_path: str) -> str:
    """
    Helper to safely resolve asset paths whether running from source or compiled.
    
    **Examples of** `relative_path`:
    - (if file is in `assets/`) "assets/image.png"
    - (if file is in a subdirectory) "assets/images/image.png"
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
    
    is_frozen: bool = getattr(sys, 'frozen', False)
    if is_frozen and hasattr(sys, '_MEIPASS'):
        base_path = getattr(sys, '_MEIPASS')
        
    return os.path.join(base_path, relative_path)

def setup_default_mod(external_mods_dir: str) -> None:
    """Copies the bundled default mod to the Documents folder on first launch."""
    target_mod_path = os.path.join(external_mods_dir, "default_pet")
    
    if os.path.exists(target_mod_path):
        return

    # Default behavior (Works for Source Code AND pyside6-deploy / Nuitka)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    bundled_assets = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "assets"))

    # PyInstaller Fallback
    is_frozen: bool = getattr(sys, 'frozen', False)
    if is_frozen and hasattr(sys, '_MEIPASS'):
        meipass_path: str = getattr(sys, '_MEIPASS')
        bundled_assets = os.path.join(meipass_path, "assets")

    bundled_mod_path = os.path.join(bundled_assets, "mods", "default_pet")

    if os.path.exists(bundled_mod_path):
        try:
            shutil.copytree(bundled_mod_path, target_mod_path)
            print(f"First launch: Copied default mod to {target_mod_path}")
        except Exception as e:
            print(f"Failed to copy default mod: {e}")
    else:
        print(f"Warning: Bundled default mod not found at {bundled_mod_path}")

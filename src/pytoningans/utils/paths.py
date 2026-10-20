import sys
from pathlib import Path
from typing import Any, Optional
from PySide6.QtCore import QStandardPaths

from pytoningans.core.constants import APP_CONFIG

def is_compiled() -> bool:
    """
    Detects if the app is packaged via pyside6-deploy (Nuitka) or PyInstaller.
    """
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
    docs_path = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    )
    
    # Resolves to Documents/PyToNingans/mods
    mods_dir: Path = docs_path / APP_CONFIG.name / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)
    
    return mods_dir

def get_settings_path() -> Path:
    """Safely resolves Documents/PyToNingans/settings.json."""
    docs_path = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    )
    app_dir: Path = docs_path / APP_CONFIG.name
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir / "settings.json"

_DEFAULT_APP_VERSION: str = "0.8.1"
_CACHED_APP_VERSION: Optional[str] = None

def get_app_version() -> str:
    """
    Extracts the application version string.
    Dynamically loads from pyproject.toml at the root directory, with fallbacks
    for packaged builds.
    """
    global _CACHED_APP_VERSION
    if _CACHED_APP_VERSION is not None:
        return _CACHED_APP_VERSION

    # Attempt to read from pyproject.toml at project root
    try:
        pyproject_file: Path = get_base_path() / "pyproject.toml"
        if pyproject_file.exists():
            import tomllib
            data: dict[str, Any] = tomllib.loads(pyproject_file.read_text(encoding="utf-8"))
            version: str = data.get("project", {}).get("version")
            if version:
                _CACHED_APP_VERSION = str(version)
                return _CACHED_APP_VERSION
    except Exception:
        pass

    # Attempt to resolve via package metadata
    try:
        from importlib.metadata import version as meta_version
        _CACHED_APP_VERSION = meta_version("pytoningans")
        return _CACHED_APP_VERSION
    except Exception:
        pass

    # Default fallback
    _CACHED_APP_VERSION = _DEFAULT_APP_VERSION
    return _CACHED_APP_VERSION


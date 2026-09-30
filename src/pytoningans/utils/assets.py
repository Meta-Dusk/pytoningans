import platform
from typing import Optional

from PySide6.QtGui import QIcon

from pytoningans.utils.paths import get_asset_path

is_windows: bool = platform.system() == "Windows"

# Store the cached icon privately
_main_window_icon: Optional[QIcon] = None

def get_main_icon() -> QIcon:
    """Lazily loads and caches the main window icon."""
    global _main_window_icon
    if _main_window_icon is None:
        _main_window_icon = QIcon(
            get_asset_path(
                "assets/icon.ico"
                if is_windows else
                "assets/icon.png"
            ).as_posix()
        )
    return _main_window_icon
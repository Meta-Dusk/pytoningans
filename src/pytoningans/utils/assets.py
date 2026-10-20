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


_google_icon: Optional[QIcon] = None

def get_google_icon() -> QIcon:
    """Lazily loads and caches the Google logo icon."""
    global _google_icon
    if _google_icon is None:
        icon_path = get_asset_path("assets/ui/google_icon.png")
        if icon_path.exists():
            _google_icon = QIcon(icon_path.as_posix())
        else:
            _google_icon = QIcon()
    return _google_icon


_github_icon: Optional[QIcon] = None

def get_github_icon() -> QIcon:
    """Lazily loads and caches the GitHub logo icon."""
    global _github_icon
    if _github_icon is None:
        icon_path = get_asset_path("assets/ui/github_icon.png")
        if icon_path.exists():
            _github_icon = QIcon(icon_path.as_posix())
        else:
            _github_icon = QIcon()
    return _github_icon

"""
PyToNingans - Avatar and Profile Image Utilities
===============================================
Provides disk-cached, async, circular avatar rendering for community creators.
Supports provider web URLs (GitHub/Google), local custom avatar image files,
and automatic fallback initials badges when offline.
"""
from __future__ import annotations

import hashlib, threading
import urllib.request
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QLabel

from pytoningans.utils.paths import get_settings_path, _DEFAULT_APP_VERSION

if TYPE_CHECKING:
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QWidget


def get_avatar_cache_dir() -> Path:
    """Returns local disk cache directory for downloaded creator avatars."""
    cache_dir: Path = get_settings_path().parent / "avatars"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cached_avatar_file(url_or_key: str) -> Path:
    """Derives unique local cached file path from URL or key."""
    hash_key: str = hashlib.md5(url_or_key.strip().encode("utf-8")).hexdigest()
    return get_avatar_cache_dir() / f"avatar_{hash_key}.png"


def make_circular_pixmap(source: QPixmap, size: int) -> QPixmap:
    """
    Crops source QPixmap to a center square, scales smoothly, and clips
    into an antialiased circular QPixmap.
    """
    if source.isNull() or size <= 0:
        return QPixmap(size, size)

    # Scale preserving aspect ratio by expanding to cover size x size
    scaled: QPixmap = source.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )

    # Crop to centered square
    x: int = max(0, (scaled.width() - size) // 2)
    y: int = max(0, (scaled.height() - size) // 2)
    square: QPixmap = scaled.copy(x, y, size, size)

    # Create destination transparent pixmap
    target = QPixmap(size, size)
    target.fill(Qt.GlobalColor.transparent)

    painter = QPainter(target)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, square)
    painter.end()

    return target


def make_initials_pixmap(
    initial: str,
    size: int,
    bg_color: str = "#89b4fa",
    text_color: str = "#1e1e2e",
) -> QPixmap:
    """Renders a stylish antialiased circular badge containing uppercase initial."""
    target = QPixmap(size, size)
    target.fill(Qt.GlobalColor.transparent)

    painter = QPainter(target)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.fillPath(path, QColor(bg_color))

    font: QFont = painter.font()
    font.setPixelSize(max(10, int(size * 0.44)))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(text_color))

    letter = (initial.strip()[:1].upper()) if initial.strip() else "M"
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, letter)
    painter.end()

    return target


def load_circular_avatar(
    source: Optional[str | Path],
    size: int = 42,
    fallback_initial: str = "M",
    callback: Optional[Callable[[QPixmap], None]] = None,
) -> QPixmap:
    """
    Loads and returns a circular QPixmap.
    - If local file exists, loads immediately.
    - If URL is already cached, loads immediately.
    - If URL is not cached, launches a background download thread, invokes callback on UI thread,
      and returns fallback initials pixmap immediately.
    """
    initial_pix: QPixmap = make_initials_pixmap(fallback_initial, size)
    if source is None or not source:
        return initial_pix

    source_str: str = str(source).strip()
    if not source_str:
        return initial_pix

    # Local disk file (e.g. user-selected custom avatar)
    local_path = Path(source_str)
    if local_path.is_file():
        try:
            pix = QPixmap(str(local_path))
            if not pix.isNull():
                return make_circular_pixmap(pix, size)
        except Exception:
            pass
        return initial_pix

    # Web URL (e.g. GitHub or Google avatar_url)
    if source_str.startswith("http://") or source_str.startswith("https://"):
        cache_file = get_cached_avatar_file(source_str)
        if cache_file.is_file() and cache_file.stat().st_size > 0:
            try:
                pix = QPixmap(str(cache_file))
                if not pix.isNull():
                    return make_circular_pixmap(pix, size)
            except Exception:
                pass

        # If not cached and callback provided, fetch asynchronously in background
        if callback is not None:
            def _worker() -> None:
                try:
                    req = urllib.request.Request(
                        source_str,
                        headers={
                            "User-Agent": f"PyToNingans-Modder/{_DEFAULT_APP_VERSION}"
                        },
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        content: bytes = resp.read()
                        cache_file.write_bytes(content)

                        pix_fetched = QPixmap()
                        pix_fetched.loadFromData(content)
                        if not pix_fetched.isNull():
                            circ: QPixmap = make_circular_pixmap(pix_fetched, size)
                            QTimer.singleShot(0, lambda: callback(circ))
                except Exception:
                    pass

            threading.Thread(target=_worker, daemon=True).start()

    return initial_pix


class AvatarLabel(QLabel):
    """
    Interactive circular avatar display widget with antialiased borders,
    offline caching, and background loading.
    """

    def __init__(
        self,
        size: int = 44,
        parent: Optional[QWidget] = None,
        border_color: str = "#89b4fa",
        border_width: int = 2,
    ) -> None:
        super().__init__(parent)
        self._size = size
        self._border_color = border_color
        self._border_width = border_width
        self._current_source: Optional[str] = None
        self._initial: str = "M"

        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_border_style()

    def _apply_border_style(self) -> None:
        radius: int = self._size // 2
        self.setStyleSheet(f"""
            QLabel {{
                border: {self._border_width}px solid {self._border_color};
                border-radius: {radius}px;
                background-color: #1e1e2e;
            }}
        """)

    def set_border_color(self, hex_color: str) -> None:
        self._border_color = hex_color
        self._apply_border_style()

    def set_avatar(self, source: Optional[str | Path], initial: str = "M") -> None:
        """Sets the avatar source (file path or URL) and fallback initial."""
        self._current_source = str(source) if source else None
        self._initial = initial

        pixmap: QPixmap = load_circular_avatar(
            self._current_source,
            size=self._size,
            fallback_initial=initial,
            callback=self._on_avatar_downloaded,
        )
        self.setPixmap(pixmap)

    def _on_avatar_downloaded(self, pixmap: QPixmap) -> None:
        """Invoked when background download finishes."""
        self.setPixmap(pixmap)


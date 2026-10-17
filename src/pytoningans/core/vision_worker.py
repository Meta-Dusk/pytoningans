import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, QRunnable, Signal


HTTRANSPARENT = -1
HTCLIENT = 1


def fetch_visible_windows_worker() -> list[str]:
    """Background worker function querying visible window titles safely."""
    user32: ctypes.WinDLL = ctypes.windll.user32

    # Ensure worker thread on Windows is attached to interactive desktop
    try:
        hdesk = user32.OpenInputDesktop(0, False, 0x10000000)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

    # Explicitly define C-types for compiled environments
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL

    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int

    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int

    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL

    titles: list[str] = []

    def foreach_window(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if buff.value:
                    titles.append(buff.value)
        return True

    # Keep a strong reference to the callback during execution to prevent GC crashes
    callback = WNDENUMPROC(foreach_window)
    user32.EnumWindows(callback, 0)

    return titles


class VisionWorkerSignals(QObject):
    finished = Signal(list)


class VisionWorker(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = VisionWorkerSignals()

    def run(self) -> None:
        titles: list[str] = fetch_visible_windows_worker()
        self.signals.finished.emit(titles)

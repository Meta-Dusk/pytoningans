from __future__ import annotations

import ctypes, os
from ctypes import wintypes
from typing import Optional

from PySide6.QtCore import QObject, QRect

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
WS_MAXIMIZE = 0x01000000
WS_EX_TOOLWINDOW = 0x00000080
GWL_STYLE = -16
GWL_EXSTYLE = -20

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumDesktopWindows.argtypes = [wintypes.HDESK, WNDENUMPROC, wintypes.LPARAM]
user32.EnumDesktopWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL

MONITOR_DEFAULTTONEAREST = 2

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]

IGNORED_WINDOW_TITLES = {
    "Program Manager",
    "Settings",
    "Windows Input Experience",
    "Battery Meter",
    "Network Flyout",
    "Volume Control",
}


def query_interactive_windows() -> list[tuple[str, QRect]]:
    """
    Queries all visible, non-maximized, interactive application
    windows in virtual screen coordinates.
    """
    try:
        hdesk = user32.OpenInputDesktop(0, False, 0x10000000)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        hdesk = 0

    my_pid = os.getpid()
    windows: list[tuple[str, QRect]] = []

    def enum_cb(hwnd: wintypes.HWND, lparam: wintypes.LPARAM) -> bool:
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True

        # Check own PID (skip our own overlay, hub, and context menu windows)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == my_pid:
            return True

        # Check cloaked (Windows 10/11 virtual desktops and suspended UWP apps)
        cloaked = ctypes.c_int(0)
        dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
        )
        if cloaked.value != 0:
            return True

        # Check maximized
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        if style & WS_MAXIMIZE:
            return True

        # Check tool window
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if ex_style & WS_EX_TOOLWINDOW:
            return True

        # Check title
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()

        if not title or title in IGNORED_WINDOW_TITLES:
            return True

        # Get visual frame bounds (accurate without invisible resize drop shadows)
        rect = wintypes.RECT()
        hr = dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
        )
        if hr != 0:
            user32.GetWindowRect(hwnd, ctypes.byref(rect))

        # Check if window is in fullscreen mode or covers the screen
        hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        if hmon:
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                if (rect.left <= mi.rcMonitor.left and rect.top <= mi.rcMonitor.top and
                        rect.right >= mi.rcMonitor.right and rect.bottom >= mi.rcMonitor.bottom):
                    return True
                if (rect.left <= mi.rcWork.left and rect.top <= mi.rcWork.top and
                        rect.right >= mi.rcWork.right and rect.bottom >= mi.rcWork.bottom):
                    return True

        w: int = rect.right - rect.left
        h: int = rect.bottom - rect.top
        if w > 100 and h > 80:
            windows.append((title, QRect(rect.left, rect.top, w, h)))

        return True

    cb = WNDENUMPROC(enum_cb)
    if hdesk:
        user32.EnumDesktopWindows(hdesk, cb, 0)
    else:
        user32.EnumWindows(cb, 0)

    return windows


class WindowTracker(QObject):
    """Tracks visible non-maximized desktop windows and maps them to local screen viewports."""

    def __init__(self) -> None:
        super().__init__()
        self.active_global_windows: list[tuple[str, QRect]] = []

    def update(self) -> list[tuple[str, QRect]]:
        """Refreshes the active desktop window list."""
        self.active_global_windows = query_interactive_windows()
        return self.active_global_windows

    def get_local_window_rects_for_screen(self, screen_geom: QRect) -> list[QRect]:
        """Maps global window bounds into a specific screen's local scene coordinates."""
        local_rects: list[QRect] = []
        screen_bounds = QRect(0, 0, screen_geom.width(), screen_geom.height())

        for _, global_rect in self.active_global_windows:
            local_x = global_rect.x() - screen_geom.x()
            local_y = global_rect.y() - screen_geom.y()
            local_rect = QRect(local_x, local_y, global_rect.width(), global_rect.height())

            if local_rect.intersects(screen_bounds):
                local_rects.append(local_rect)

        return local_rects

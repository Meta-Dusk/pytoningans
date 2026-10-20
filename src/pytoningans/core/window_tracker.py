from __future__ import annotations

import ctypes, os
from ctypes import Array, wintypes
from typing import Optional

from PySide6.QtCore import QObject, QRect

user32: ctypes.WinDLL = ctypes.windll.user32
dwmapi: ctypes.WinDLL = ctypes.windll.dwmapi

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
WS_MAXIMIZE = 0x01000000
WS_EX_TOOLWINDOW = 0x00000080
GWL_STYLE = -16
GWL_EXSTYLE = -20

SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_ASYNCWINDOWPOS = 0x4000

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumDesktopWindows.argtypes = [wintypes.HDESK, WNDENUMPROC, wintypes.LPARAM]
user32.EnumDesktopWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL

user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL

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


class TrackedWindow:
    """Represents an active interactive desktop window with its native handle and bounds."""

    def __init__(self, hwnd: wintypes.HWND | int, title: str, rect: QRect) -> None:
        self.hwnd: int = int(hwnd)
        self.title: str = title
        self.rect: QRect = rect

    def __iter__(self):
        yield self.title
        yield self.rect

    def __repr__(self) -> str:
        return f"TrackedWindow(hwnd={self.hwnd}, title={self.title!r}, rect={self.rect})"


def query_interactive_windows() -> list[TrackedWindow]:
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

    my_pid: int = os.getpid()
    windows: list[TrackedWindow] = []

    def enum_cb(hwnd: wintypes.HWND, lparam: wintypes.LPARAM) -> bool:
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True

        # Check own PID (skip our own overlay, hub, and context menu windows)
        pid: ctypes.c_ulong = wintypes.DWORD()
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
        buf: Array[ctypes.c_wchar] = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title: str = buf.value.strip()

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
            windows.append(TrackedWindow(hwnd, title, QRect(rect.left, rect.top, w, h)))

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
        self.active_global_windows: list[TrackedWindow] = []

    def update(self) -> list[TrackedWindow]:
        """Refreshes the active desktop window list."""
        self.active_global_windows = query_interactive_windows()
        return self.active_global_windows

    def get_local_windows_for_screen(self, screen_geom: QRect) -> list[tuple[TrackedWindow, QRect]]:
        """Maps global window bounds into a specific screen's local scene coordinates."""
        local_entries: list[tuple[TrackedWindow, QRect]] = []
        screen_bounds = QRect(0, 0, screen_geom.width(), screen_geom.height())

        for tracked_win in self.active_global_windows:
            global_rect: QRect = tracked_win.rect
            local_x: int = global_rect.x() - screen_geom.x()
            local_y: int = global_rect.y() - screen_geom.y()
            local_rect = QRect(local_x, local_y, global_rect.width(), global_rect.height())

            if local_rect.intersects(screen_bounds):
                local_entries.append((tracked_win, local_rect))

        return local_entries

    def get_local_window_rects_for_screen(self, screen_geom: QRect) -> list[QRect]:
        """Maps global window bounds into a specific screen's local scene coordinates."""
        return [lr for _, lr in self.get_local_windows_for_screen(screen_geom)]

    def move_window(self, hwnd: int, dx: int, dy: int) -> tuple[bool, int, int]:
        """
        Moves the desktop window associated with `hwnd` by (dx, dy) pixels.
        Clamps the new window position to the monitor's work area.
        Returns (succeeded, actual_dx, actual_dy).
        """
        if not user32.IsWindow(hwnd):
            return False, 0, 0

        # Retrieve current visual frame bounds
        rect = wintypes.RECT()
        hr = dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
        )
        if hr != 0:
            user32.GetWindowRect(hwnd, ctypes.byref(rect))

        curr_x: int = rect.left
        curr_y: int = rect.top
        w: int = rect.right - rect.left
        h: int = rect.bottom - rect.top

        # Clamp against monitor work area
        hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        if hmon:
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                work_left = mi.rcWork.left
                work_right = mi.rcWork.right
                work_top = mi.rcWork.top
                work_bottom = mi.rcWork.bottom

                target_x: int = curr_x + dx
                target_y: int = curr_y + dy

                clamped_x = max(work_left, min(target_x, work_right - w))
                clamped_y = max(work_top, min(target_y, work_bottom - h))
            else:
                clamped_x = curr_x + dx
                clamped_y = curr_y + dy
        else:
            clamped_x = curr_x + dx
            clamped_y = curr_y + dy

        actual_dx = clamped_x - curr_x
        actual_dy = clamped_y - curr_y

        if actual_dx == 0 and actual_dy == 0:
            return False, 0, 0

        flags = SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS
        success = bool(user32.SetWindowPos(hwnd, 0, clamped_x, clamped_y, 0, 0, flags))
        if success:
            for tw in self.active_global_windows:
                if tw.hwnd != hwnd: continue
                tw.rect = QRect(clamped_x, clamped_y, w, h)
                break
        return success, actual_dx, actual_dy

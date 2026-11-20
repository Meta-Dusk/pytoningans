import os, sys, ctypes
from ctypes import wintypes


def _enable_windows_ansi() -> None:
    if sys.platform != "win32":
        return

    std_output_handle: int = -11
    enable_vt_processing: int = 0x0004

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.GetStdHandle(std_output_handle)
    mode = wintypes.DWORD()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | enable_vt_processing)


class Style:
    _ENABLED: bool = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    if _ENABLED:
        _enable_windows_ansi()

    RESET: str = "\033[0m" if _ENABLED else ""
    BOLD: str = "\033[1m" if _ENABLED else ""
    DIM: str = "\033[2m" if _ENABLED else ""
    RED: str = "\033[91m" if _ENABLED else ""
    GREEN: str = "\033[92m" if _ENABLED else ""
    YELLOW: str = "\033[93m" if _ENABLED else ""
    CYAN: str = "\033[96m" if _ENABLED else ""

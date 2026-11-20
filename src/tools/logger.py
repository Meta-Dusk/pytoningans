from typing import Optional

from .style_service import Style


class Log:
    @staticmethod
    def info(msg: str) -> None:
        print(f"{Style.CYAN}[INFO]  {msg}{Style.RESET}")
    
    @staticmethod
    def success(msg: str) -> None:
        print(f"{Style.GREEN}[OK]    {msg}{Style.RESET}")
    
    @staticmethod
    def warn(msg: str) -> None:
        print(f"{Style.YELLOW}[WARN]  {msg}{Style.RESET}")
    
    @staticmethod
    def error(msg: str) -> None:
        print(f"{Style.RED}[ERROR] {msg}{Style.RESET}")

class PrintBadge:
    @staticmethod
    def info(end: Optional[str] = "") -> None:
        print(f"{Style.CYAN}[INFO]  {Style.RESET}", end=end)
    
    @staticmethod
    def success(end: Optional[str] = "") -> None:
        print(f"{Style.GREEN}[OK]    {Style.RESET}", end=end)
    
    @staticmethod
    def warn(end: Optional[str] = "") -> None:
        print(f"{Style.YELLOW}[WARN]  {Style.RESET}", end=end)
    
    @staticmethod
    def error(end: Optional[str] = "") -> None:
        print(f"{Style.RED}[ERROR] {Style.RESET}", end=end)

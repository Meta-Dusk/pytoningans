from typing import Protocol, Optional
from PySide6.QtCore import QPoint
from pytoningans.core.constants import PetState

# TODO: Test API Interface if it works in a modding environment

class IPet(Protocol):
    """
    Public-facing type definition for modders. 
    Provides IDE autocompletion and type safety for behavior scripts.
    """
    x: int
    y: int
    state: PetState
    is_dead: bool
    current_health: int
    target_pos: Optional[QPoint]
    facing_left: bool

    def jump(self) -> None:
        """Forces the pet to perform a jump action."""
        ...

    def die(self) -> None:
        """Immediately kills the pet."""
        ...

    def revive(self) -> None:
        """Revives the pet back to full health."""
        ...

    def width(self) -> int:
        """Returns the current width of the pet window."""
        ...

    def height(self) -> int:
        """Returns the current height of the pet window."""
        ...

    def move(self, x: int, y: int) -> None:
        """Teleports or moves the pet window to absolute screen coordinates."""
        ...
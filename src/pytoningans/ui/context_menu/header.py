from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from .window import EntityContextMenu


class ContextMenuHeader(QWidget):
    """
    Draggable header bar for the entity context menu window.
    Clicking and dragging on this header smoothly repositions the window on screen.
    """
    def __init__(self, parent_window: EntityContextMenu) -> None:
        super().__init__(parent_window)
        self.parent_window: EntityContextMenu = parent_window
        self._drag_offset: Optional[QPoint] = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self.parent_window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()


from typing import Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QStyle, QStyleOption
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent, QPainter, QPaintEvent

from pytoningans.utils.paths import get_app_version

class CustomTitleBar(QWidget):
    def __init__(
        self, parent: QWidget, title: str,
        show_version: bool = True,
        can_minimize: bool = True,
        can_maximize: bool = True
    ) -> None:
        super().__init__(parent)
        self.parent_window: QWidget = parent
        self._drag_offset: Optional[QPoint] = None
        self._setup_ui(title, show_version, can_minimize, can_maximize)

    def _setup_ui(
        self, title: str,
        show_version: bool = True,
        can_minimize: bool = True,
        can_maximize: bool = True
    ) -> None:
        self.setFixedHeight(32)
        self.setObjectName("CustomTitleBar")
        
        layout: QHBoxLayout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(6)
        
        self.title_label: QLabel = QLabel(title)
        self.title_label.setObjectName("TitleBarText")
        layout.addWidget(self.title_label)
        
        if show_version:
            self.version_label: QLabel = QLabel(f"v{get_app_version()}")
            self.version_label.setObjectName("TitleBarVersion")
            layout.addWidget(self.version_label)
        
        layout.addStretch()

        if can_minimize:
            self.minimize_btn: QPushButton = QPushButton("[_]")
            self.minimize_btn.setFixedSize(32, 32)
            self.minimize_btn.setObjectName("TitleBarBtn")
            self.minimize_btn.clicked.connect(self.parent_window.showMinimized)
            layout.addWidget(self.minimize_btn)
        
        if can_maximize:
            self.maximize_btn: QPushButton = QPushButton("[+]")
            self.maximize_btn.setFixedSize(32, 32)
            self.maximize_btn.setObjectName("TitleBarBtn")
            self.maximize_btn.clicked.connect(self._toggle_maximize)
            layout.addWidget(self.maximize_btn)
        
        self.close_btn: QPushButton = QPushButton("[X]")
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setObjectName("TitleBarCloseBtn")
        self.close_btn.clicked.connect(self.parent_window.close)
        layout.addWidget(self.close_btn)

    def paintEvent(self, _: QPaintEvent) -> None:
        """Forces the QSS engine to render backgrounds and borders on custom QWidgets."""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

    # --- Window Dragging Logic ---
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            topLeft: QPoint = self.parent_window.frameGeometry().topLeft()
            self._drag_offset = event.globalPosition().toPoint() - topLeft
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            if self.parent_window.isMaximized():
                # Fetch the exact width the window WILL be when it restores
                normal_width = self.parent_window.normalGeometry().width()
                
                # Fallback just in case the OS hasn't cached a normal geometry yet
                if normal_width == 0: normal_width = 880
                
                # Calculate the proportional offset using the active maximized width
                max_width = self.parent_window.width()
                ratio = self._drag_offset.x() / max_width
                new_offset_x = int(normal_width * ratio)
                
                # Update the offset BEFORE restoring the window
                self._drag_offset = QPoint(new_offset_x, self._drag_offset.y())
                
                # Restore the window
                self.parent_window.showNormal()
                if hasattr(self, "maximize_btn"):
                    self.maximize_btn.setText("[+]")

            # Move the window
            self.parent_window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()
    
    # --- Other Window Events ---
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if hasattr(self, "maximize_btn") and event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
            event.accept()
    
    def _toggle_maximize(self) -> None:
        if not hasattr(self, "maximize_btn"):
            return
            
        # Get the top-level parent widget
        window: QWidget = self.window()
        if window.isMaximized():
            window.showNormal()
            self.maximize_btn.setText("[+]")
        else:
            window.showMaximized()
            self.maximize_btn.setText("[-]")

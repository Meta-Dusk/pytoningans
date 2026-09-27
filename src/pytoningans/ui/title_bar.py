from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QStyle, QStyleOption
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent, QPainter, QPaintEvent

class CustomTitleBar(QWidget):
    def __init__(self, parent: QWidget, title: str) -> None:
        super().__init__(parent)
        self.parent_window: QWidget = parent
        self._drag_offset: QPoint | None = None
        self._setup_ui(title)

    def _setup_ui(self, title: str) -> None:
        self.setFixedHeight(32)
        self.setObjectName("CustomTitleBar")
        
        layout: QHBoxLayout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        
        self.title_label: QLabel = QLabel(title)
        self.title_label.setObjectName("TitleBarText")
        
        self.close_btn: QPushButton = QPushButton("[X]")
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setObjectName("TitleBarCloseBtn")
        self.close_btn.clicked.connect(self.parent_window.close)
        
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.close_btn)

    def paintEvent(self, _: QPaintEvent) -> None:
        """Forces the QSS engine to render backgrounds and borders on custom QWidgets."""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

    # --- Window Dragging Logic ---
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton:
            topLeft: QPoint = self.parent_window.frameGeometry().topLeft()
            self._drag_offset = event.globalPosition().toPoint() - topLeft
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() is Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self.parent_window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()
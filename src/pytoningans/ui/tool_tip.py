from typing import Optional
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QGuiApplication, QPainter, QPaintEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QStyle, QStyleOption, QWidget

class CustomToolTip(QWidget):
    """A completely customized overlay widget acting as a modern tooltip."""

    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        self.label = QLabel(text)
        self.label.setObjectName("ToolTipText")
        # Enable word wrapping and restrict width to prevent runaway horizontal growth
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(260)

        layout.addWidget(self.label)
        self.setObjectName("ToolTipLabel")

    def paintEvent(self, _: QPaintEvent) -> None:
        """Forces the QSS engine to render backgrounds and borders on custom QWidgets."""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)


class ToolTipLabel(QLabel):
    """A label for showing custom tool tips with monitor boundary awareness."""

    def __init__(self, text: str = "", tooltip_text: Optional[str] = None,
        *, parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(text, parent=parent)
        self.tooltip_text = tooltip_text
        self.custom_tooltip: Optional[CustomToolTip] = None
        self.init_tooltip()

    def init_tooltip(self) -> None:
        if self.tooltip_text:
            self.custom_tooltip = CustomToolTip(self.tooltip_text)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ToolTip and self.custom_tooltip:
            # Recompute layout size to accurately measure wrapped text dimensions
            self.custom_tooltip.adjustSize()
            tip_w = self.custom_tooltip.width()
            tip_h = self.custom_tooltip.height()

            # Target position: directly below the triggering label
            global_pos = self.mapToGlobal(QPoint(0, self.height() + 5))

            # Query the screen displaying the tooltip
            screen = (
                QGuiApplication.screenAt(global_pos)
                or QGuiApplication.primaryScreen()
            )
            if screen:
                screen_geom = screen.availableGeometry()

                # Clamp horizontal overflow (right edge)
                if global_pos.x() + tip_w > screen_geom.right() - 8:
                    global_pos.setX(screen_geom.right() - tip_w - 8)

                # Clamp horizontal underflow (left edge)
                if global_pos.x() < screen_geom.left() + 8:
                    global_pos.setX(screen_geom.left() + 8)

                # Clamp vertical overflow (flip above widget if hitting bottom edge)
                if global_pos.y() + tip_h > screen_geom.bottom() - 8:
                    above_pos = self.mapToGlobal(QPoint(0, 0)).y() - tip_h - 5
                    global_pos.setY(above_pos)

            self.custom_tooltip.move(global_pos)
            self.custom_tooltip.show()
            return True

        elif event.type() == QEvent.Type.Leave:
            if self.custom_tooltip:
                self.custom_tooltip.hide()

        return super().event(event)
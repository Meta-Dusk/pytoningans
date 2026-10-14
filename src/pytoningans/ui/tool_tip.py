from typing import Optional, cast

from PySide6.QtCore import (
    QAbstractItemModel, QEvent, QModelIndex, QPoint, QPointF, QRect, Qt, QObject, QTimer
)
from PySide6.QtGui import (
    QGuiApplication, QPainter, QPaintEvent, QScreen, QHelpEvent, QMouseEvent
)
from PySide6.QtWidgets import (
    QApplication, QGraphicsItem, QHBoxLayout, QLabel, QStyle, QStyleOption, QWidget,
    QAbstractItemView, QHeaderView, QGraphicsView
)

class CustomToolTip(QWidget):
    """A completely customized overlay widget acting as a modern tooltip."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        self.label = QLabel(text)
        self.label.setObjectName("ToolTipText")
        # Enable word wrapping and restrict width to prevent runaway horizontal growth
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(280)

        layout.addWidget(self.label)
        self.setObjectName("ToolTipLabel")

    def set_text(self, text: str) -> None:
        """Updates the tooltip text and resizes layout accordingly."""
        self.label.setText(text)
        self.adjustSize()

    def paintEvent(self, _: QPaintEvent) -> None:
        """Forces the QSS engine to render backgrounds and borders on custom QWidgets."""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)


class CustomToolTipManager(QObject):
    """Global manager that intercepts Qt ToolTip events and displays CustomToolTip for all widgets."""
    _instance: Optional[CustomToolTipManager] = None

    def __init__(self) -> None:
        super().__init__()
        self._tooltip_widget: Optional[CustomToolTip] = None
        self._current_widget: Optional[QObject] = None
        self._show_pos: QPoint = QPoint()

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_tip)

    @classmethod
    def get(cls) -> CustomToolTipManager:
        if cls._instance is None:
            cls._instance = CustomToolTipManager()
        return cls._instance

    def _ensure_widget(self) -> CustomToolTip:
        if self._tooltip_widget is None:
            self._tooltip_widget = CustomToolTip("")
        return self._tooltip_widget

    def show_tip(self, watched: Optional[QObject], text: str, global_pos: QPoint) -> None:
        clean_text: str = text.strip()
        if not clean_text:
            self.hide_tip()
            return

        tip: CustomToolTip = self._ensure_widget()
        if tip.label.text() != clean_text:
            tip.set_text(clean_text)
        tip_w: int = tip.width()
        tip_h: int = tip.height()

        pos = QPoint(global_pos.x() + 10, global_pos.y() + 18)

        # Screen boundary clamping
        screen: Optional[QScreen] = (
            QGuiApplication.screenAt(pos)
            or QGuiApplication.primaryScreen()
        )
        if screen:
            screen_geom: QRect = screen.availableGeometry()

            # Right edge clamp
            if pos.x() + tip_w > screen_geom.right() - 8:
                pos.setX(screen_geom.right() - tip_w - 8)

            # Left edge clamp
            if pos.x() < screen_geom.left() + 8:
                pos.setX(screen_geom.left() + 8)

            # Bottom edge clamp: flip above cursor if hitting bottom boundary
            if pos.y() + tip_h > screen_geom.bottom() - 8:
                pos.setY(global_pos.y() - tip_h - 8)

            # Top edge clamp
            if pos.y() < screen_geom.top() + 8:
                pos.setY(screen_geom.top() + 8)

        self._current_widget = watched
        self._show_pos = QPoint(global_pos)
        tip.move(pos)
        tip.show()
        tip.raise_()
        self._hide_timer.start(8000)

    def hide_tip(self) -> None:
        self._hide_timer.stop()
        self._current_widget = None
        if self._tooltip_widget is not None:
            self._tooltip_widget.hide()

    def _extract_tooltip_text(self, watched: QObject, event: QEvent) -> str:
        # Custom ToolTipLabel or any widget with tooltip_text attribute
        custom_tip = getattr(watched, "tooltip_text", None)
        if custom_tip:
            return str(custom_tip)

        # Extract position from QHelpEvent if available
        help_pos: QPoint = event.pos() if isinstance(event, QHelpEvent) else QPoint()

        # Item Views (QTableWidget, QListWidget, QTreeWidget, etc.)
        if isinstance(watched, QAbstractItemView):
            index: QModelIndex = watched.indexAt(help_pos)
            if index.isValid():
                tip_data = index.data(Qt.ItemDataRole.ToolTipRole)
                if tip_data:
                    return str(tip_data)
            return watched.toolTip()

        # Viewport of Item Views (where mouse events actually land in Qt)
        parent: Optional[QObject] = watched.parent()
        if isinstance(parent, QAbstractItemView):
            index: QModelIndex = parent.indexAt(help_pos)
            if index.isValid():
                tip_data = index.data(Qt.ItemDataRole.ToolTipRole)
                if tip_data:
                    return str(tip_data)
            return parent.toolTip()

        # Header views
        if isinstance(watched, QHeaderView):
            logical_index: int = watched.logicalIndexAt(help_pos)
            if logical_index >= 0:
                model: QAbstractItemModel = watched.model()
                if model:
                    tip_data = model.headerData(logical_index, watched.orientation(), Qt.ItemDataRole.ToolTipRole)
                    if tip_data:
                        return str(tip_data)
            return watched.toolTip()

        # Graphics Views (World overlay and scene items)
        view: Optional[QGraphicsView] = None
        if isinstance(watched, QGraphicsView):
            view = watched
        elif isinstance(watched, QWidget) and isinstance(watched.parent(), QGraphicsView):
            view = cast(QGraphicsView, watched.parent())

        if view is not None and view.scene() is not None:
            if isinstance(event, QHelpEvent):
                global_pos: QPoint = event.globalPos()
                viewport_pos: QPoint = view.viewport().mapFromGlobal(global_pos)
            else:
                viewport_pos = help_pos
            scene_pos: QPointF = view.mapToScene(viewport_pos)
            item: Optional[QGraphicsItem] = view.scene().itemAt(scene_pos, view.transform())
            curr_item: Optional[QGraphicsItem] = item
            while curr_item is not None:
                tip: str = curr_item.toolTip()
                if tip:
                    return tip
                display_name = getattr(curr_item, "display_name", None)
                if display_name:
                    return str(display_name)
                curr_item = curr_item.parentItem()
            return view.toolTip()

        # General QWidget
        if isinstance(watched, QWidget):
            direct_tip: str = watched.toolTip()
            if direct_tip:
                return direct_tip

            # Check ancestor widgets in compound controls
            curr: Optional[QObject] = watched.parent()
            while isinstance(curr, QWidget):
                curr_tip: str = curr.toolTip()
                if curr_tip:
                    return curr_tip
                curr = curr.parent()

        return ""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        event_type = event.type()

        if event_type == QEvent.Type.ToolTip:
            text: str = self._extract_tooltip_text(watched, event)
            if text:
                help_pos: QPoint = event.globalPos() if isinstance(event, QHelpEvent) else QPoint()
                self.show_tip(watched, text, help_pos)
                return True
            else:
                self.hide_tip()
                return False

        elif event_type == QEvent.Type.MouseMove:
            if self._current_widget is not None and watched is self._current_widget:
                is_view = isinstance(watched, (QGraphicsView, QAbstractItemView)) or (
                    isinstance(watched, QWidget) and isinstance(watched.parent(), (QGraphicsView, QAbstractItemView))
                )
                if not is_view:
                    mouse_pos = event.globalPos() if isinstance(event, (QMouseEvent, QHelpEvent)) else QPoint()
                    if (mouse_pos - self._show_pos).manhattanLength() > 25:
                        self.hide_tip()

        elif event_type in (
            QEvent.Type.Leave,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.WindowDeactivate,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel
        ):
            if event_type in (QEvent.Type.WindowDeactivate, QEvent.Type.KeyPress):
                self.hide_tip()
            elif self._current_widget is not None:
                if event_type == QEvent.Type.Leave and watched is not self._current_widget:
                    pass
                else:
                    self.hide_tip()

        return False


def install_global_tooltip_filter(app: Optional[QApplication] = None) -> CustomToolTipManager:
    """Installs the custom tooltip filter globally on the application."""
    manager = CustomToolTipManager.get()
    target_app = app or QApplication.instance()
    if target_app and not getattr(target_app, "_custom_tooltip_installed", False):
        target_app.installEventFilter(manager)
        setattr(target_app, "_custom_tooltip_installed", True)
    return manager


class ToolTipLabel(QLabel):
    """A label for showing custom tool tips with monitor boundary awareness."""

    def __init__(
        self, text: str = "", tooltip_text: Optional[str] = None,
        *, parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(text, parent=parent)
        self.tooltip_text: Optional[str] = tooltip_text
        if tooltip_text is not None:
            self.setToolTip(tooltip_text)
        self.custom_tooltip: Optional[CustomToolTip] = None

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ToolTip and self.tooltip_text:
            CustomToolTipManager.get().show_tip(
                self, self.tooltip_text, self.mapToGlobal(QPoint(0, self.height() + 5))
            )
            return True
        elif event.type() == QEvent.Type.Leave:
            CustomToolTipManager.get().hide_tip()
        return super().event(event)

    def show_tooltip(self) -> None:
        if self.tooltip_text:
            CustomToolTipManager.get().show_tip(
                self, self.tooltip_text, self.mapToGlobal(QPoint(0, self.height() + 5))
            )
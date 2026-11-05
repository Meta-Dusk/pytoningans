from __future__ import annotations

from typing import Optional, cast, TYPE_CHECKING

from PySide6.QtCore import QEvent, QPoint, Qt, QObject, QTimer
from PySide6.QtGui import QGuiApplication, QPainter, QHelpEvent, QMouseEvent
from PySide6.QtWidgets import (
    QApplication, QGraphicsItem, QHBoxLayout, QLabel, QStyle, QStyleOption, QWidget,
    QAbstractItemView, QHeaderView, QGraphicsView
)

if TYPE_CHECKING:
    from PySide6.QtCore import QAbstractItemModel, QModelIndex, QPointF, QRect
    from PySide6.QtGui import QScreen, QPaintEvent


class CustomToolTip(QWidget):
    """A completely customized overlay widget acting as a modern tooltip."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QHBoxLayout(self); layout.setContentsMargins(10, 8, 10, 8)

        self.label = QLabel(text); self.label.setObjectName("ToolTipText")
        self.label.setWordWrap(True); self.label.setMaximumWidth(280)

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
        if screen is not None:
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

        #? Header Views (QHeaderView or its viewport)
        # Checked before QAbstractItemView since QHeaderView subclasses QAbstractItemView
        header_view: Optional[QHeaderView] = None
        if isinstance(watched, QHeaderView):
            header_view = watched
        elif isinstance(watched, QWidget) and isinstance(watched.parent(), QHeaderView):
            header_view = cast(QHeaderView, watched.parent())

        if header_view is not None:
            logical_index: int = header_view.logicalIndexAt(help_pos)
            if logical_index >= 0:
                model: Optional[QAbstractItemModel] = header_view.model()
                if model is not None:
                    tip_data = model.headerData(
                        logical_index, header_view.orientation(), Qt.ItemDataRole.ToolTipRole
                    )
                    if tip_data:
                        return str(tip_data)
                    disp_data = model.headerData(
                        logical_index, header_view.orientation(), Qt.ItemDataRole.DisplayRole
                    )
                    if disp_data:
                        disp_str = str(disp_data)
                        sec_size: int = header_view.sectionSize(logical_index)
                        fm = header_view.fontMetrics()
                        if fm.horizontalAdvance(disp_str) > sec_size - 12:
                            return disp_str
            return header_view.toolTip()

        #? Item Views (QTableWidget, QListView, QTreeWidget, etc. or their viewport)
        item_view: Optional[QAbstractItemView] = None
        if isinstance(watched, QAbstractItemView):
            item_view = watched
        elif isinstance(watched, QWidget) and isinstance(watched.parent(), QAbstractItemView):
            item_view = cast(QAbstractItemView, watched.parent())

        if item_view is not None:
            index: QModelIndex = item_view.indexAt(help_pos)
            if index.isValid():
                tip_data = index.data(Qt.ItemDataRole.ToolTipRole)
                if tip_data:
                    return str(tip_data)
                disp_text = index.data(Qt.ItemDataRole.DisplayRole)
                if disp_text:
                    disp_str = str(disp_text)
                    rect: QRect = item_view.visualRect(index)
                    fm = item_view.fontMetrics()
                    if fm.horizontalAdvance(disp_str) > rect.width() - 8:
                        return disp_str
            return item_view.toolTip()

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
        event_type: QEvent.Type = event.type()

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
                is_view: bool = isinstance(watched, (QGraphicsView, QAbstractItemView)) or (
                    isinstance(watched, QWidget) and isinstance(
                        watched.parent(), (QGraphicsView, QAbstractItemView)
                    )
                )
                if not is_view:
                    mouse_pos: QPoint = (
                        event.globalPos() if isinstance(event, (QMouseEvent, QHelpEvent))
                        else QPoint()
                    )
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
    manager: CustomToolTipManager = CustomToolTipManager.get()
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

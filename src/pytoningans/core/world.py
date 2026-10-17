from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import TYPE_CHECKING, cast, Optional

from PySide6.QtCore import QRect, Qt, QPoint, QPointF, QEvent, QObject
from PySide6.QtGui import QScreen, QMouseEvent, QKeyEvent, QColor, QBrush
from PySide6.QtWidgets import QMainWindow, QGraphicsView, QGraphicsScene, QApplication

from pytoningans.core.entity.indicators import DamageNumberItem
from pytoningans.core.vision_worker import HTCLIENT, HTTRANSPARENT
from pytoningans.core.window_tracker import TrackedWindow

if TYPE_CHECKING:
    from pytoningans.core.entity_manager import EntityManager
    from pytoningans.core.entity.base_entity import BaseEntity
    from pytoningans.core.entity.base_structure import BaseStructure
    from pytoningans.core.entity.base_item import BaseItem
    from pytoningans.core.entity.living_entity import Entity


class WorldView(QGraphicsView):
    """Specialized fullscreen view capturing mouse events for interactive placement."""

    def __init__(self, scene: QGraphicsScene, overlay: WorldOverlay) -> None:
        super().__init__(scene, overlay)
        self.overlay: WorldOverlay = overlay
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setStyleSheet("background: transparent; border: none;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched == self.viewport():
            etype = event.type()
            if etype == QEvent.Type.MouseMove:
                if self.overlay.manager.spawning_system.handle_mouse_move(self.overlay, cast(QMouseEvent, event)):
                    return True
            elif etype == QEvent.Type.MouseButtonPress:
                if self.overlay.manager.spawning_system.handle_mouse_press(self.overlay, cast(QMouseEvent, event)):
                    return True
            elif etype == QEvent.Type.MouseButtonRelease:
                if self.overlay.manager.spawning_system.handle_mouse_release(self.overlay, cast(QMouseEvent, event)):
                    return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            for entity in self.overlay.active_entities:
                if not entity.is_cursor_grabbed: continue
                entity.release_cursor()
        if self.overlay.manager.spawning_system.handle_key_press(self.overlay, event):
            event.accept()
            return
        super().keyPressEvent(event)


class WorldOverlay(QMainWindow):
    """The transparent, fullscreen monitor overlay that acts as a **World**."""
    def __init__(self, screen: QScreen, manager: EntityManager) -> None:
        super().__init__()
        self.manager = manager
        self.target_screen = screen
        
        # The World now manages multiple entity types natively
        self.active_entities: list[Entity] = []
        self.active_structures: list[BaseStructure] = []
        self.active_items: list[BaseItem] = []
        self.active_damage_numbers: list[DamageNumberItem] = []
        self.active_window_rects: list[QRect] = []
        self.active_windows: list[tuple[TrackedWindow, QRect]] = []
        
        flags: Qt.WindowType = (
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.scene = QGraphicsScene(self)
        
        screen_geom: QRect = self.target_screen.availableGeometry()
        self.scene.setSceneRect(0, 0, screen_geom.width(), screen_geom.height())
        
        # Invisible alpha=1 backing to enable Windows DWM hit testing when placement mode is active
        self.capture_item = self.scene.addRect(
            0, 0, screen_geom.width(), screen_geom.height(),
            brush=QBrush(QColor(0, 0, 0, 1)),
            pen=Qt.PenStyle.NoPen
        )
        self.capture_item.setZValue(-1000)
        self.capture_item.setVisible(False)

        self.view = WorldView(self.scene, self)
        
        self.setCentralWidget(self.view)
        self.setGeometry(screen_geom)

    def set_input_capture(self, enabled: bool) -> None:
        """Toggles invisible alpha=1 surface backing so Windows DWM hit tests the overlay."""
        self.capture_item.setVisible(enabled)
        self.view.viewport().update()
        
    def nativeEvent(self, eventType, message):
        msg: wintypes.MSG = wintypes.MSG.from_address(message.__int__())
        if msg.message == 0x0084: # WM_NCHITTEST
            x: int = ctypes.c_short(msg.lParam & 0xFFFF).value
            y: int = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
            
            # If interactive placement or region selection mode is active
            if self.manager.spawning_system.is_active:
                cursor_global = QPoint(x, y)
                widget_under = QApplication.widgetAt(cursor_global)
                if widget_under is not None and widget_under.window() not in self.manager.active_worlds:
                    return True, HTTRANSPARENT
                return True, HTCLIENT

            local_pos: QPoint = self.view.mapFromGlobal(QPoint(x, y))
            scene_pos: QPointF = self.view.mapToScene(local_pos)
            
            item = self.scene.itemAt(scene_pos, self.view.transform())
            if item is not None and item != self.capture_item:
                return True, HTCLIENT
                
            return True, HTTRANSPARENT
            
        return super().nativeEvent(eventType, message)

    def spawn_damage_number(
        self, amount: int, scene_pos: QPointF, is_heal: bool = False
    ) -> None:
        indicator = DamageNumberItem(amount, scene_pos, is_heal)
        self.scene.addItem(indicator)
        self.active_damage_numbers.append(indicator)

    def move_window(self, win_rect: QRect, dx: int, dy: int) -> bool:
        """
        Moves the desktop window associated with win_rect by (dx, dy).
        Updates local collision rects immediately and carries any entities standing on it.
        """
        if self.manager.window_tracker is None:
            return False

        target_entry: Optional[tuple[TrackedWindow, QRect]] = None
        for tw, lr in self.active_windows:
            if lr is win_rect or lr == win_rect or lr.intersects(win_rect):
                target_entry = (tw, lr)
                break

        if target_entry is None:
            return False

        tw, lr = target_entry
        success, actual_dx, actual_dy = self.manager.window_tracker.move_window(tw.hwnd, dx, dy)
        if success and (actual_dx != 0 or actual_dy != 0):
            lr.translate(actual_dx, actual_dy)
            if win_rect is not lr:
                win_rect.translate(actual_dx, actual_dy)

            # Carry any entities currently standing on top of this window platform
            for entity in self.active_entities:
                if entity.physics_sys is None: continue
                current_platform_rect: Optional[QRect] = entity.physics_sys.current_platform_rect
                if current_platform_rect is None: continue
                if (
                    current_platform_rect is win_rect or 
                    current_platform_rect is lr or 
                    current_platform_rect == win_rect
                ):
                    entity.setPos(entity.x() + actual_dx, entity.y() + actual_dy)

            return True
        return False

    def update_systems(self, dt: int) -> None:
        # Tick static/interactive structures first
        for struct in list(self.active_structures):
            struct.update_systems(dt)
            
        # Tick mobile entities
        centers: dict[BaseEntity, QPointF] = {
            entity: entity.sceneBoundingRect().center() for entity in self.active_entities
        }
        for entity in list(self.active_entities):
            entity.update_systems(dt, centers)

        # Tick items
        for item in list(self.active_items):
            item.update_systems(dt)

        # Tick floating combat numbers
        for num in list(self.active_damage_numbers):
            if not num.tick(dt): continue
            if num.scene():
                self.scene.removeItem(num)
            if num in self.active_damage_numbers:
                self.active_damage_numbers.remove(num)
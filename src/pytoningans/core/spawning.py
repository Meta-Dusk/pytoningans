from __future__ import annotations

import random
from enum import StrEnum, unique
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QObject, QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QKeyEvent, QMouseEvent, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsColorizeEffect,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)

from pytoningans.core.constants import EntityState
from pytoningans.core.mod_manager import ModManager

if TYPE_CHECKING:
    from pytoningans.core.entity.base_entity import BaseEntity
    from pytoningans.core.entity_manager import EntityManager
    from pytoningans.core.world import WorldOverlay


@unique
class SpawnAreaMode(StrEnum):
    SCREEN = "screen"
    GROUND = "ground"
    SKY = "sky"
    CUSTOM = "custom"


def calculate_spawn_bounds(
    world: WorldOverlay,
    area_mode: str,
    custom_rect: Optional[QRect] = None,
) -> QRect:
    """Calculates candidate boundary rectangle based on area mode and target screen size."""
    scene_rect: QRectF = world.scene.sceneRect()
    sw = int(scene_rect.width())
    sh = int(scene_rect.height())

    if area_mode == SpawnAreaMode.GROUND.value:
        gh: int = max(60, int(sh * 0.18))
        return QRect(50, sh - gh - 30, max(50, sw - 100), gh)

    elif area_mode == SpawnAreaMode.SKY.value:
        sh_air: int = max(60, int(sh * 0.25))
        return QRect(50, 40, max(50, sw - 100), sh_air)

    elif (
        area_mode == SpawnAreaMode.CUSTOM.value
        and custom_rect is not None
        and not custom_rect.isEmpty()
    ):
        clamped: QRect = custom_rect.intersected(QRect(0, 0, sw, sh))
        if clamped.width() > 30 and clamped.height() > 30:
            return clamped

    # Default: Full Screen / World Bounds
    return QRect(50, 50, max(50, sw - 150), max(50, sh - 150))


def find_safe_spawn_coords(
    world: WorldOverlay,
    mod_folder: str,
    mods_dir: Path | str,
    bounds: QRect,
    avoid_windows: bool = True,
) -> tuple[float, float]:
    """
    Computes a non-colliding (x, y) spawn position for the entity within bounds.
    If avoid_windows is True, verifies that the entity's hitbox does not intersect
    any active desktop window to prevent ejection / boundary crushing.
    """
    mod_manager = ModManager(str(mods_dir))
    mod_manager.load_mod(mod_folder)

    # Physics extraction for frame 0 idle
    anchor, hitbox = mod_manager.get_frame_physics(EntityState.IDLE.value, 0)
    hw: int = hitbox.width() if hitbox.width() > 0 else 64
    hh: int = hitbox.height() if hitbox.height() > 0 else 64
    hx: int = hitbox.x()
    hy: int = hitbox.y()

    min_x: int = max(0, bounds.left())
    max_x: int = max(min_x, bounds.right() - hw)
    min_y: int = max(0, bounds.top())
    max_y: int = max(min_y, bounds.bottom() - hh)

    if max_x <= min_x:
        max_x = min_x + 5
    if max_y <= min_y:
        max_y = min_y + 5

    window_rects: list[QRect] = world.active_window_rects
    if not avoid_windows or not window_rects:
        rx: float = random.uniform(min_x, max_x)
        ry: float = random.uniform(min_y, max_y)
        return rx - hx, ry - hy

    # Window avoidance: sample candidate spots outside all active windows
    for _ in range(50):
        sample_x: float = random.uniform(min_x, max_x)
        sample_y: float = random.uniform(min_y, max_y)
        cand_hitbox = QRect(int(sample_x), int(sample_y), hw, hh)

        if not any(cand_hitbox.intersects(w) for w in window_rects):
            return sample_x - hx, sample_y - hy

    # If all 50 samples collide, attempt placing on top of a window roof platform
    for w in window_rects:
        roof_y: int = w.top() - hh
        if bounds.top() <= roof_y <= bounds.bottom():
            plat_left: int = max(bounds.left(), w.left() + 5)
            plat_right: int = min(bounds.right() - hw, w.right() - 5)
            if plat_right > plat_left:
                plat_x: float = random.uniform(plat_left, plat_right)
                cand_hitbox = QRect(int(plat_x), int(roof_y), hw, hh)
                if not any(
                    cand_hitbox.intersects(other_w)
                    for other_w in window_rects
                    if other_w != w
                ):
                    return plat_x - hx, roof_y - hy

    # Fallback to floor of bounds
    floor_y: int = max(bounds.top(), bounds.bottom() - hh)
    return random.uniform(min_x, max_x) - hx, floor_y - hy


class GhostPlacementItem(QGraphicsPixmapItem):
    """Semi-transparent preview item that follows the mouse cursor during placement mode."""

    def __init__(self) -> None:
        super().__init__()
        self.setZValue(999999)
        self.setOpacity(0.65)

        self.colorize_effect = QGraphicsColorizeEffect()
        self.colorize_effect.setColor(QColor(255, 60, 60))
        self.colorize_effect.setStrength(0.85)
        self.colorize_effect.setEnabled(False)
        self.setGraphicsEffect(self.colorize_effect)
        self.is_blocked: bool = False

    def set_blocked(self, blocked: bool) -> None:
        if self.is_blocked != blocked:
            self.is_blocked = blocked
            self.colorize_effect.setEnabled(blocked)
            self.setOpacity(0.45 if blocked else 0.70)


class RegionSelectionItem(QGraphicsRectItem):
    """Interactive drag selection rubberband rectangle with live dimension readout."""

    def __init__(self) -> None:
        super().__init__()
        self.setZValue(999998)
        pen = QPen(QColor(60, 160, 255), 2, Qt.PenStyle.DashLine)
        brush = QBrush(QColor(60, 160, 255, 45))
        self.setPen(pen)
        self.setBrush(brush)

        self.label = QGraphicsSimpleTextItem(self)
        self.label.setBrush(QBrush(QColor(255, 255, 255)))
        font = QFont("Pixel Code", 12, QFont.Weight.Bold)
        self.label.setFont(font)
        self.label.setText("")

    def update_rect(self, rect: QRectF) -> None:
        self.setRect(rect)
        w, h = int(rect.width()), int(rect.height())
        self.label.setText(f" {w} x {h} ")
        self.label.setPos(rect.left() + 6, rect.top() + 6)


class SpawningSystem(QObject):
    """
    Coordinates entity placement modes, window-safe coordinate sampling,
    and region bounds selection across all desktop world overlays.
    """

    placement_started = Signal(str, int)  # (mod_name, remaining_count)
    placement_count_changed = Signal(int)  # (remaining_count)
    placement_ended = Signal()

    region_selection_started = Signal()
    region_selection_ended = Signal(bool, QRect)  # (succeeded, rect)

    def __init__(self, manager: EntityManager) -> None:
        super().__init__()
        self.manager: EntityManager = manager

        self.is_placing: bool = False
        self.is_selecting_region: bool = False

        self.placement_mod_folder: str = ""
        self.placement_mod_name: str = ""
        self.remaining_count: int = 0
        self.avoid_windows: bool = True

        self.ghost_item: GhostPlacementItem = GhostPlacementItem()
        self.ghost_anchor: QPoint = QPoint(0, 0)
        self.ghost_hitbox: QRect = QRect()

        self.selection_item: RegionSelectionItem = RegionSelectionItem()
        self.selection_start_pos: Optional[QPointF] = None
        self.selection_world: Optional[WorldOverlay] = None

        self.custom_region: Optional[QRect] = None
        self.custom_region_world: Optional[WorldOverlay] = None

    @property
    def is_active(self) -> bool:
        """True if any interactive mode (placement or region selection) is underway."""
        return self.is_placing or self.is_selecting_region

    def start_placement(
        self, mod_folder: str, amount: int = 1, avoid_windows: bool = True
    ) -> None:
        """Activates cursor placement mode with ghost preview."""
        self.cancel_all()

        self.placement_mod_folder = mod_folder
        mod_manager = ModManager(str(self.manager.mod_manager.mods_dir))
        mod_manager.load_mod(mod_folder)

        self.placement_mod_name = mod_manager.current_mod_name or mod_folder
        self.remaining_count = max(1, amount)
        self.avoid_windows = avoid_windows

        pixmap: Optional[QPixmap] = mod_manager.get_frame(EntityState.IDLE.value, 0)
        if pixmap is None or pixmap.isNull():
            for key in mod_manager.animations.keys():
                pixmap = mod_manager.get_frame(key, 0)
                if pixmap is not None and not pixmap.isNull():
                    break

        if pixmap is None or pixmap.isNull():
            pixmap = QPixmap(64, 64)
            pixmap.fill(QColor(100, 150, 255, 120))

        anchor, hitbox = mod_manager.get_frame_physics(EntityState.IDLE.value, 0)
        self.ghost_anchor = anchor
        self.ghost_hitbox = hitbox
        if self.ghost_hitbox.isEmpty() or self.ghost_hitbox.width() == 0:
            self.ghost_hitbox = QRect(0, 0, pixmap.width(), pixmap.height())

        self.ghost_item.setPixmap(pixmap)
        self.ghost_item.set_blocked(False)
        self.is_placing = True

        for world in self.manager.active_worlds:
            world.set_input_capture(True)
            world.view.viewport().setCursor(Qt.CursorShape.CrossCursor)

        self.placement_started.emit(self.placement_mod_name, self.remaining_count)

    def cancel_placement(self) -> None:
        """Exits placement mode and removes the ghost preview from scenes."""
        if not self.is_placing:
            return
        self.is_placing = False
        if self.ghost_item.scene() is not None:
            self.ghost_item.scene().removeItem(self.ghost_item)
        for world in self.manager.active_worlds:
            world.set_input_capture(False)
            world.view.viewport().unsetCursor()
        self.placement_ended.emit()

    def start_region_selection(self) -> None:
        """Enables interactive rubberband box drag across monitor overlays."""
        self.cancel_all()
        self.is_selecting_region = True
        self.selection_start_pos = None
        self.selection_world = None
        for world in self.manager.active_worlds:
            world.set_input_capture(True)
            world.view.viewport().setCursor(Qt.CursorShape.CrossCursor)
        QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
        self.region_selection_started.emit()

    def cancel_region_selection(self) -> None:
        """Cancels region selection mode without saving."""
        if not self.is_selecting_region:
            return
        self.is_selecting_region = False
        self.selection_start_pos = None
        self.selection_world = None
        if self.selection_item.scene() is not None:
            self.selection_item.scene().removeItem(self.selection_item)
        for world in self.manager.active_worlds:
            world.set_input_capture(False)
            world.view.viewport().unsetCursor()
        QApplication.restoreOverrideCursor()
        self.region_selection_ended.emit(False, QRect())

    def confirm_region_selection(self, world: WorldOverlay, rect: QRect) -> None:
        """Confirms and stores the user-drawn region."""
        self.is_selecting_region = False
        self.selection_start_pos = None
        self.selection_world = None
        self.custom_region = rect
        self.custom_region_world = world
        if self.selection_item.scene() is not None:
            self.selection_item.scene().removeItem(self.selection_item)
        for w in self.manager.active_worlds:
            w.set_input_capture(False)
            w.view.viewport().unsetCursor()
        QApplication.restoreOverrideCursor()
        self.region_selection_ended.emit(True, rect)

    def cancel_all(self) -> None:
        """Cancels any running interactive placement or region selection mode."""
        if self.is_placing:
            self.cancel_placement()
        if self.is_selecting_region:
            self.cancel_region_selection()
        for world in self.manager.active_worlds:
            world.set_input_capture(False)
            world.view.viewport().unsetCursor()

    def handle_mouse_move(self, world: WorldOverlay, event: QMouseEvent) -> bool:
        """Tracks cursor movement for ghost placement or region box updates."""
        pt = event.position().toPoint()
        if self.is_placing:
            scene_pos: QPointF = world.view.mapToScene(pt)

            if self.ghost_item.scene() != world.scene:
                if self.ghost_item.scene() is not None:
                    self.ghost_item.scene().removeItem(self.ghost_item)
                world.scene.addItem(self.ghost_item)

            self.ghost_item.setVisible(True)
            gx: float = scene_pos.x() - self.ghost_anchor.x()
            gy: float = scene_pos.y() - self.ghost_anchor.y()
            self.ghost_item.setPos(gx, gy)

            # Hitbox check for window collisions
            hw: int = self.ghost_hitbox.width()
            hh: int = self.ghost_hitbox.height()
            hx: int = self.ghost_hitbox.x()
            hy: int = self.ghost_hitbox.y()
            cand_hitbox = QRect(int(gx + hx), int(gy + hy), hw, hh)

            win_rects: list[QRect] = world.active_window_rects
            blocked: bool = self.avoid_windows and any(
                cand_hitbox.intersects(w) for w in win_rects
            )
            self.ghost_item.set_blocked(blocked)
            return True

        elif self.is_selecting_region:
            if self.selection_start_pos is not None and self.selection_world == world:
                curr_pos: QPointF = world.view.mapToScene(pt)
                x1, y1 = self.selection_start_pos.x(), self.selection_start_pos.y()
                x2, y2 = curr_pos.x(), curr_pos.y()
                rect = QRectF(
                    min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)
                )
                self.selection_item.update_rect(rect)
                return True

        return False

    def handle_mouse_press(self, world: WorldOverlay, event: QMouseEvent) -> bool:
        """Processes clicks during placement (spawning) or region selection (anchor start)."""
        pt = event.position().toPoint()
        if self.is_placing:
            if event.button() == Qt.MouseButton.LeftButton:
                scene_pos: QPointF = world.view.mapToScene(pt)
                gx: float = scene_pos.x() - self.ghost_anchor.x()
                gy: float = scene_pos.y() - self.ghost_anchor.y()

                hw: int = self.ghost_hitbox.width()
                hh: int = self.ghost_hitbox.height()
                hx: int = self.ghost_hitbox.x()
                hy: int = self.ghost_hitbox.y()
                cand_hitbox = QRect(int(gx + hx), int(gy + hy), hw, hh)

                win_rects: list[QRect] = world.active_window_rects
                if self.avoid_windows and any(cand_hitbox.intersects(w) for w in win_rects):
                    # Prevent placement inside desktop window
                    return True

                self.manager.spawn_entity(
                    gx, gy, self.placement_mod_folder, target_world=world
                )

                self.remaining_count -= 1
                self.placement_count_changed.emit(self.remaining_count)

                if self.remaining_count <= 0:
                    self.cancel_placement()
                return True

            elif event.button() == Qt.MouseButton.RightButton:
                self.cancel_placement()
                return True

        elif self.is_selecting_region:
            if event.button() == Qt.MouseButton.LeftButton:
                self.selection_world = world
                self.selection_start_pos = world.view.mapToScene(pt)

                if self.selection_item.scene() != world.scene:
                    if self.selection_item.scene() is not None:
                        self.selection_item.scene().removeItem(self.selection_item)
                    world.scene.addItem(self.selection_item)

                self.selection_item.update_rect(
                    QRectF(self.selection_start_pos, self.selection_start_pos)
                )
                self.selection_item.setVisible(True)
                return True

            elif event.button() == Qt.MouseButton.RightButton:
                self.cancel_region_selection()
                return True

        return False

    def handle_mouse_release(self, world: WorldOverlay, event: QMouseEvent) -> bool:
        """Processes mouse release to confirm region selection."""
        pt = event.position().toPoint()
        if self.is_selecting_region and self.selection_start_pos is not None:
            if (
                event.button() == Qt.MouseButton.LeftButton
                and self.selection_world == world
            ):
                curr_pos: QPointF = world.view.mapToScene(pt)
                x1, y1 = self.selection_start_pos.x(), self.selection_start_pos.y()
                x2, y2 = curr_pos.x(), curr_pos.y()
                rx = int(min(x1, x2))
                ry = int(min(y1, y2))
                rw = int(abs(x2 - x1))
                rh = int(abs(y2 - y1))

                if rw >= 30 and rh >= 30:
                    rect = QRect(rx, ry, rw, rh)
                    self.confirm_region_selection(world, rect)
                else:
                    self.cancel_region_selection()
                return True
        return False

    def handle_key_press(self, _: WorldOverlay, event: QKeyEvent) -> bool:
        """Escape key cancels any active placement or region selection mode."""
        if event.key() == Qt.Key.Key_Escape:
            if self.is_placing:
                self.cancel_placement()
                return True
            elif self.is_selecting_region:
                self.cancel_region_selection()
                return True
        return False

    def spawn_random(
        self,
        mod_folder: str,
        amount: int = 1,
        target_world: Optional[WorldOverlay] = None,
        area_mode: str = "screen",
        custom_rect: Optional[QRect] = None,
        avoid_windows: bool = True,
    ) -> list[BaseEntity]:
        """Spawns entities randomly within the configured area and safe window rules."""
        spawned: list[BaseEntity] = []
        worlds: list[WorldOverlay] = self.manager.active_worlds
        if not worlds:
            return spawned

        for _ in range(amount):
            world: WorldOverlay = target_world or random.choice(worlds)
            bounds: QRect = calculate_spawn_bounds(world, area_mode, custom_rect)
            x, y = find_safe_spawn_coords(
                world=world,
                mod_folder=mod_folder,
                mods_dir=self.manager.mod_manager.mods_dir,
                bounds=bounds,
                avoid_windows=avoid_windows,
            )
            entity: Optional[BaseEntity] = self.manager.spawn_entity(x, y, mod_folder, target_world=world)
            if entity is not None:
                spawned.append(entity)

        return spawned

